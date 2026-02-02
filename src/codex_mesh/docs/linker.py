from __future__ import annotations

import re

from ..core.edges import Edge, EdgeType
from ..core.nodes import ClassNode, DocSectionNode, FunctionNode

EXPLICIT_NODE_ID = re.compile(r"\b(?:function|class|method)::[^\s`]+")
DOTTED_METHOD_RE = re.compile(r"\b([A-Z][A-Za-z0-9_]+)\.([a-zA-Z_][a-zA-Z0-9_]*)\b")
IDENT_RE = re.compile(r"`([A-Za-z_][A-Za-z0-9_]*)`")


def _norm(s: str) -> str:
    return s.strip().lower()


def _extract_tokens_from_text(text: str) -> list[str]:
    tokens: list[str] = []
    tokens += EXPLICIT_NODE_ID.findall(text)
    tokens += [f"{a}.{b}" for a, b in DOTTED_METHOD_RE.findall(text)]
    tokens += list(IDENT_RE.findall(text))
    return list(dict.fromkeys(tokens))


class DocsLinker:
    def __init__(self, graph):
        self.graph = graph

    def resolve_links(self):
        # 1) Build symbol index
        by_name: dict[str, list[str]] = {}
        by_dotted: dict[str, str] = {}  # "Class.method" -> node_id
        node_id_set = set()

        for node in self.graph.get_all_nodes():
            node_id_set.add(node.id)
            if isinstance(node, ClassNode):
                by_name.setdefault(_norm(node.name), []).append(node.id)
            elif isinstance(node, FunctionNode):
                by_name.setdefault(_norm(node.name), []).append(node.id)
                if node.is_method and node.class_name:
                    by_dotted[_norm(f"{node.class_name}.{node.name}")] = node.id

        # 2) Link docs -> symbols
        doc_nodes = [n for n in self.graph.get_all_nodes() if isinstance(n, DocSectionNode)]

        new_edges = []
        for dn in doc_nodes:
            # Combine parsed refs and heuristics
            tokens = list(dn.refs)
            tokens.extend(_extract_tokens_from_text(dn.content))

            for t in set(tokens):  # dedup
                t_norm = _norm(t)
                target = None
                reason = "heuristic"
                confidence = 0.5

                # Explicit node_id
                if t.startswith(("function::", "class::", "method::")):
                    if t in node_id_set:
                        target = t
                        reason = "explicit"
                        confidence = 1.0

                # Class.method
                elif t_norm in by_dotted:
                    target = by_dotted[t_norm]
                    reason = "dotted_match"
                    confidence = 0.9

                # Bare identifier (class/function name)
                elif t_norm in by_name:
                    ids = by_name[t_norm]
                    if len(ids) == 1:
                        target = ids[0]
                        reason = "unique_name"
                        confidence = 0.7
                    else:
                        # Ambiguous
                        continue

                if target:
                    meta = {"confidence": confidence, "reason": reason, "status": "OK"}
                    # Add DOCS edge
                    new_edges.append(Edge.create(dn.id, target, EdgeType.DOCUMENTS, metadata=meta))
                    # Add DOCUMENTED_BY edge
                    new_edges.append(
                        Edge.create(target, dn.id, EdgeType.DOCUMENTED_BY, metadata=meta)
                    )

        return new_edges
