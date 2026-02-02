"""
Graph Service for CodexMesh Analysis.
"""

import logging
from typing import Any

from ...core.edges import EdgeType
from ...core.nodes import FileNode, FunctionNode
from ...review.graph_render import to_tree

logger = logging.getLogger(__name__)


class GraphService:
    """Handles graph traversal and analysis operations."""

    def __init__(self, service):
        self.service = service

    def get_subgraph(
        self,
        roots: str | list[str],
        depth: int = 1,
        direction: str = "both",
        edge_types: list[str] | None = None,
        max_nodes: int = 200,
    ) -> dict[str, Any]:
        """Get subgraph (nodes, edges) and mermaid."""
        if isinstance(roots, str):
            roots = [roots]

        et = self.service._parse_edge_types(edge_types)
        builder = self.service.call_graph_builder

        result = builder.build(
            roots=roots, depth=depth, direction=direction, edge_types=et, max_nodes=max_nodes
        )

        result["root"] = roots[0] if len(roots) == 1 else roots
        return result

    def get_dependency_tree(
        self,
        root_id: str,
        depth: int = 2,
        direction: str = "out",
        edge_types: list[str] | None = None,
    ) -> dict[str, Any]:
        """Get dependency tree."""
        server = self.service._get_server()
        et = self.service._parse_edge_types(edge_types)
        nodes, edges = server.graph_search.get_subgraph(root_id, depth, direction, et)

        tree = to_tree(nodes, edges, root_id)

        nodes_data = []
        for n in nodes:
            nodes_data.append(
                {
                    "id": n.id,
                    "name": n.name,
                    "type": n.node_type.value,
                    "file_path": self.service._node_file_path(n),
                    "span": {
                        "start_line": getattr(n, "line_start", 0),
                        "end_line": getattr(n, "line_end", 0),
                    },
                }
            )

        return {
            "root": root_id,
            "tree": tree,
            "nodes": nodes_data,
            "edges": edges,
            "direction": direction,
        }

    def compute_reachable_set(
        self, roots: list[str], edge_types: list[str], max_depth: int = 10, max_nodes: int = 1000
    ) -> dict[str, Any]:
        """Compute reachable set of nodes."""
        types = self.service._parse_edge_types(edge_types)
        ids, count = self.service._get_server().graph_search.compute_reachability(
            roots, max_depth, types
        )
        return {"reachable_ids": ids[:max_nodes], "reachable_count": count, "count": count}

    def find_dead_code(
        self, reachable_ids: list[str], mode: str = "conservative"
    ) -> dict[str, Any]:
        """Identify likely dead code."""
        server = self.service._get_server()
        all_nodes = server.graph_builder.graph.nodes()

        reachable_set = set(reachable_ids)
        dead_candidates = []

        from ...review.markdown_render import MarkdownRenderer

        for node in all_nodes:
            if isinstance(node, FunctionNode) and node.id not in reachable_set:
                if node.name.startswith("__") and node.name.endswith("__"):
                    continue
                if "test" in node.file_path.lower():
                    continue

                dead_candidates.append(node)

        return {
            "likely_dead_md": MarkdownRenderer.render_dead_code_candidates(dead_candidates),
            "count": len(dead_candidates),
            "ids": [n.id for n in dead_candidates],
        }

    def build_module_graph(self, max_nodes: int = 100) -> dict[str, Any]:
        """Aggregate file graph into module graph."""
        server = self.service._get_server()
        files = server.graph_builder.get_files()
        graph = server.graph_builder.graph

        modules: dict[str, dict[str, Any]] = {}

        for f in files:
            module_path = "/".join(f.relative_path.split("/")[:-1]) or "root"
            if module_path not in modules:
                modules[module_path] = {"files": [], "imports": {}}
            modules[module_path]["files"].append(f)

        module_adj: dict[tuple[str, str], int] = {}

        for f in files:
            src_mod = "/".join(f.relative_path.split("/")[:-1]) or "root"
            f_idx = server.graph_builder._node_id_to_index.get(f.id)
            if f_idx is not None:
                out_edges = graph.out_edges(f_idx)
                for _, dst_idx, edge_data in out_edges:
                    if edge_data.edge_type == EdgeType.IMPORTS:
                        dst_node = graph[dst_idx]
                        if isinstance(dst_node, (FileNode)):
                            dst_mod = "/".join(dst_node.relative_path.split("/")[:-1]) or "root"
                            if src_mod != dst_mod:
                                pair = (src_mod, dst_mod)
                                module_adj[pair] = module_adj.get(pair, 0) + 1
                        elif hasattr(dst_node, "file_path"):
                            dst_mod = "/".join(dst_node.file_path.split("/")[:-1]) or "root"
                            if src_mod != dst_mod:
                                pair = (src_mod, dst_mod)
                                module_adj[pair] = module_adj.get(pair, 0) + 1

        nodes_data = [
            {"id": m, "name": m, "type": "module", "size": len(d["files"])}
            for m, d in modules.items()
        ]
        edges_data = [
            {"source": s, "target": t, "weight": w, "type": "imports"}
            for (s, t), w in module_adj.items()
        ]

        return {
            "nodes": nodes_data,
            "edges": edges_data,
            "summary": f"Built module graph with {len(nodes_data)} modules.",
        }
