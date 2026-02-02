"""RepoMap generator using PageRank for importance ranking."""

import rustworkx as rx

from ..core.graph import CodeGraphBuilder
from ..core.nodes import BaseNode, ClassNode, FileNode, FunctionNode


class RepoMapGenerator:
    """
    Generates a compact repository map for LLM context.

    Uses PageRank algorithm to rank nodes by importance and selects
    the most relevant nodes within a token budget.
    """

    # Approximate tokens per character
    TOKENS_PER_CHAR = 0.25

    def __init__(self, graph_builder: CodeGraphBuilder):
        """
        Initialize with a built code graph.

        Args:
            graph_builder: CodeGraphBuilder with a populated graph
        """
        self.graph = graph_builder.graph
        self.builder = graph_builder
        self._ranks: dict[int, float] = {}

    def calculate_importance(self, damping: float = 0.85) -> dict[str, float]:
        """
        Calculate importance scores using PageRank.

        Args:
            damping: PageRank damping factor (default 0.85)

        Returns:
            Dictionary mapping node_id to importance score
        """
        if self.graph.num_nodes() == 0:
            return {}

        # Run PageRank on the graph - returns CentralityMapping
        pagerank_result = rx.pagerank(self.graph, alpha=damping)

        # Convert CentralityMapping to regular dict (it's indexed by node index)
        self._ranks = dict(pagerank_result)

        # Convert to node_id mapping
        importance = {}
        for idx, node in enumerate(self.graph.nodes()):
            if idx in self._ranks:
                importance[node.id] = self._ranks[idx]

        return importance

    def generate(
        self,
        token_budget: int = 1024,
        include_signatures: bool = True,
        include_docstrings: bool = False,
    ) -> str:
        """
        Generate a repository map within the token budget.

        Args:
            token_budget: Maximum number of tokens for the output
            include_signatures: Whether to include function signatures
            include_docstrings: Whether to include docstrings

        Returns:
            Formatted repository map as a string
        """
        # Calculate importance if not done
        if not self._ranks:
            self.calculate_importance()

        # Sort nodes by importance (descending)
        nodes_with_scores = []
        for idx, node in enumerate(self.graph.nodes()):
            score = self._ranks.get(idx, 0.0)
            nodes_with_scores.append((node, score))

        nodes_with_scores.sort(key=lambda x: x[1], reverse=True)

        # Build output within token budget
        current_tokens = 0

        # Group by file for cleaner output
        file_contents: dict[str, list[str]] = {}

        for node, _score in nodes_with_scores:
            entry = self._format_node(node, include_signatures, include_docstrings)
            entry_tokens = int(len(entry) * self.TOKENS_PER_CHAR)

            if current_tokens + entry_tokens > token_budget:
                break

            if isinstance(node, FileNode):
                file_path = node.relative_path
                if file_path not in file_contents:
                    file_contents[file_path] = []
            elif isinstance(node, (ClassNode, FunctionNode)):
                file_path = node.file_path
                if file_path not in file_contents:
                    file_contents[file_path] = []
                file_contents[file_path].append(entry)
                current_tokens += entry_tokens

        # Format output
        output_lines = ["# Repository Map", ""]

        for file_path in sorted(file_contents.keys()):
            output_lines.append(f"## {file_path}")
            entries = file_contents[file_path]
            if entries:
                for entry in entries:
                    output_lines.append(f"  {entry}")
            output_lines.append("")

        return "\n".join(output_lines)

    def _format_node(
        self,
        node: BaseNode,
        include_signature: bool = True,
        include_docstring: bool = False,
    ) -> str:
        """Format a node for the repository map."""
        if isinstance(node, FileNode):
            return f"📄 {node.relative_path}"

        elif isinstance(node, ClassNode):
            parts = [f"🔷 class {node.name}"]
            if node.bases:
                parts[0] += f"({', '.join(node.bases)})"
            if include_docstring and node.docstring:
                # Truncate long docstrings
                doc = node.docstring[:100] + "..." if len(node.docstring) > 100 else node.docstring
                parts.append(f'    """{doc}"""')
            return "\n".join(parts)

        elif isinstance(node, FunctionNode):
            prefix = "🔹" if node.is_method else "⚡"
            if node.is_method and node.class_name:
                name = f"{node.class_name}.{node.name}"
            else:
                name = node.name

            if include_signature and node.signature:
                entry = f"{prefix} {node.signature}"
            else:
                entry = f"{prefix} {name}()"

            if include_docstring and node.docstring:
                doc = node.docstring[:80] + "..." if len(node.docstring) > 80 else node.docstring
                entry += f"  # {doc}"

            return entry

        return f"• {node.name}"

    def get_context_for_query(
        self,
        query: str,
        token_budget: int = 512,
    ) -> str:
        """
        Generate context relevant to a specific query.

        This is a simplified version - full implementation would use
        semantic search to find relevant nodes.

        Args:
            query: User's query string
            token_budget: Token budget for this context

        Returns:
            Relevant context as a string
        """
        query_lower = query.lower()

        # Find nodes matching the query
        matching_nodes = []
        for node in self.graph.nodes():
            if query_lower in node.name.lower() or (
                isinstance(node, (ClassNode, FunctionNode))
                and node.docstring
                and query_lower in node.docstring.lower()
            ):
                matching_nodes.append(node)

        if not matching_nodes:
            # Fall back to top-ranked nodes
            return self.generate(token_budget=token_budget)

        # Format matching nodes
        lines = [f"# Context for: {query}", ""]
        current_tokens = 0

        for node in matching_nodes[:10]:  # Limit to 10 matches
            entry = self._format_node(node, include_signature=True, include_docstring=True)
            entry_tokens = int(len(entry) * self.TOKENS_PER_CHAR)

            if current_tokens + entry_tokens > token_budget:
                break

            lines.append(entry)
            current_tokens += entry_tokens

        return "\n".join(lines)
