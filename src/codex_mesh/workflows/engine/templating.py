"""
Templating engine for workflows.
Supports {{ mustache }} variable substitution and property access.

Additions vs v1:
- Type-preserving substitution for pure "{{expr}}" strings
- List wildcard: foo[*].bar
- Simple filters: |length
"""

from __future__ import annotations

import re
from typing import Any

# allow *, | in expressions
_MUSTACHE_ANY = re.compile(r"\{\{\s*([^}]+?)\s*\}\}")
_MUSTACHE_FULL = re.compile(r"^\s*\{\{\s*([^}]+?)\s*\}\}\s*$")


def _split_filters(expr: str) -> tuple[str, list[str]]:
    parts = [p.strip() for p in expr.split("|")]
    path = parts[0]
    filters = parts[1:] if len(parts) > 1 else []
    return path, filters


def _tokenize(path: str) -> list[str]:
    # tokens: foo, [0], [*], bar
    tokens: list[str] = []
    i = 0
    while i < len(path):
        if path[i] == "[":
            j = path.find("]", i)
            if j == -1:
                raise ValueError(f"Unclosed [ in path: {path}")
            tokens.append(path[i : j + 1])
            i = j + 1
        elif path[i] == ".":
            i += 1
        else:
            j = i
            while j < len(path) and path[j] not in ".[":
                j += 1
            tokens.append(path[i:j])
            i = j
    return tokens


def _get_attr(cur: Any, key: str) -> Any:
    if isinstance(cur, dict):
        return cur.get(key)
    return getattr(cur, key, None)


def _apply_tokens(cur: Any, tokens: list[str]) -> Any:
    if cur is None:
        return None
    if not tokens:
        return cur

    t = tokens[0]

    # wildcard over list
    if t == "[*]":
        if not isinstance(cur, list):
            return None
        return [_apply_tokens(item, tokens[1:]) for item in cur]

    # index access
    if t.startswith("[") and t.endswith("]"):
        inside = t[1:-1].strip()
        if inside == "*":  # allow [*] also here
            if not isinstance(cur, list):
                return None
            return [_apply_tokens(item, tokens[1:]) for item in cur]
        try:
            idx = int(inside)
        except ValueError:
            return None
        if not isinstance(cur, list) or idx < 0 or idx >= len(cur):
            return None
        return _apply_tokens(cur[idx], tokens[1:])

    # property access
    nxt = _get_attr(cur, t)
    # Handle implicit dict access if attr failed on object, though _get_attr does both
    return _apply_tokens(nxt, tokens[1:])


def eval_expr(ctx: dict[str, Any], expr: str) -> Any:
    path, filters = _split_filters(expr.strip())
    tokens = _tokenize(path) if path else []
    val = _apply_tokens(ctx, tokens)

    for f in filters:
        if f == "length":
            try:
                val = 0 if val is None else len(val)
            except TypeError:
                val = 0
        elif f == "int":
            try:
                val = int(val)
            except (ValueError, TypeError):
                val = 0
        elif f == "float":
            try:
                val = float(val)
            except (ValueError, TypeError):
                val = 0.0
        elif f == "bool":
            val = bool(val)
        elif f == "str":
            val = str(val) if val is not None else ""
        elif f == "json":
            import json

            try:
                val = json.loads(val) if isinstance(val, str) else val
            except json.JSONDecodeError:
                val = None
        elif f.startswith("map("):
            import re

            m = re.search(r"map\((?:attribute=['\"]?|['\"]?)(\w+)['\"]?\)", f)
            if m and isinstance(val, list):
                attr = m.group(1)
                new_val = []
                for item in val:
                    if isinstance(item, dict):
                        new_val.append(item.get(attr))
                    else:
                        new_val.append(getattr(item, attr, None))
                val = new_val
        elif f.startswith("join("):
            import re

            m = re.search(r"join\(['\"]?(.*?)['\"]?\)", f)
            sep = m.group(1) if m else ", "
            if isinstance(val, list):
                val = sep.join(str(x) for x in val)
        else:
            # unknown filter -> leave as is (or could raise/log)
            pass
    return val


def render_template(value: Any, ctx: dict[str, Any]) -> Any:
    """
    - If value is a string:
      - if it's exactly "{{expr}}" -> returns the evaluated value with original type
      - else: interpolates all {{expr}} into the string (casting each to str)
    - If value is a dict/list: render recursively.
    - Otherwise return as-is.
    """
    if isinstance(value, str):
        # Check for exact single expression match first
        mfull = _MUSTACHE_FULL.match(value)
        if mfull:
            # Return the raw type from eval_expr (int, bool, list, etc.)
            return eval_expr(ctx, mfull.group(1))

        # Otherwise perform string interpolation
        def repl(m: re.Match) -> str:
            v = eval_expr(ctx, m.group(1))
            return "" if v is None else str(v)

        return _MUSTACHE_ANY.sub(repl, value)

    if isinstance(value, list):
        return [render_template(v, ctx) for v in value]

    if isinstance(value, dict):
        return {k: render_template(v, ctx) for k, v in value.items()}

    return value


# Jinja2 control structure detection
_JINJA_CONTROL = re.compile(r"\{%\s*(for|if|elif|else|endif|endfor|macro|endmacro)")


def _has_jinja_control(template: str) -> bool:
    """Check if template contains Jinja2 control structures."""
    return bool(_JINJA_CONTROL.search(template))


def render_compose_template(template_lines: list[str], ctx: dict[str, Any]) -> str:
    """
    Render a compose template (list of lines) with full Jinja2 support.

    For templates with {% for %}, {% if %}, etc., uses Jinja2 sandbox.
    For simple mustache-only templates, uses the faster mustache renderer.

    Args:
        template_lines: List of template strings to join and render.
        ctx: Context dictionary with variables.

    Returns:
        Rendered template string.
    """
    template_str = "\n".join(template_lines)

    # Check if we need full Jinja2
    if _has_jinja_control(template_str):
        return _render_jinja2(template_str, ctx)

    # Simple mustache rendering for each line
    rendered_lines = []
    for line in template_lines:
        rendered = render_template(line, ctx)
        if isinstance(rendered, str):
            rendered_lines.append(rendered)
        else:
            # If expression returned non-string (list, dict), convert to string
            rendered_lines.append(str(rendered) if rendered is not None else "")

    return "\n".join(rendered_lines)


def _render_jinja2(template_str: str, ctx: dict[str, Any]) -> str:
    """
    Render template using Jinja2 sandbox environment.

    Falls back gracefully if Jinja2 is not installed.
    """
    try:
        from jinja2.sandbox import SandboxedEnvironment
    except ImportError:
        # Jinja2 not available, try basic mustache rendering
        import logging

        logging.getLogger(__name__).warning(
            "Jinja2 not installed. Template with control structures may not render correctly."
        )
        return render_template(template_str, ctx)

    # Use sandboxed environment for security
    env = SandboxedEnvironment(
        # Keep {{ }} for variable interpolation (Jinja2 default)
        variable_start_string="{{",
        variable_end_string="}}",
        # Trim whitespace around blocks for cleaner output
        trim_blocks=True,
        lstrip_blocks=True,
    )

    try:
        template = env.from_string(template_str)
        return template.render(**ctx)
    except Exception as e:
        import logging

        logging.getLogger(__name__).error(f"Jinja2 template rendering failed: {e}")
        # Fall back to basic rendering
        return render_template(template_str, ctx)
