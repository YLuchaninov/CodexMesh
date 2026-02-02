"""Graph-based code search."""

from typing import Any

from ..core.edges import EdgeType
from ..core.graph import CodeGraphBuilder
from ..core.nodes import BaseNode, ClassNode, FunctionNode


class GraphSearch:
    """
    Graph-based search for code elements.

    Provides structural search capabilities using the code graph.
    """

    def __init__(self, graph_builder: CodeGraphBuilder):
        """Initialize with a built code graph."""
        self.graph = graph_builder.graph
        self.builder = graph_builder

        # Build search index
        self._name_index: dict[str, list[BaseNode]] = {}
        self._graph_id = id(self.builder.graph)
        self._build_name_index()

    def _refresh_if_needed(self) -> None:
        """Refresh internal indices if the underlying graph object changed."""
        current_id = id(self.builder.graph)
        if current_id != self._graph_id:
            self._graph_id = current_id
            self.graph = self.builder.graph
            self._name_index.clear()
            self._build_name_index()

    def _build_name_index(self) -> None:
        """Build an index of node names for fast lookup."""
        for node in self.graph.nodes():
            name_lower = node.name.lower()
            if name_lower not in self._name_index:
                self._name_index[name_lower] = []
            self._name_index[name_lower].append(node)

    def search_by_name(self, query: str, limit: int = 10) -> list[BaseNode]:
        """
        Search nodes by name (exact or prefix match).

        Args:
            query: Search query
            limit: Maximum results to return

        Returns:
            List of matching nodes
            List of matching nodes
        """
        self._refresh_if_needed()

        query_lower = query.lower()
        results = []

        # Exact match first
        if query_lower in self._name_index:
            results.extend(self._name_index[query_lower])

        # Prefix/substring match
        for name, nodes in self._name_index.items():
            if query_lower in name and name != query_lower:
                results.extend(nodes)
                if len(results) >= limit:
                    break

        return results[:limit]

    def search_functions(self, query: str, limit: int = 10) -> list[FunctionNode]:
        """Search for functions matching the query."""
        results = self.search_by_name(query, limit=limit * 2)
        functions = [n for n in results if isinstance(n, FunctionNode)]
        return functions[:limit]

    def search_classes(self, query: str, limit: int = 10) -> list[ClassNode]:
        """Search for classes matching the query."""
        results = self.search_by_name(query, limit=limit * 2)
        classes = [n for n in results if isinstance(n, ClassNode)]
        return classes[:limit]

    def get_callers(self, function_id: str) -> list[BaseNode]:
        """Get all functions that call the specified function."""
        idx = self.builder._node_id_to_index.get(function_id)
        if idx is None:
            return []

        # Get predecessors (incoming edges)
        callers: list[BaseNode] = []
        for pred_idx in self.graph.predecessor_indices(idx):
            edge = self.graph.get_edge_data(pred_idx, idx)
            # Filter for CALLS edges only
            if edge and getattr(edge, "edge_type", None) == EdgeType.CALLS:
                node = self.graph[pred_idx]
                if isinstance(node, FunctionNode):
                    callers.append(node)

        return callers

    def get_callees(self, function_id: str) -> list[BaseNode]:
        """Get all functions called by the specified function."""
        idx = self.builder._node_id_to_index.get(function_id)
        if idx is None:
            return []

        # Get successors (outgoing edges)
        callees: list[BaseNode] = []
        for succ_idx in self.graph.successor_indices(idx):
            edge = self.graph.get_edge_data(idx, succ_idx)
            # Filter for CALLS edges only
            if edge and getattr(edge, "edge_type", None) == EdgeType.CALLS:
                node = self.graph[succ_idx]
                if isinstance(node, FunctionNode):
                    callees.append(node)

        return callees

    def compute_reachability(
        self, root_ids: list[str], max_depth: int = 10, edge_types: list[EdgeType] | None = None
    ) -> tuple[list[str], int]:
        """
        Compute reachable set of node IDs from roots.

        Args:
           root_ids: List of starting node IDs
           max_depth: Maximum traversal depth
           edge_types: Optional strict filter for edge types

        Returns:
           Tuple of (reachable_ids, count)
        """
        queue = []
        visited = set()

        for rid in root_ids:
            idx = self.builder._node_id_to_index.get(rid)
            if idx is not None:
                queue.append((idx, 0))
                visited.add(idx)

        import collections

        q = collections.deque(queue)

        while q:
            curr_idx, depth = q.popleft()
            if depth >= max_depth:
                continue

            for succ_idx in self.graph.successor_indices(curr_idx):
                if succ_idx in visited:
                    continue

                edge = self.graph.get_edge_data(curr_idx, succ_idx)
                if not edge:
                    continue

                if edge_types and getattr(edge, "edge_type", None) not in edge_types:
                    continue

                visited.add(succ_idx)
                q.append((succ_idx, depth + 1))

        reachable_ids = [self.graph[i].id for i in visited]
        return reachable_ids, len(visited)

    def get_file_contents(self, file_path: str) -> list[BaseNode]:
        """Get all nodes contained in a file."""
        file_id = f"file::{file_path}"
        idx = self.builder._node_id_to_index.get(file_id)
        if idx is None:
            return []

        contents = []
        for succ_idx in self.graph.successor_indices(idx):
            edge = self.graph.get_edge_data(idx, succ_idx)
            if edge and edge.edge_type == EdgeType.CONTAINS:
                contents.append(self.graph[succ_idx])

        return contents

    def get_subgraph(
        self,
        root_id: str,
        depth: int = 1,
        direction: str = "both",
        edge_types: list[EdgeType] | None = None,
    ) -> tuple[list[BaseNode], list[Any]]:  # Returns nodes, edges
        """
        Get a subgraph centered around a node.

        Args:
            root_id: Center node ID
            depth: Traversal depth
            direction: 'in', 'out', or 'both'
            edge_types: Optional list of edge types to follow

        Returns:
            Tuple of (nodes, edges) where edges are dicts
        """
        start_idx = self.builder._node_id_to_index.get(root_id)
        if start_idx is None:
            return [], []

        collected_edges = []

        # We need to collect edges between visited nodes too,
        # but standard BFS only sees edges traversed.
        # For a "subgraph", usually we want all edges between the collected nodes
        # OR just the tree edges.
        # Let's collect traversed edges for now (tree-like) + back edges if we encounter them?
        # Simpler: BFS to find nodes. THEN Collect all edges between these nodes.

        # 1. Find nodes within depth
        nodes_indices = {start_idx}

        # BFS
        import collections

        q = collections.deque([(start_idx, 0)])

        while q:
            curr_idx, d = q.popleft()
            if d >= depth:
                continue

            # Outgoing
            if direction in ["out", "both"]:
                for succ_idx in self.graph.successor_indices(curr_idx):
                    edge = self.graph.get_edge_data(curr_idx, succ_idx)
                    if not edge:
                        continue
                    if edge_types and edge.edge_type not in edge_types:
                        continue

                    if succ_idx not in nodes_indices:
                        nodes_indices.add(succ_idx)
                        q.append((succ_idx, d + 1))

            # Incoming
            if direction in ["in", "both"]:
                for pred_idx in self.graph.predecessor_indices(curr_idx):
                    edge = self.graph.get_edge_data(pred_idx, curr_idx)
                    if not edge:
                        continue
                    if edge_types and edge.edge_type not in edge_types:
                        continue

                    if pred_idx not in nodes_indices:
                        nodes_indices.add(pred_idx)
                        q.append((pred_idx, d + 1))

        # 2. Collect nodes and edges
        result_nodes = []
        node_idx_map = {}  # graph_idx -> local_idx or just use IDs

        for idx in nodes_indices:
            node = self.graph[idx]
            result_nodes.append(node)
            node_idx_map[idx] = node.id

        # 3. Collect all edges between identified nodes (induced subgraph)
        # Or only traversed edges? Induced is usually better for "context".
        # But we must respect edge_type filter.

        for idx in nodes_indices:
            # Check outgoing edges from this node to other nodes in the set
            for succ_idx in self.graph.successor_indices(idx):
                if succ_idx in nodes_indices:
                    edge = self.graph.get_edge_data(idx, succ_idx)
                    if edge:
                        if edge_types and edge.edge_type not in edge_types:
                            continue

                        collected_edges.append(
                            {
                                "source": self.graph[idx].id,
                                "target": self.graph[succ_idx].id,
                                "type": edge.edge_type.value,
                                "weight": edge.weight,
                            }
                        )

        return result_nodes, collected_edges

    def find_path(
        self,
        source_id: str,
        target_id: str,
        edge_types: list[EdgeType] | None = None,
        *,
        max_hops: int | None = None,
    ) -> list[BaseNode] | None:
        """
        Find a path between two nodes using BFS.

        Args:
            source_id: Starting node ID
            target_id: Target node ID
            edge_types: Optional list of edge types to traverse
            max_hops: Maximum number of hops allowed (edges in path)

        Returns:
            List of nodes forming the path, or None if no path exists within hop limit
        """
        source_idx = self.builder._node_id_to_index.get(source_id)
        target_idx = self.builder._node_id_to_index.get(target_id)

        if source_idx is None or target_idx is None:
            return None

        # Default max_hops if not specified
        if max_hops is None:
            max_hops = 50

        # BFS to find shortest path by hop count
        from collections import deque

        queue = deque([source_idx])
        parent: dict[int, int | None] = {source_idx: None}
        depth: dict[int, int] = {source_idx: 0}

        while queue:
            u = queue.popleft()

            # Found target
            if u == target_idx:
                break

            # Reached max depth
            if depth[u] >= max_hops:
                continue

            # Explore successors
            for v in self.graph.successor_indices(u):
                edge = self.graph.get_edge_data(u, v)
                if not edge:
                    continue

                # Filter by edge type if specified
                if edge_types and edge.edge_type not in edge_types:
                    continue

                # Skip if already visited
                if v in parent:
                    continue

                parent[v] = u
                depth[v] = depth[u] + 1
                queue.append(v)

        # Check if target was reached
        if target_idx not in parent:
            return None

        # Reconstruct path from target to source
        path_nodes: list[BaseNode] = []
        cur: int | None = target_idx
        while cur is not None:
            path_nodes.append(self.graph[cur])
            cur = parent[cur]

        # Reverse to get source → target path
        path_nodes.reverse()
        return path_nodes
