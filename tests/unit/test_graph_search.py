"""
Unit tests for GraphSearch.

Tests graph-based code search including name search, caller/callee resolution,
subgraph extraction, path finding, and reachability computation.
"""

from unittest.mock import MagicMock

import pytest
import rustworkx as rx

from codex_mesh.core.edges import Edge, EdgeType
from codex_mesh.core.graph import CodeGraphBuilder
from codex_mesh.core.nodes import ClassNode, FileNode, FunctionNode
from codex_mesh.storage.search import GraphSearch


@pytest.fixture
def mock_graph_builder():
    """Create a mock GraphBuilder with a simple graph."""
    builder = MagicMock(spec=CodeGraphBuilder)

    # Create real rustworkx graph
    graph = rx.PyDiGraph()

    # Create nodes using Pydantic model
    file_node = FileNode(
        id="file::main.py", name="main.py", path="/project/main.py", relative_path="main.py"
    )

    func1 = FunctionNode(
        id="func::main",
        name="main",
        file_path="main.py",
        line_start=5,
        line_end=15,
        docstring="Entry point",
    )

    func2 = FunctionNode(
        id="func::helper",
        name="helper",
        file_path="main.py",
        line_start=17,
        line_end=20,
        docstring="Helper function",
    )

    class_node = ClassNode(
        id="class::App",
        name="App",
        file_path="main.py",
        line_start=22,
        line_end=35,
        bases=["object"],
        docstring="Application class",
    )

    # Add nodes to graph
    file_idx = graph.add_node(file_node)
    func1_idx = graph.add_node(func1)
    func2_idx = graph.add_node(func2)
    class_idx = graph.add_node(class_node)

    # Add edges - Edge uses source_id and target_id
    graph.add_edge(
        file_idx,
        func1_idx,
        Edge(source_id=file_node.id, target_id=func1.id, edge_type=EdgeType.CONTAINS),
    )
    graph.add_edge(
        file_idx,
        func2_idx,
        Edge(source_id=file_node.id, target_id=func2.id, edge_type=EdgeType.CONTAINS),
    )

    # main calls helper
    graph.add_edge(
        func1_idx, func2_idx, Edge(source_id=func1.id, target_id=func2.id, edge_type=EdgeType.CALLS)
    )

    # Setup mock
    builder.graph = graph
    builder._node_id_to_index = {
        file_node.id: file_idx,
        func1.id: func1_idx,
        func2.id: func2_idx,
        class_node.id: class_idx,
    }

    return builder


class TestGraphSearchInit:
    """Tests for GraphSearch initialization."""

    def test_init_builds_name_index(self, mock_graph_builder):
        """Test that name index is built on initialization."""
        search = GraphSearch(mock_graph_builder)

        # Check index was built - keys are lowercase
        assert len(search._name_index) > 0
        assert "main" in search._name_index
        assert "helper" in search._name_index
        assert "app" in search._name_index  # Lowercase


class TestSearchByName:
    """Tests for search_by_name method."""

    def test_exact_match(self, mock_graph_builder):
        """Test exact name matching."""
        search = GraphSearch(mock_graph_builder)

        results = search.search_by_name("main")

        assert len(results) >= 1
        assert any(r.name == "main" for r in results)

    def test_prefix_match(self, mock_graph_builder):
        """Test prefix matching."""
        search = GraphSearch(mock_graph_builder)

        results = search.search_by_name("hel")

        assert len(results) >= 1
        assert any(r.name == "helper" for r in results)

    def test_case_insensitive(self, mock_graph_builder):
        """Test case insensitive matching."""
        search = GraphSearch(mock_graph_builder)

        results = search.search_by_name("MAIN")

        assert len(results) >= 1
        assert any(r.name == "main" for r in results)

    def test_no_results(self, mock_graph_builder):
        """Test when no matches found."""
        search = GraphSearch(mock_graph_builder)

        results = search.search_by_name("nonexistent_xyz_123")

        assert len(results) == 0

    def test_limit_results(self, mock_graph_builder):
        """Test limiting number of results."""
        search = GraphSearch(mock_graph_builder)

        results = search.search_by_name("m", limit=1)

        assert len(results) <= 1


