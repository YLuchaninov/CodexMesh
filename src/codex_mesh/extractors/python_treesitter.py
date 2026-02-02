"""
Python extractor (Tree-sitter) extracted from core/graph.py.

Goal: keep "richer" Python MVP (classes, functions, methods, docstrings, calls, imports),
but decouple it from CodeGraphBuilder.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass

from tree_sitter import Language, Parser
from tree_sitter import Node as TSNode

from codex_mesh.core.edges import Edge, EdgeType
from codex_mesh.core.nodes import BaseNode, ClassNode, FileNode, FunctionNode

from .protocols import ExtractionResult, ExtractorContext, PendingCall, PendingImport


@dataclass(frozen=True)
class _FuncSpan:
    node_id: str
    start: int
    end: int


class PythonTreeSitterExtractor:
    language_id: str = "python"
    extensions: tuple[str, ...] = (".py",)

    _language: Language | None
    _parser: Parser | None

    def __init__(self) -> None:
        try:
            import tree_sitter_python as tspython

            self._language = Language(tspython.language())
            self._parser = Parser(self._language)
            self._init_error = None
        except Exception as e:
            self._language = None
            self._parser = None
            self._init_error = str(e)

    def extract(self, ctx: ExtractorContext, file_node: FileNode, content: str) -> ExtractionResult:
        if self._parser is None:
            # Soft fail if grammar/parser failed to initialize
            return ExtractionResult(
                nodes=[],
                edges=[],
                pending_imports=[],
                pending_calls=[],
            )

        tree = self._parser.parse(bytes(content, "utf8"))
        root = tree.root_node

        nodes: list[BaseNode] = []
        edges: list[Edge] = []
        pending_imports: list[PendingImport] = []
        pending_calls: list[PendingCall] = []

        # 1) Classes + methods + functions
        classes = self._extract_classes(file_node.relative_path, root)
        functions = self._extract_functions(file_node.relative_path, root)
        methods = self._extract_methods(file_node.relative_path, root)

        # 1.1) Main guard detection
        main_calls = self._extract_main_guard_calls(root)
        if main_calls:
            # Mark functions called in main guard as entrypoints
            for f in functions:
                if f.name in main_calls:
                    # Add metadata marker
                    if f.meta is None:
                        f.meta = {}
                    f.meta["is_main_guard"] = True

        nodes.extend(classes)
        nodes.extend(functions)
        nodes.extend(methods)

        # File contains symbols
        for n in nodes:
            edges.append(Edge.create(file_node.id, n.id, EdgeType.CONTAINS))

        # Inheritance edges
        class_by_name = {c.name: c for c in classes}
        for c in classes:
            for base in c.bases:
                base_name = base.split(".")[-1]
                if base_name in class_by_name:
                    edges.append(Edge.create(c.id, class_by_name[base_name].id, EdgeType.INHERITS))

        # 2) Imports (pending, resolve in builder)
        for imp_info in self._extract_imports(root):
            candidates, is_external = self._python_import_candidates(
                ctx.relative_path, imp_info["raw"]
            )
            pending_imports.append(
                PendingImport(
                    source_file_id=file_node.id,
                    raw=imp_info["raw"],
                    candidates=candidates,
                    is_external=is_external,
                    imported_names=imp_info.get("imported_names"),
                    alias_map=imp_info.get("alias_map"),
                    is_star=imp_info.get("is_star", False),
                    kind=imp_info.get("kind"),
                    module=imp_info["raw"],
                )
            )

        # 3) Calls (pending, resolve in builder)
        spans = self._build_function_spans(functions + methods)
        for call in self._extract_calls(root, spans, file_node.relative_path):
            pending_calls.append(call)

        return ExtractionResult(
            nodes=nodes,
            edges=edges,
            pending_imports=pending_imports,
            pending_calls=pending_calls,
        )

    def _extract_docstring(self, node: TSNode) -> str | None:
        body = None
        for child in node.children:
            if child.type == "block":
                body = child
                break

        if body and body.children:
            first_stmt = body.children[0]
            if first_stmt.type == "expression_statement" and first_stmt.children:
                expr = first_stmt.children[0]
                if expr.type == "string" and expr.text:
                    s = expr.text.decode("utf-8")
                    for q in ('"""', "'''", '"', "'"):
                        if s.startswith(q) and s.endswith(q):
                            s = s[len(q) : -len(q)]
                            break
                    return s.strip()
        return None

    def _extract_classes(self, rel_path: str, root: TSNode) -> list[ClassNode]:
        out: list[ClassNode] = []

        def walk(n: TSNode) -> None:
            if n.type == "class_definition":
                name_node = n.child_by_field_name("name")
                if not name_node:
                    return

                name = name_node.text.decode("utf-8") if name_node.text else ""
                doc = self._extract_docstring(n)
                bases = self._extract_python_bases(n)
                decorators = self._extract_decorators(n)

                out.append(
                    ClassNode.create(
                        name=name,
                        file_path=rel_path,
                        line_start=n.start_point[0] + 1,
                        line_end=n.end_point[0] + 1,
                        docstring=doc,
                        bases=bases,
                        decorators=decorators,
                    )
                )
                return

            for ch in n.children:
                walk(ch)

        walk(root)
        return out

    def _extract_functions(self, rel_path: str, root: TSNode) -> list[FunctionNode]:
        out: list[FunctionNode] = []

        def walk(n: TSNode) -> None:
            if n.type == "function_definition":
                # ignore methods here (handled separately)
                if self._enclosing_class_name(n) is not None:
                    return

                name_node = n.child_by_field_name("name")
                if not name_node:
                    return

                name = name_node.text.decode("utf-8") if name_node.text else ""
                doc = self._extract_docstring(n)
                decorators = self._extract_decorators(n)
                modifiers = []
                if (
                    n.parent and n.parent.type == "async_function_definition"
                ):  # TS quirk or just check children?
                    # Python TS often wraps async def in function_definition but has 'async' keyword?
                    # Let's check children for 'async'
                    pass

                # Check for async
                # In tree-sitter-python, 'async' keyword often precedes 'def' or is part of structure.
                # Actually newer grammar has `async_function_definition` node type?
                # Let's check n.parent.type if implementation differs, but usually it's a property.
                # Simplest check: search children for "async" keyword
                for ch in n.children:
                    if ch.type == "async":
                        modifiers.append("async")
                        break

                out.append(
                    FunctionNode.create(
                        name=name,
                        file_path=rel_path,
                        line_start=n.start_point[0] + 1,
                        line_end=n.end_point[0] + 1,
                        docstring=doc,
                        is_method=False,
                        class_name=None,
                        decorators=decorators,
                        modifiers=modifiers,
                    )
                )
                return

            for ch in n.children:
                walk(ch)

        walk(root)
        return out

    def _extract_methods(self, rel_path: str, root: TSNode) -> list[FunctionNode]:
        out: list[FunctionNode] = []

        def walk(n: TSNode) -> None:
            if n.type == "function_definition":
                cls = self._enclosing_class_name(n)
                if not cls:
                    return
                name_node = n.child_by_field_name("name")
                if not name_node:
                    return

                name = name_node.text.decode("utf-8") if name_node.text else ""
                doc = self._extract_docstring(n)
                decorators = self._extract_decorators(n)
                modifiers = []
                for ch in n.children:
                    if ch.type == "async":
                        modifiers.append("async")
                        break

                out.append(
                    FunctionNode.create(
                        name=name,
                        file_path=rel_path,
                        line_start=n.start_point[0] + 1,
                        line_end=n.end_point[0] + 1,
                        docstring=doc,
                        is_method=True,
                        class_name=cls,
                        decorators=decorators,
                        modifiers=modifiers,
                    )
                )
                return

            for ch in n.children:
                walk(ch)

        walk(root)
        return out

    def _enclosing_class_name(self, node: TSNode) -> str | None:
        p = node.parent
        while p is not None:
            if p.type == "class_definition":
                name_node = p.child_by_field_name("name")
                return name_node.text.decode("utf-8") if name_node and name_node.text else None
            p = p.parent
        return None

    def _extract_python_bases(self, class_node: TSNode) -> list[str]:
        bases: list[str] = []
        supers = class_node.child_by_field_name("superclasses")
        if not supers:
            return bases

        # superclasses is typically an argument_list
        for ch in supers.children:
            if ch.type in {"identifier", "attribute"} and ch.text:
                bases.append(ch.text.decode("utf-8"))
        return bases

    def _extract_decorators(self, node: TSNode) -> list[str]:
        """Extract decorators from a function or class node."""
        decorators: list[str] = []
        p = node.parent
        # In tree-sitter-python, decorators wrap the definition:
        # (decorated_definition (decorator) (function_definition))
        # So we look at parent if it is a decorated_definition
        if p and p.type == "decorated_definition":
            for ch in p.children:
                if ch.type == "decorator" and ch.text:
                    decorators.append(ch.text.decode("utf-8").strip())
        return decorators

    def _extract_main_guard_calls(self, root: TSNode) -> list[str]:
        """Detect functions called inside 'if __name__ == "__main__":'."""
        calls: list[str] = []

        def is_main_guard(n: TSNode) -> bool:
            if n.type != "if_statement":
                return False
            cond = n.child_by_field_name("condition")
            if not cond:
                return False
            # Look for __name__ == "__main__" or "__name__" == '__main__'
            text = cond.text.decode("utf-8") if cond.text else ""
            return "__name__" in text and "__main__" in text

        def walk(n: TSNode) -> None:
            if is_main_guard(n):
                # Found the guard. Now look for calls in its body.
                # Consequence is the 'then' block
                body = n.child_by_field_name("consequence")
                if body:

                    def find_calls(sub: TSNode):
                        if sub.type == "call":
                            fn = sub.child_by_field_name("function")
                            if fn and fn.text:
                                calls.append(fn.text.decode("utf-8"))
                        for c in sub.children:
                            find_calls(c)

                    find_calls(body)
                return

            for ch in n.children:
                walk(ch)

        walk(root)
        return calls

    def _extract_imports(self, root: TSNode) -> list[dict]:
        """
        Extract detailed import information from Python source.

        Returns list of dicts with:
        - raw: The raw module string (e.g., 'os.path' or 'utils')
        - imported_names: Specific names imported (e.g., ('join', 'exists'))
        - alias_map: Mapping of original to alias (e.g., {'join': 'pjoin'})
        - is_star: Whether it's a star import (from x import *)
        - kind: 'import' or 'from'
        """
        imports: list[dict] = []

        def walk(n: TSNode) -> None:
            if n.type == "import_statement":
                # import a, b as c
                for ch in n.children:
                    if ch.type == "dotted_name" and ch.text:
                        imports.append(
                            {
                                "raw": ch.text.decode("utf-8"),
                                "imported_names": None,
                                "alias_map": None,
                                "is_star": False,
                                "kind": "import",
                            }
                        )
                    elif ch.type == "aliased_import":
                        # import foo as bar
                        name_node = ch.child_by_field_name("name")
                        alias_node = ch.child_by_field_name("alias")
                        if name_node and name_node.text:
                            raw = name_node.text.decode("utf-8")
                            alias_map = None
                            if alias_node and alias_node.text:
                                alias_map = {raw: alias_node.text.decode("utf-8")}
                            imports.append(
                                {
                                    "raw": raw,
                                    "imported_names": None,
                                    "alias_map": alias_map,
                                    "is_star": False,
                                    "kind": "import",
                                }
                            )

            elif n.type == "import_from_statement":
                # from x import y, z as w
                mod = n.child_by_field_name("module_name")
                raw = mod.text.decode("utf-8") if mod and mod.text else ""

                imported_names: list[str] = []
                from_alias_map: dict[str, str] = {}
                is_star = False

                for ch in n.children:
                    if ch.type == "wildcard_import":
                        is_star = True
                    elif ch.type == "dotted_name" and ch != mod:
                        # from x import name (without alias)
                        if ch.text:
                            imported_names.append(ch.text.decode("utf-8"))
                    elif ch.type == "aliased_import":
                        name_node = ch.child_by_field_name("name")
                        alias_node = ch.child_by_field_name("alias")
                        if name_node and name_node.text:
                            name = name_node.text.decode("utf-8")
                            imported_names.append(name)
                            if alias_node and alias_node.text:
                                from_alias_map[name] = alias_node.text.decode("utf-8")

                if raw:
                    imports.append(
                        {
                            "raw": raw,
                            "imported_names": tuple(imported_names) if imported_names else None,
                            "alias_map": from_alias_map if from_alias_map else None,
                            "is_star": is_star,
                            "kind": "from",
                        }
                    )

            for ch in n.children:
                walk(ch)

        walk(root)
        return imports

    def _python_import_candidates(self, rel_path: str, raw: str) -> tuple[tuple[str, ...], bool]:
        """
        Convert python module import to candidate local file paths.

        Example: "utils" -> ("utils.py", "utils/__init__.py")
        """
        # Treat stdlib/externals as external by default unless it looks like relative local module
        is_external = not bool(re.match(r"^[a-zA-Z_]\w*(\.[a-zA-Z_]\w*)*$", raw))
        module_path = raw.replace(".", "/")
        candidates = (f"{module_path}.py", f"{module_path}/__init__.py")
        return candidates, is_external

    def _build_function_spans(self, funcs: Iterable[FunctionNode]) -> list[_FuncSpan]:
        spans: list[_FuncSpan] = []
        for f in funcs:
            spans.append(_FuncSpan(node_id=f.id, start=f.line_start, end=f.line_end))
        return spans

    def _extract_calls(
        self, root: TSNode, spans: list[_FuncSpan], rel_path: str
    ) -> list[PendingCall]:
        calls: list[PendingCall] = []

        def find_enclosing_function(line: int) -> str | None:
            for s in spans:
                if s.start <= line <= s.end:
                    return s.node_id
            return None

        def walk(n: TSNode) -> None:
            if n.type == "call":
                fn = n.child_by_field_name("function")
                if fn:
                    callee = None
                    receiver = None
                    if fn.type == "identifier" and fn.text:
                        callee = fn.text.decode("utf-8")
                    elif fn.type == "attribute":
                        attr = fn.child_by_field_name("attribute")
                        if attr and attr.text:
                            callee = attr.text.decode("utf-8")
                        obj = fn.child_by_field_name("object")
                        if obj and obj.text:
                            receiver = obj.text.decode("utf-8")

                    if callee:
                        line = n.start_point[0] + 1
                        src = find_enclosing_function(line)
                        if src:
                            calls.append(
                                PendingCall(
                                    source_id=src,
                                    callee_name=callee,
                                    file_path=rel_path,
                                    line=line,
                                    receiver=receiver,
                                )
                            )

            for ch in n.children:
                walk(ch)

        walk(root)
        return calls
