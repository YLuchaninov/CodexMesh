from __future__ import annotations

from ..core.edges import EdgeType
from ..core.nodes import DocSectionNode, FileNode


class DocsAudit:
    def __init__(self, graph, stale_days: int = 14):
        self.graph = graph
        self.stale_seconds = stale_days * 86400

    def audit(self):
        # Identify stale links
        # We need the mtime of the file containing the doc section and the file containing the code symbol

        # Build file mtime map
        file_mtime = {}
        for n in self.graph.get_all_nodes():
            if isinstance(n, FileNode):
                file_mtime[n.id] = n.mtime
                # Also map relative path to mtime just in case
                file_mtime[n.relative_path] = n.mtime

        # Helper to get mtime for a node
        def get_node_mtime(node_id):
            node = self.graph.get_node_by_id(node_id)
            if not node:
                return 0
            if isinstance(node, FileNode):
                return node.mtime
            if hasattr(node, "file_path"):
                # Construct file id? Or look up by path?
                # FileNode id is file::relative_path
                fid = f"file::{node.file_path}"
                return file_mtime.get(fid, 0)
            return 0

        nodes = self.graph.graph.nodes()
        stale_edges = []

        # Iterate all nodes to find doc sections
        for u_idx, u_node in enumerate(nodes):
            if isinstance(u_node, DocSectionNode):
                doc_mtime = get_node_mtime(u_node.id)

                # Check outgoing DOCUMENTS edges
                for _, v_idx, edge_data in self.graph.graph.out_edges(u_idx):
                    if edge_data.edge_type == EdgeType.DOCUMENTS:
                        target_node = self.graph.graph[v_idx]
                        target_mtime = get_node_mtime(target_node.id)

                        # Logic: If code (target) is newer than doc (source) + buffer
                        # Then doc is potentially stale
                        if target_mtime > doc_mtime + self.stale_seconds:
                            stale_edges.append(
                                {
                                    "doc_id": u_node.id,
                                    "target_id": target_node.id,
                                    "doc_mtime": doc_mtime,
                                    "target_mtime": target_mtime,
                                    "diff_curr": target_mtime - doc_mtime,
                                }
                            )

        return stale_edges
