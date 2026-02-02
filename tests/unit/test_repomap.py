"""
Unit tests for RepoMapGenerator.

Tests PageRank-based importance calculation, token-budget-aware generation,
and context generation for queries.
"""

from unittest.mock import MagicMock

import pytest
import rustworkx as rx

from codex_mesh.core.edges import Edge, EdgeType
from codex_mesh.core.graph import CodeGraphBuilder
from codex_mesh.core.nodes import ClassNode, FileNode, FunctionNode
from codex_mesh.storage.repomap import RepoMapGenerator


@pytest.fixture
def mock_graph_builder():
    """Create a mock GraphBuilder with a sample graph for testing."""
    builder = MagicMock(spec=CodeGraphBuilder)

    # Create real rustworkx graph
    graph = rx.PyDiGraph()

    # Create nodes
    file_node = FileNode(
        id="file::app.py", name="app.py", path="/project/app.py", relative_path="app.py"
    )

    class_node = ClassNode(
        id="class::Server",
        name="Server",
        file_path="app.py",
        line_start=10,
        line_end=50,
        bases=["BaseServer"],
        docstring="Main server class that handles HTTP requests.",
    )

    func1 = FunctionNode(
        id="func::main",
        name="main",
        file_path="app.py",
        line_start=5,
        line_end=8,
        docstring="Entry point for the application",
    )

    method1 = FunctionNode(
        id="func::Server.run",
        name="run",
        file_path="app.py",
        line_start=20,
        line_end=30,
        docstring="Start the server",
        is_method=True,
        class_name="Server",
    )

    method2 = FunctionNode(
        id="func::Server.handle",
        name="handle",
        file_path="app.py",
        line_start=32,
        line_end=45,
        docstring="Handle incoming request",
        is_method=True,
        class_name="Server",
    )

    # Add nodes
    file_idx = graph.add_node(file_node)
    class_idx = graph.add_node(class_node)
    func_idx = graph.add_node(func1)
    method1_idx = graph.add_node(method1)
    method2_idx = graph.add_node(method2)

    # Add edges - using source_id and target_id
    graph.add_edge(
        file_idx,
        class_idx,
        Edge(source_id=file_node.id, target_id=class_node.id, edge_type=EdgeType.CONTAINS),
    )
    graph.add_edge(
        file_idx,
        func_idx,
        Edge(source_id=file_node.id, target_id=func1.id, edge_type=EdgeType.CONTAINS),
    )
    graph.add_edge(
        class_idx,
        method1_idx,
        Edge(source_id=class_node.id, target_id=method1.id, edge_type=EdgeType.CONTAINS),
    )
    graph.add_edge(
        class_idx,
        method2_idx,
        Edge(source_id=class_node.id, target_id=method2.id, edge_type=EdgeType.CONTAINS),
    )
    graph.add_edge(
        func_idx,
        method1_idx,
        Edge(source_id=func1.id, target_id=method1.id, edge_type=EdgeType.CALLS),
    )
    graph.add_edge(
        method1_idx,
        method2_idx,
        Edge(source_id=method1.id, target_id=method2.id, edge_type=EdgeType.CALLS),
    )

    builder.graph = graph
    return builder


@pytest.fixture
def empty_graph_builder():
    """Create a mock GraphBuilder with an empty graph."""
    builder = MagicMock(spec=CodeGraphBuilder)
    builder.graph = rx.PyDiGraph()
    return builder


class TestRepoMapInit:
    """Tests for RepoMapGenerator initialization."""

    def test_init_stores_graph(self, mock_graph_builder):
        """Test that initialization stores the graph correctly."""
        gen = RepoMapGenerator(mock_graph_builder)

        assert gen.graph is mock_graph_builder.graph
        assert gen.builder is mock_graph_builder
        assert gen._ranks == {}


