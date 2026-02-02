from __future__ import annotations

import json
import re
from typing import Any

_RE_INT = re.compile(r"\b(\d{1,6})\b")
_RE_KV = re.compile(
    r"(?P<k>[a-zA-Z_][a-zA-Z0-9_]*)\s*[:=]\s*(?P<v>.+?)(?=(\s+[a-zA-Z_][a-zA-Z0-9_]*\s*[:=])|$)"
)
_RE_FROM_TO = re.compile(r"\bfrom\s+(.+?)\s+to\s+(.+)$", re.IGNORECASE)
_RE_BETWEEN_AND = re.compile(r"\bbetween\s+(.+?)\s+and\s+(.+)$", re.IGNORECASE)


def _coerce(value: Any, schema: dict[str, Any]) -> Any:
    t = schema.get("type")
    if value is None:
        return None
    if t == "integer":
        try:
            return int(value)
        except Exception:
            return None
    if t == "boolean":
        if isinstance(value, bool):
            return value
        s = str(value).strip().lower()
        if s in ("1", "true", "yes", "y", "on"):
            return True
        if s in ("0", "false", "no", "n", "off"):
            return False
        return None
    if t == "array":
        if isinstance(value, list):
            return value
        s = str(value).strip()
        # try json list
        if s.startswith("[") and s.endswith("]"):
            try:
                v = json.loads(s)
                return v if isinstance(v, list) else None
            except Exception:
                pass
        # comma-separated
        return [x.strip() for x in s.split(",") if x.strip()]
    # string/object fallback
    return str(value)


def _parse_inline_json(text: str) -> dict[str, Any]:
    # allow: "... {\"symbol\":\"X\", \"depth\":2}"
    i = text.find("{")
    j = text.rfind("}")
    if i != -1 and j != -1 and j > i:
        chunk = text[i : j + 1]
        try:
            obj = json.loads(chunk)
            return obj if isinstance(obj, dict) else {}
        except Exception:
            return {}
    return {}


def _parse_kv(text: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for m in _RE_KV.finditer(text):
        out[m.group("k")] = m.group("v").strip().strip('"').strip("'")
    return out


def _first_int(text: str) -> int | None:
    m = _RE_INT.search(text)
    return int(m.group(1)) if m else None


def prepare_intent_input(
    intent_def: Any, query: str, slots: dict[str, Any] | None = None
) -> dict[str, Any]:
    """
    Build workflow input dict from:
      - schema defaults (intent_def.slots[*].default)
      - router slots (if any)
      - inline JSON or k=v inside query
      - heuristics for common fields
    """
    slots = dict(slots or {})
    schema = getattr(intent_def, "input_schema", {}) or {"type": "object", "properties": {}}
    props: dict[str, Any] = dict(schema.get("properties", {}) or {})

    out: dict[str, Any] = {}

    # 1) Parse inline JSON: "find {symbol: 'foo'}..."
    out.update(_parse_inline_json(query))

    # 2) Parse direct k=v pairs: "find symbol=foo depth=3"
    out.update(_parse_kv(query))

    # 5) heuristics for common required fields
    q = query.strip()

    # Special Heuristic: "Diagram of X" -> feature_query=X
    if "feature_query" in props and ("feature_query" not in out or not out.get("feature_query")):
        # English patterns
        m_en = re.search(
            r"\b(diagram|graph|call\s*graph)\s+(?:of|for|about)?\s*(.+)$", q, re.IGNORECASE
        )
        # Russian/Slavic patterns (fallback if no translation happened yet)
        m_ru = re.search(
            r"\b(диаграмма|граф|схема)\s+(?:модуля|файла|для)?\s*(.+)$", q, re.IGNORECASE
        )

        match = m_en or m_ru
        if match:
            candidate = match.group(2).strip()
            # if candidate is not just json or something
            if "{" not in candidate and len(candidate) > 1:
                out["feature_query"] = candidate

    # from/to patterns (graph_path)
    if "from" in props and ("from" not in out or not out.get("from")):
        m = _RE_FROM_TO.search(q) or _RE_BETWEEN_AND.search(q)
        if m:
            out["from"] = m.group(1).strip().strip('"').strip("'")
            if "to" in props:
                out["to"] = m.group(2).strip().strip('"').strip("'")

    # auto-fill single main string fields
    for key in ("symbol", "target", "query", "symptom", "scenario", "feature_query"):
        if key in props and (key not in out or out.get(key) in (None, "")):
            if key == "feature_query" and out.get(key):
                continue
            out[key] = q

    # numbers for common integer params
    n = _first_int(q)
    if n is not None:
        for key in (
            "limit",
            "k",
            "depth",
            "max_hops",
            "max_nodes",
            "token_budget",
            "duration_sec",
            "hotspot_limit",
            "max_depth",
        ):
            if key in props and (key not in out or out.get(key) is None):
                sch = props.get(key) if isinstance(props.get(key), dict) else {}
                cv = _coerce(n, sch if isinstance(sch, dict) else {})
                if cv is not None:
                    out[key] = cv

    # simple enums
    if "direction" in props and ("direction" not in out or not out.get("direction")):
        if re.search(r"\b(inbound|in)\b", q, re.IGNORECASE):
            out["direction"] = "in"
        elif re.search(r"\b(outbound|out)\b", q, re.IGNORECASE):
            out["direction"] = "out"

    if "horizon" in props and ("horizon" not in out or not out.get("horizon")):
        if "short" in q.lower():
            out["horizon"] = "short"
        elif "mid" in q.lower():
            out["horizon"] = "mid"
        elif "long" in q.lower():
            out["horizon"] = "long"

    # 6) Apply explicit slots (override heuristics)
    for key, val in slots.items():
        if val is not None:
            sch = props.get(key) if isinstance(props.get(key), dict) else {}
            coerced = _coerce(val, sch) if isinstance(sch, dict) else val
            if coerced is not None:
                out[key] = coerced

    # 7) defaults from schema (FINAL BACKFILL)
    for k, sch in props.items():
        if k not in out and isinstance(sch, dict) and "default" in sch:
            out[k] = sch["default"]

    return out
