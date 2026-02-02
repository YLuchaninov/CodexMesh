"""
Generic multi-language extractor via tree-sitter-language-pack + queries.

MVP goal:
- symbols: classes/functions/methods
- imports: best-effort local path resolution for JS/TS (and minimal for others)
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from tree_sitter import Node as TSNode
from tree_sitter_language_pack import get_language, get_parser

from codex_mesh.core.edges import Edge, EdgeType
from codex_mesh.core.nodes import BaseNode, ClassNode, FileNode, FunctionNode

from .import_resolvers import resolve_import_resolver
from .protocols import ExtractionResult, ExtractorContext, PendingCall, PendingImport

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class QueryBundle:
    """
    Queries for extracting language constructs via tree-sitter.

    Each field is a tree-sitter query string. Capture names:
    - @name / @class_name / @func_name / @method_name: Symbol identifiers
    - @decorator: Decorator nodes
    - @modifier: Access modifiers, async keywords, etc.
    - @entrypoint: Entry point markers
    - @source: Import source path
    - @imported_name: Individual imported name
    - @alias: Alias for imported name
    - @star_import: Star/wildcard import marker
    - @callee / @receiver: Call expression parts
    - @base: Base class/interface
    """

    classes: str | None
    functions: str | None
    methods: str | None
    imports: str | None
    calls: str | None = None
    bases: str | None = None
    decorators: str | None = None
    modifiers: str | None = None
    entrypoints: str | None = None
    # Async detection - captures "async" keyword in function contexts
    async_markers: str | None = None


class TreeSitterQueryExtractor:
    def __init__(
        self,
        *,
        language_id: str,
        extensions: tuple[str, ...],
        ts_lang_key: str,
        queries: QueryBundle,
    ) -> None:
        self.language_id = language_id
        self.extensions = extensions
        self._ts_lang_key = ts_lang_key
        # Lazy initialization might be safer if import fails, but the language pack can still be incomplete.
        # Never crash registration if a grammar isn't available in the installed pack.
        self._init_error: str | None = None
        try:
            self._language = get_language(ts_lang_key)  # type: ignore
            self._parser = get_parser(ts_lang_key)  # type: ignore
        except Exception as e:
            self._language = None  # type: ignore
            self._parser = None  # type: ignore
            self._init_error = str(e)
            logger.warning(
                "Tree-sitter language '%s' unavailable; extractor '%s' disabled: %s",
                ts_lang_key,
                language_id,
                e,
            )
        self._queries = queries
        # Caches (extractors are reused across files/projects)
        self._compiled_query_cache: dict[str, Any] = {}
        # Import resolver cache: (root, file_path_parent, raw_import) -> (candidates, is_external)
        self._import_cache: dict[tuple[str, str, str], tuple[tuple[str, ...], bool]] = {}

    def extract(self, ctx: ExtractorContext, file_node: FileNode, content: str) -> ExtractionResult:
        if self._parser is None:
            # Grammar missing / extractor disabled
            return ExtractionResult(nodes=[], edges=[], pending_imports=[], pending_calls=[])

        try:
            tree = self._parser.parse(bytes(content, "utf8"))
            root = tree.root_node
        except Exception as e:
            logger.warning("Extraction error for %s: %s", self.language_id, e)
            # Fallback for empty content or parse errors
            return ExtractionResult(nodes=[], edges=[], pending_imports=[], pending_calls=[])

        nodes: list[BaseNode] = []
        edges: list[Edge] = []
        pending_imports: list[PendingImport] = []
        pending_calls: list[PendingCall] = []

        content_bytes = content.encode("utf-8", errors="replace")
        lines = content.splitlines()

        bases_by_class: dict[str, list[str]] = {}
        if self._queries.bases:
            bases_by_class = self._run_bases_query(root, self._queries.bases)

        # Symbols - Single Pass to handle interleaved decorators/modifiers
        # We rewrite specific capture names to differentiate kinds
        combined_parts = []
        if self._queries.classes:
            combined_parts.append(self._queries.classes.replace("@name", "@class_name"))
        if self._queries.methods:
            combined_parts.append(self._queries.methods.replace("@name", "@method_name"))
        if self._queries.functions:
            combined_parts.append(self._queries.functions.replace("@name", "@func_name"))
        if self._queries.decorators:
            combined_parts.append(self._queries.decorators)
        if self._queries.modifiers:
            combined_parts.append(self._queries.modifiers)
        if self._queries.entrypoints:
            combined_parts.append(self._queries.entrypoints)

        full_query = "\n".join(combined_parts)

        symbol_nodes = self._run_symbol_query(
            ctx.relative_path, root, content_bytes, lines, full_query, bases_by_class=bases_by_class
        )
        nodes.extend(symbol_nodes)

        for n in nodes:
            edges.append(Edge.create(file_node.id, n.id, EdgeType.CONTAINS))

        # Inheritance edges (local-only, like Python MVP)
        class_by_name = {c.name: c for c in nodes if isinstance(c, ClassNode)}
        for c in nodes:
            if not isinstance(c, ClassNode):
                continue
            for base in c.bases:
                # Naive resolution for local classes: check if base name matches any class in file
                # Often bases are qualified like "foo.Bar", we check "Bar"
                base_name = base.split(".")[-1].split("::")[-1]
                if base_name in class_by_name:
                    edges.append(Edge.create(c.id, class_by_name[base_name].id, EdgeType.INHERITS))

        # Imports (best-effort) - now with detailed metadata
        if self._queries.imports:
            for imp_info in self._run_import_query(root, self._queries.imports):
                raw = imp_info.get("raw", "")
                if not raw:
                    continue
                candidates, is_external = self._import_candidates(
                    ctx.file_path, ctx.project_root, raw
                )
                pending_imports.append(
                    PendingImport(
                        source_file_id=file_node.id,
                        raw=raw,
                        candidates=candidates,
                        is_external=is_external,
                        imported_names=imp_info.get("imported_names"),
                        alias_map=imp_info.get("alias_map"),
                        is_star=imp_info.get("is_star", False),
                        kind=imp_info.get("kind", "import"),
                        module=raw,
                    )
                )

        # Merge defaults with language-specific extra call queries
        call_queries: list[str] = []
        if self._queries.calls:
            call_queries.append(self._queries.calls)

        # Add extra call queries if any defined for this language
        if self.language_id in _EXTRA_CALL_QUERIES:
            call_queries.append(_EXTRA_CALL_QUERIES[self.language_id])

        if call_queries:
            combined_calls = "\n".join(call_queries)
            # First, build spans for local functions to map calls to callers
            spans = self._build_function_spans([n for n in nodes if isinstance(n, FunctionNode)])
            pending_calls.extend(
                self._extract_calls_generic(root, spans, ctx.relative_path, combined_calls)
            )

        return ExtractionResult(
            nodes=nodes, edges=edges, pending_imports=pending_imports, pending_calls=pending_calls
        )

    def _compile_query(self, query_src: str):
        if self._language is None:
            return None
        if query_src in self._compiled_query_cache:
            return self._compiled_query_cache[query_src]

        try:
            from tree_sitter import Query

            q = Query(self._language, query_src)
            self._compiled_query_cache[query_src] = q
            return q
        except Exception as e:
            # Critical fix: never crash extraction due to query mismatch
            logger.warning("Failed to compile query for %s: %s", self.language_id, e)
            self._compiled_query_cache[query_src] = None
            return None

    def _ts_captures(self, q: Any, root: TSNode):
        """Return query captures across tree-sitter binding variants."""
        # Prefer Query.captures if available (tree-sitter >=0.22).
        try:
            return q.captures(root)
        except Exception:
            pass

        # Fallback: QueryCursor variants
        try:
            from tree_sitter import QueryCursor  # type: ignore

            try:
                cursor = QueryCursor(q)  # type: ignore # older/alternate bindings
                return cursor.captures(root)
            except TypeError:
                cursor = QueryCursor()  # type: ignore
                for args in ((q, root), (root, q)):
                    try:
                        return cursor.captures(*args)
                    except TypeError:
                        continue
        except Exception:
            pass

        return []

    def _ts_matches(self, q: Any, root: TSNode):
        """Return query matches across tree-sitter binding variants."""
        try:
            return q.matches(root)
        except Exception:
            pass

        try:
            from tree_sitter import QueryCursor  # type: ignore

            try:
                cursor = QueryCursor(q)  # type: ignore
                return cursor.matches(root)
            except TypeError:
                cursor = QueryCursor()  # type: ignore
                for args in ((q, root), (root, q)):
                    try:
                        return cursor.matches(*args)
                    except TypeError:
                        continue
        except Exception:
            pass

        return []

    def _run_symbol_query(
        self,
        rel_path: str,
        root: TSNode,
        content_bytes: bytes,
        lines: list[str],
        query_src: str | None,
        *,
        bases_by_class: dict[str, list[str]] | None = None,
    ) -> list[BaseNode]:
        if query_src is None:
            return []
        q = self._compile_query(query_src)
        if q is None:
            return []
        captures_raw = self._ts_captures(q, root)

        if not captures_raw:
            return []

        out: list[BaseNode] = []

        query_captures: list[tuple[TSNode, str]] = []
        if isinstance(captures_raw, dict):
            for name, nodes_list in captures_raw.items():
                for n in nodes_list:
                    query_captures.append((n, name))
        else:
            # In some versions/bindings it might be a list
            query_captures = captures_raw  # type: ignore

        # Sort captures by position to handle interleaved decorators/modifiers properly
        # If position is same, priority: auxiliary before primary
        def capture_priority(name: str) -> int:
            if name in ("decorator", "modifier", "entrypoint"):
                return 0
            return 1

        query_captures.sort(key=lambda x: (x[0].start_byte, capture_priority(x[1])))

        pending_decorators: list[str] = []
        pending_modifiers: list[str] = []
        pending_meta: dict[str, Any] = {}
        explicit_receiver: str | None = None

        for node, cap_name in query_captures:
            text = self._safe_node_text(node).strip()
            if not text:
                continue

            if cap_name == "decorator":
                clean_text = text.lstrip("@").strip()
                pending_decorators.append(clean_text)
                continue
            if cap_name == "modifier":
                pending_modifiers.append(text)
                continue
            if cap_name == "entrypoint":
                pending_meta["is_entrypoint"] = True
                continue
            if cap_name == "receiver_type":
                explicit_receiver = text
                continue

            kind = None
            if cap_name == "class_name":
                kind = "class"
            elif cap_name == "func_name":
                kind = "function"
            elif cap_name == "method_name":
                kind = "method"
            else:
                continue

            name = text

            decl = self._find_decl_ancestor(node, kind) or node
            line_start = decl.start_point[0] + 1
            line_end = decl.end_point[0] + 1

            doc = self._extract_doc_comment(lines, line_start)
            sig = None
            if kind in ("function", "method"):
                sig = self._extract_signature(content_bytes, decl)

            # Try to detect enclosing class for methods
            class_name = explicit_receiver
            if kind == "method" and not class_name:
                class_name = self._enclosing_class_name(node)

            # Use collected decorators/modifiers (copying)
            decos = list(pending_decorators)
            mods = list(pending_modifiers)
            meta_dict = pending_meta.copy()

            # Clear for next symbol
            pending_decorators.clear()
            pending_modifiers.clear()
            pending_meta.clear()
            explicit_receiver = None

            if kind == "class":
                out.append(
                    ClassNode.create(
                        name=name,
                        file_path=rel_path,
                        line_start=line_start,
                        line_end=line_end,
                        docstring=doc,
                        bases=(bases_by_class or {}).get(name, []),
                        decorators=decos,
                        modifiers=mods,
                        meta=meta_dict,
                    )
                )
            else:
                # function or method
                out.append(
                    FunctionNode.create(
                        name=name,
                        file_path=rel_path,
                        line_start=line_start,
                        line_end=line_end,
                        docstring=doc,
                        signature=sig,
                        is_method=(kind == "method") or bool(class_name),
                        class_name=class_name,
                        decorators=decos,
                        modifiers=mods,
                        meta=meta_dict,
                    )
                )

        return out

    def _safe_node_text(self, node: TSNode) -> str:
        if node.text is None:
            return ""
        try:
            return node.text.decode("utf-8")
        except UnicodeDecodeError:
            return ""

    def _find_decl_ancestor(self, node: TSNode, kind: str) -> TSNode | None:
        """Climb up to find declaration node for better spans."""
        # This list depends on grammar, but we can try common ones
        if kind == "class":
            primaries = {
                "class_declaration",
                "class_definition",
                "class_specifier",
                "struct_specifier",
                "struct_item",
                "interface_declaration",
                "object_definition",
                "type_spec",
            }
        elif kind == "method":
            primaries = {
                "method_definition",
                "method_declaration",
                "method",
                "constructor_declaration",
                "impl_item",
            }
        else:
            primaries = {
                "function_declaration",
                "function_definition",
                "function_item",
                "function_signature",
                "function_declarator",
                "method_declaration",
            }

        wrappers = {"export_statement", "decorated_definition"}

        p: TSNode | None = node
        best_p: TSNode | None = None
        # First find the primary declaration node
        while p:
            if p.type in primaries:
                best_p = p
                break
            p = p.parent

        if not best_p:
            return node

        # Then climb through wrappers
        curr = best_p
        while curr.parent and curr.parent.type in wrappers:
            curr = curr.parent
        return curr

    def _extract_doc_comment(self, lines: list[str], line_start_1based: int) -> str | None:
        """Extract doc comment immediately above."""
        i = line_start_1based - 2
        if i < 0 or i >= len(lines):
            return None
        while i >= 0 and not lines[i].strip():
            i -= 1
        if i < 0:
            return None

        # Check for block end */
        if "*/" in lines[i]:
            # scan up for /*
            end = i
            start = i
            while start >= 0:
                if "/*" in lines[start]:
                    break
                start -= 1
            if start < 0:
                return None
            # Extract content
            chunk = lines[start : end + 1]
            # Simple cleanup: remove /*, *, */
            cleaned = []
            for ln in chunk:
                s = ln.strip()
                s = re.sub(r"^/\*+", "", s)
                s = re.sub(r"\*+/$", "", s)
                s = s.lstrip("*").strip()
                if s:
                    cleaned.append(s)
            return "\n".join(cleaned) or None

        # Check for single line prefixes
        prefixes = ["///", "//", "#"]  # Generic
        found = []
        curr = i
        while curr >= 0:
            line = lines[curr].strip()
            matched = False
            for p in prefixes:
                if line.startswith(p):
                    found.append(line[len(p) :].strip())
                    matched = True
                    break
            if not matched:
                break
            curr -= 1

        if found:
            return "\n".join(reversed(found)) or None
        return None

    def _extract_signature(self, content_bytes: bytes, decl: TSNode) -> str | None:
        start = decl.start_byte
        # Limit to 500 chars to avoid huge output
        end = min(decl.end_byte, start + 500)
        text = content_bytes[start:end].decode("utf-8", errors="replace")
        # Cut at first {, ;, or newline
        for sep in ["{", ";", "\n"]:
            if sep in text:
                text = text.split(sep)[0]
        text = re.sub(r"\s+", " ", text).strip()
        return text or None

    def _run_bases_query(self, root: TSNode, query_src: str) -> dict[str, list[str]]:
        if not query_src:
            return {}
        q = self._compile_query(query_src)
        if not q:
            return {}
        captures_raw = self._ts_captures(q, root)

        if not captures_raw:
            return {}

        query_captures: list[tuple[TSNode, str]] = []
        if isinstance(captures_raw, dict):
            for name, nodes_list in captures_raw.items():
                for n in nodes_list:
                    query_captures.append((n, name))
        else:
            query_captures = captures_raw  # type: ignore

        bases_by_cls: dict[str, list[str]] = {}
        for node, cap_name in query_captures:
            if cap_name != "base":
                continue

            cls = self._enclosing_class_name(node)
            if not cls:
                continue

            base = self._safe_node_text(node).strip()
            if base:
                bases_by_cls.setdefault(cls, []).append(base)
        return bases_by_cls

    def _run_import_query(self, root: TSNode, query_src: str) -> list[dict[str, Any]]:
        """
        Execute import query and return detailed import metadata.
        Uses matches() to group captures by statement.
        """
        if not query_src:
            return []
        q = self._compile_query(query_src)
        if not q:
            return []
        matches = self._ts_matches(q, root)

        if not matches:
            return []

        # Merge matches by source node (the @source capture)
        merged_imports: dict[TSNode, dict[str, Any]] = {}

        for match in matches:
            # captures is often a dict {name: [nodes]} in newer tree-sitter or similar structure
            captures = (
                match[1] if isinstance(match, (list, tuple)) else getattr(match, "captures", {})
            )

            # Every import hit should have at least one @source capture
            source_nodes = captures.get("source", [])
            if not source_nodes:
                continue
            source_node = source_nodes[0]

            if source_node not in merged_imports:
                text = self._safe_node_text(source_node).strip().strip('"').strip("'")
                merged_imports[source_node] = {
                    "raw": text,
                    "imported_names": set(),
                    "alias_map": {},
                    "is_star": False,
                    "kind": self._detect_import_kind(source_node),
                }

            imp_info = merged_imports[source_node]

            if "star_import" in captures:
                imp_info["is_star"] = True

            # Extract names and aliases
            names = [self._safe_node_text(n).strip() for n in captures.get("imported_name", [])]
            aliases = [self._safe_node_text(n).strip() for n in captures.get("alias", [])]

            for name in names:
                imp_info["imported_names"].add(name)

            # Pairing aliases: if we have (name, alias) in the same match, we pair them.
            # This works if the query groups them like (import_specifier name: (x) @imported_name alias: (y) @alias)
            if len(names) == 1 and len(aliases) == 1:
                imp_info["alias_map"][names[0]] = aliases[0]
            elif not names and len(aliases) == 1 and imp_info["is_star"]:
                # import * as alias -> record alias for the "star" module?
                # We'll put it in alias_map under "*" or just ignore for now as per Python MVP
                pass

        # Finalize results
        out: list[dict[str, Any]] = []
        for info in merged_imports.values():
            if info["imported_names"]:
                info["imported_names"] = tuple(sorted(info["imported_names"]))
            else:
                info["imported_names"] = None

            if not info["alias_map"]:
                info["alias_map"] = None

            out.append(info)

        return out

    def _detect_import_kind(self, node: TSNode) -> str:
        """
        Detect the kind of import statement from the AST node context.

        Returns: 'import', 'from', 'require', 'use', 'using', 'include', etc.
        """
        # Walk up to find the import statement type
        p = node.parent
        while p is not None:
            node_type = p.type.lower()
            if "import_from" in node_type or "from_import" in node_type:
                return "from"
            if "import" in node_type:
                return "import"
            if "require" in node_type:
                return "require"
            if "use_declaration" in node_type or "use_" in node_type:
                return "use"
            if "using" in node_type:
                return "using"
            if "include" in node_type:
                return "include"
            if "preproc_include" in node_type:
                return "include"
            p = p.parent
        return "import"  # Default

    def _run_calls_query(self, root: TSNode, query_src: str) -> list[dict[str, Any]]:
        if not query_src:
            return []
        q = self._compile_query(query_src)
        if not q:
            return []
        matches = self._ts_matches(q, root)

        if not matches:
            return []

        out: list[dict[str, Any]] = []
        for match in matches:
            # Each match represents ONE call site with multiple captures (@callee, @receiver)
            call_info: dict[str, Any] = {"callee": None, "receiver": None, "line": None}
            # match is (pattern_index, captures_dict) or similar depending on version
            # Usually Match(pattern_index, captures={name: nodes})
            captures = (
                match[1] if isinstance(match, (list, tuple)) else getattr(match, "captures", {})
            )

            # For calls as well
            for cap_name, nodes in captures.items():
                node = nodes[0] if nodes else None
                if not node:
                    continue

                # Check for @callee or @call.method or @call.function
                # to support more fine-grained queries
                if cap_name in ("callee", "call.method", "call.function"):
                    call_info["callee"] = self._safe_node_text(node).strip()
                    call_info["line"] = node.start_point[0] + 1
                elif cap_name == "receiver":
                    call_info["receiver"] = self._safe_node_text(node).strip()

            if call_info["callee"]:
                out.append(call_info)
        return out

    def _build_function_spans(self, nodes: list[FunctionNode]) -> list[tuple[int, int, str]]:
        """Build (start, end, func_id) list for hit testing."""
        # Filter and sort
        out = []
        for n in nodes:
            out.append((n.line_start, n.line_end, n.id))
        out.sort(key=lambda x: x[0])
        return out

    def _extract_calls_generic(
        self, root: TSNode, spans: list[tuple[int, int, str]], rel_path: str, call_query: str
    ) -> list[PendingCall]:
        # We need _run_calls_query to get all call sites
        if not call_query:
            return []

        raw_calls = self._run_calls_query(root, call_query)
        pending = []

        # Optimize matching: for each call, determine which function span contains it
        # Spans are sorted by start line. We can binary search or just linear scan since it's typically small per file.
        # However, nested functions exists. We want the tightest span.

        for call_info in raw_calls:
            callee = call_info["callee"]
            line = call_info["line"]
            receiver = call_info["receiver"]

            best_id = None
            best_len = 999999

            for start, end, fid in spans:
                if start <= line <= end:
                    msg_len = end - start
                    if msg_len < best_len:
                        best_len = msg_len
                        best_id = fid

            if best_id:
                pending.append(
                    PendingCall(
                        source_id=best_id,
                        callee_name=callee,
                        file_path=rel_path,
                        line=line,
                        receiver=receiver,
                    )
                )
        return pending

    def _enclosing_class_name(self, node: TSNode) -> str | None:
        """
        Find the enclosing class name for a node (used for method detection).
        """
        # All known class-like node types across languages
        class_node_types = {
            # Common
            "class_declaration",
            "class_definition",
            "class_specifier",
            # C++
            "struct_specifier",
            # Rust
            "struct_item",
            "impl_item",
            # Go
            "type_spec",
            # Kotlin/Scala
            "object_declaration",
            "object_definition",
            "trait_definition",
            # Ruby
            "class",
            "module",
            # PHP
            "trait_declaration",
            "interface_declaration",
            # Enums/Records
            "enum_declaration",
            "mixin_declaration",
        }

        p = node.parent
        while p is not None:
            if p.type in class_node_types:
                # Rust impl block - get the type being implemented
                if p.type == "impl_item":
                    type_node = p.child_by_field_name("type")
                    if type_node:
                        return self._safe_node_text(type_node)

                # Try common field names for class name
                for field_name in ("name", "type", "superclass"):
                    nm = p.child_by_field_name(field_name)
                    if nm and nm.type in (
                        "identifier",
                        "type_identifier",
                        "simple_identifier",
                        "constant",
                    ):
                        return self._safe_node_text(nm)

                # Fallback: look for identifier-like first child
                for child in p.named_children:
                    if child.type in (
                        "identifier",
                        "type_identifier",
                        "simple_identifier",
                        "property_identifier",
                        "field_identifier",
                        "constant",  # Ruby
                    ):
                        return self._safe_node_text(child)

            p = p.parent
        return None

    def _import_candidates(
        self, file_path: Path, project_root: Path, raw: str
    ) -> tuple[tuple[str, ...], bool]:
        """
        Best-effort import resolution using language-specific strategies.
        """
        raw = raw.strip()
        cache_key = (self.language_id, str(file_path.parent), raw)

        if cache_key in self._import_cache:
            return self._import_cache[cache_key]

        resolver = resolve_import_resolver(self.language_id)
        candidates = resolver.resolve(project_root, file_path, raw)

        # Boolean is "is_external"; if candidates found, then local (False), else likely external (True)
        # However, empty candidates can also mean "internal but failed to resolve".
        # We assume if resolver returns nothing, it's either external or unresolvable.
        # For our purposes, treating it as external (no edge) is safe.

        # Exception: JS/TS often has clear external indicators (no ./ or /).
        # We trust the resolver to return candidates only if local.

        is_external = len(candidates) == 0

        res = (tuple(sorted(candidates)), is_external)
        self._import_cache[cache_key] = res
        return res


# ---------------------------------------------------------------------
# Extra/Fallback Call Queries for languages not covered by main bundles
# ---------------------------------------------------------------------

_EXTRA_CALL_QUERIES = {
    "go": """
        (call_expression
            function: (selector_expression operand: (_) @receiver field: (field_identifier) @callee)
        )
    """,
    "ruby": """
        (call
            method: (identifier) @callee
            receiver: (_)? @receiver
        )

    """,
    "rust": """
        (call_expression
            function: (identifier) @callee
        )


    """,
    "cpp": """
        (call_expression
            function: (identifier) @callee
        )

    """,
    "c_sharp": """
        (invocation_expression
            function: [
                (identifier) @callee
                (member_access_expression name: (identifier) @callee expression: (_) @receiver)
            ]
        )

    """,
}
