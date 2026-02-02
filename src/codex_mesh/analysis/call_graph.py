"""
Call Graph Builder Module.
Builds specialized subgraphs for call analysis.
"""

from typing import Any

from ..core.edges import EdgeType
from ..review.graph_render import to_mermaid


class CallGraphBuilder:
    def __init__(self, server):
        self.server = server

    def build(
        self,
        roots: list[str],
        depth: int = 1,
        direction: str = "both",
        edge_types: list[EdgeType] | None = None,
        max_nodes: int = 200,
    ) -> dict[str, Any]:
        """
        Build a call graph (or any subgraph) starting from roots.
        """
        if edge_types is None:
            edge_types = [EdgeType.CALLS]

        nodes = []
        edges = []

        for r in roots:
            n, e = self.server.graph_search.get_subgraph(
                r, depth=depth, direction=direction, edge_types=edge_types
            )
            nodes.extend(n)
            edges.extend(e)

        return self.format_subgraph(roots, nodes, edges, direction=direction, max_nodes=max_nodes)

    def format_subgraph(
        self,
        roots: list[str],
        nodes: list[Any],
        edges: list[Any],
        direction: str = "both",
        max_nodes: int = 200,
    ) -> dict[str, Any]:
        """
        Deduplicate, format and generate mermaid for a list of nodes and edges.
        """
        # Deduplicate
        unique_nodes = {n.id: n for n in nodes}
        unique_edges = {}

        nodes_data = []
        for n in unique_nodes.values():
            nodes_data.append(
                {
                    "id": n.id,
                    "name": n.name,
                    "type": n.node_type.value,
                    "file_path": getattr(n, "file_path", getattr(n, "relative_path", None)),
                    "span": {
                        "start_line": getattr(n, "line_start", 0),
                        "end_line": getattr(n, "line_end", 0),
                    },
                }
            )

        edges_data = []
        for e in edges:
            try:
                src_id = e.source
                tgt_id = e.target
                key = f"{src_id}->{tgt_id}"
                if key not in unique_edges:
                    unique_edges[key] = {
                        "source": src_id,
                        "target": tgt_id,
                        "type": str(getattr(e, "type", "unknown")),
                    }
                    edges_data.append(unique_edges[key])
            except AttributeError:
                pass

        if len(nodes_data) > max_nodes:
            # Very simple truncation
            nodes_data = nodes_data[:max_nodes]
            allowed = {n["id"] for n in nodes_data}
            edges_data = [
                e for e in edges_data if e["source"] in allowed and e["target"] in allowed
            ]

        mermaid_direction = "LR" if direction in ["both", "out"] else "RL"
        mermaid = to_mermaid(list(unique_nodes.values()), edges, direction=mermaid_direction)

        return {
            "roots": roots,
            "nodes": nodes_data,
            "edges": edges_data,
            "mermaid": mermaid,
            "stats": {"node_count": len(nodes_data), "edge_count": len(edges_data)},
        }

    def callers_of(self, node_id: str, depth: int = 1) -> dict[str, Any]:
        """Find functions that call the given node."""
        nodes, _edges = self.server.graph_search.get_subgraph(
            node_id, depth=depth, direction="in", edge_types=[EdgeType.CALLS]
        )
        # Exclude the node itself from callers? Usually yes, keep callers only.
        callers = [n for n in nodes if n.id != node_id]
        return {
            "node_id": node_id,
            "callers": [
                {"id": n.id, "name": n.name, "file_path": getattr(n, "file_path", None)}
                for n in callers
            ],
            "count": len(callers),
        }

    def callees_of(self, node_id: str, depth: int = 1) -> dict[str, Any]:
        """Find functions called by the given node."""
        nodes, _edges = self.server.graph_search.get_subgraph(
            node_id, depth=depth, direction="out", edge_types=[EdgeType.CALLS]
        )
        callees = [n for n in nodes if n.id != node_id]
        return {
            "node_id": node_id,
            "callees": [
                {"id": n.id, "name": n.name, "file_path": getattr(n, "file_path", None)}
                for n in callees
            ],
            "count": len(callees),
        }

    def find_entrypoint_paths(
        self, target_id: str, entrypoints: list[str], max_hops: int = 10
    ) -> dict[str, Any]:
        """
        Find paths from any of the entrypoints to the target_id.
        """
        paths: list[dict[str, Any]] = []
        for ep in entrypoints:
            # find_path usually just one path.
            # We might want all paths?
            # For now reuse find_path (shortest path)
            p = self.server.graph_search.find_path(
                ep, target_id, edge_types=[EdgeType.CALLS], max_hops=max_hops
            )
            if p:
                paths.append({"entrypoint": ep, "length": len(p), "path": [n.id for n in p]})

        paths.sort(key=lambda x: int(x["length"]))
        return {"target": target_id, "paths": paths}