class TestCalculateImportance:
    """Tests for PageRank importance calculation."""

    def test_calculate_importance_returns_scores(self, mock_graph_builder):
        """Test that importance scores are calculated for all nodes."""
        gen = RepoMapGenerator(mock_graph_builder)

        scores = gen.calculate_importance()

        assert len(scores) > 0
        assert all(score >= 0 for score in scores.values())

    def test_calculate_importance_empty_graph(self, empty_graph_builder):
        """Test importance calculation on empty graph."""
        gen = RepoMapGenerator(empty_graph_builder)

        scores = gen.calculate_importance()

        assert scores == {}

    def test_calculate_importance_caches_ranks(self, mock_graph_builder):
        """Test that ranks are cached after calculation."""
        gen = RepoMapGenerator(mock_graph_builder)

        gen.calculate_importance()

        assert gen._ranks != {}


class TestGenerate:
    """Tests for repository map generation."""

    def test_generate_includes_header(self, mock_graph_builder):
        """Test that output includes repository map header."""
        gen = RepoMapGenerator(mock_graph_builder)

        result = gen.generate(token_budget=2000)

        assert "# Repository Map" in result

    def test_generate_includes_file_sections(self, mock_graph_builder):
        """Test that output organizes by file."""
        gen = RepoMapGenerator(mock_graph_builder)

        result = gen.generate(token_budget=2000)

        assert "app.py" in result

    def test_generate_produces_output(self, mock_graph_builder):
        """Test generation produces non-empty output."""
        gen = RepoMapGenerator(mock_graph_builder)

        result = gen.generate(token_budget=2000, include_signatures=True)

        assert len(result) > 0

    def test_generate_small_budget_still_works(self, mock_graph_builder):
        """Test that small budget still produces some output."""
        gen = RepoMapGenerator(mock_graph_builder)

        result = gen.generate(token_budget=100)

        assert len(result) > 0


class TestFormatNode:
    """Tests for node formatting."""

    def test_format_file_node(self, mock_graph_builder):
        """Test formatting a file node."""
        gen = RepoMapGenerator(mock_graph_builder)

        file_node = FileNode(
            id="file::test.py", name="test.py", path="/project/test.py", relative_path="test.py"
        )

        result = gen._format_node(file_node)

        assert "📄" in result
        assert "test.py" in result

    def test_format_class_node(self, mock_graph_builder):
        """Test formatting a class node."""
        gen = RepoMapGenerator(mock_graph_builder)

        class_node = ClassNode(
            id="class::MyClass",
            name="MyClass",
            file_path="test.py",
            line_start=1,
            line_end=10,
            bases=["BaseClass"],
            docstring="A test class",
        )

        result = gen._format_node(class_node, include_signature=True)

        assert "🔷" in result
        assert "class MyClass" in result
        assert "BaseClass" in result

    def test_format_function_node(self, mock_graph_builder):
        """Test formatting a function node."""
        gen = RepoMapGenerator(mock_graph_builder)

        func_node = FunctionNode(
            id="func::my_func",
            name="my_func",
            file_path="test.py",
            line_start=1,
            line_end=5,
            docstring="My function",
            signature="def my_func() -> None",
        )

        result = gen._format_node(func_node, include_signature=True)

        assert "⚡" in result
        assert "my_func" in result

    def test_format_method_node(self, mock_graph_builder):
        """Test formatting a method node."""
        gen = RepoMapGenerator(mock_graph_builder)

        method_node = FunctionNode(
            id="func::MyClass.method",
            name="method",
            file_path="test.py",
            line_start=5,
            line_end=10,
            docstring="A method",
            is_method=True,
            class_name="MyClass",
        )

        result = gen._format_node(method_node)

        assert "🔹" in result


class TestGetContextForQuery:
    """Tests for query-based context generation."""

    def test_get_context_with_matching_nodes(self, mock_graph_builder):
        """Test context generation when query matches nodes."""
        gen = RepoMapGenerator(mock_graph_builder)

        result = gen.get_context_for_query("Server", token_budget=500)

        assert len(result) > 0

    def test_get_context_no_matches_fallback(self, mock_graph_builder):
        """Test that no matches falls back to top-ranked nodes."""
        gen = RepoMapGenerator(mock_graph_builder)

        result = gen.get_context_for_query("nonexistent_query_xyz", token_budget=500)

        assert len(result) > 0