class TestSearchFunctionsAndClasses:
    """Tests for type-specific search methods."""

    def test_search_functions(self, mock_graph_builder):
        """Test searching for functions only."""
        search = GraphSearch(mock_graph_builder)

        results = search.search_functions("main")

        assert len(results) >= 1
        assert all(isinstance(r, FunctionNode) for r in results)

    def test_search_classes(self, mock_graph_builder):
        """Test searching for classes only."""
        search = GraphSearch(mock_graph_builder)

        results = search.search_classes("App")

        assert len(results) >= 1
        assert all(isinstance(r, ClassNode) for r in results)


class TestCallerCallee:
    """Tests for caller/callee resolution."""

    def test_get_callers(self, mock_graph_builder):
        """Test getting callers of a function."""
        search = GraphSearch(mock_graph_builder)

        # helper is called by main
        callers = search.get_callers("func::helper")

        assert len(callers) == 1
        assert callers[0].name == "main"

    def test_get_callees(self, mock_graph_builder):
        """Test getting functions called by a function."""
        search = GraphSearch(mock_graph_builder)

        # main calls helper
        callees = search.get_callees("func::main")

        assert len(callees) == 1
        assert callees[0].name == "helper"

    def test_get_callers_no_callers(self, mock_graph_builder):
        """Test when function has no callers."""
        search = GraphSearch(mock_graph_builder)

        callers = search.get_callers("func::main")

        assert len(callers) == 0

    def test_get_callees_no_callees(self, mock_graph_builder):
        """Test when function has no callees."""
        search = GraphSearch(mock_graph_builder)

        callees = search.get_callees("func::helper")

        assert len(callees) == 0


class TestSubgraph:
    """Tests for subgraph extraction."""

    def test_get_subgraph_depth_1(self, mock_graph_builder):
        """Test getting subgraph with depth 1."""
        search = GraphSearch(mock_graph_builder)

        nodes, edges = search.get_subgraph("func::main", depth=1)

        # Should include main and its neighbors
        node_ids = {n.id for n in nodes}
        assert "func::main" in node_ids

    def test_get_subgraph_direction_out(self, mock_graph_builder):
        """Test outgoing-only subgraph."""
        search = GraphSearch(mock_graph_builder)

        nodes, edges = search.get_subgraph("func::main", depth=1, direction="out")

        node_ids = {n.id for n in nodes}
        assert "func::main" in node_ids

    def test_get_subgraph_direction_in(self, mock_graph_builder):
        """Test incoming-only subgraph."""
        search = GraphSearch(mock_graph_builder)

        nodes, edges = search.get_subgraph("func::helper", depth=1, direction="in")

        node_ids = {n.id for n in nodes}
        assert "func::helper" in node_ids


class TestFindPath:
    """Tests for path finding between nodes."""

    def test_find_path_exists(self, mock_graph_builder):
        """Test finding path when it exists."""
        search = GraphSearch(mock_graph_builder)

        path = search.find_path("func::main", "func::helper")

        assert path is not None
        assert len(path) == 2
        assert path[0].id == "func::main"
        assert path[1].id == "func::helper"

    def test_find_path_not_exists(self, mock_graph_builder):
        """Test when no path exists."""
        search = GraphSearch(mock_graph_builder)

        # helper -> main has no path (edge is main -> helper)
        path = search.find_path("func::helper", "func::main")

        # May be None or empty depending on implementation
        assert path is None or len(path) == 0


class TestReachability:
    """Tests for reachability computation."""

    def test_compute_reachability_basic(self, mock_graph_builder):
        """Test basic reachability computation."""
        search = GraphSearch(mock_graph_builder)

        reachable_ids, count = search.compute_reachability(["func::main"])

        assert count >= 1

    def test_compute_reachability_with_depth(self, mock_graph_builder):
        """Test reachability with max depth."""
        search = GraphSearch(mock_graph_builder)

        reachable_ids, count = search.compute_reachability(["func::main"], max_depth=1)

        # Should reach at least some nodes
        assert count >= 1

    def test_compute_reachability_multiple_roots(self, mock_graph_builder):
        """Test reachability from multiple starting nodes."""
        search = GraphSearch(mock_graph_builder)

        reachable_ids, count = search.compute_reachability(["func::main", "func::helper"])

        assert count >= 2


class TestFileContents:
    """Tests for get_file_contents method."""

    def test_get_file_contents(self, mock_graph_builder):
        """Test getting all nodes in a file."""
        search = GraphSearch(mock_graph_builder)

        contents = search.get_file_contents("main.py")

        # Should find functions in main.py
        node_names = {n.name for n in contents}
        assert "main" in node_names or "helper" in node_names
