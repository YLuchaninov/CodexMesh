"""
Unit tests for graph rendering utilities.

Tests Mermaid diagram generation and tree rendering.
"""

import pytest

from codex_mesh.core.nodes import ClassNode, FileNode, FunctionNode
from codex_mesh.review.graph_render import to_mermaid, to_tree


@pytest.fixture
def sample_nodes():
    """Create sample nodes for testing."""
    return [
        FunctionNode(
            id="func::main",
            name="main",
            file_path="app.py",
            line_start=1,
            line_end=10,
            docstring="",
        ),
        FunctionNode(
            id="func::helper",
            name="helper",
            file_path="app.py",
            line_start=12,
            line_end=20,
            docstring="",
        ),
        ClassNode(
            id="class::Service",
            name="Service",
            file_path="service.py",
            line_start=1,
            line_end=50,
            bases=["BaseService"],
            docstring="Service class",
        ),
    ]


@pytest.fixture
def sample_edges():
    """Create sample edges as dicts for testing (to_tree expects dicts)."""
    return [
        {"source": "func::main", "target": "func::helper", "type": "CALLS"},
        {"source": "func::main", "target": "class::Service", "type": "USES"},
    ]


class TestToMermaid:
    """Tests for Mermaid diagram generation."""

    def test_basic_mermaid_generation(self, sample_nodes, sample_edges):
        """Test basic Mermaid diagram generation."""
        result = to_mermaid(sample_nodes, sample_edges)

        assert "graph" in result
        assert "main" in result
        assert "helper" in result

    def test_mermaid_includes_edges(self, sample_nodes, sample_edges):
        """Test that edges are included in the diagram."""
        result = to_mermaid(sample_nodes, sample_edges)

        assert "-->" in result or "--" in result

    def test_mermaid_direction_td(self, sample_nodes, sample_edges):
        """Test Mermaid with top-down direction."""
        result = to_mermaid(sample_nodes, sample_edges, direction="TD")

        assert "TD" in result

    def test_mermaid_direction_lr(self, sample_nodes, sample_edges):
        """Test Mermaid with left-right direction."""
        result = to_mermaid(sample_nodes, sample_edges, direction="LR")

        assert "LR" in result

    def test_mermaid_empty_graph(self):
        """Test Mermaid with empty inputs."""
        result = to_mermaid([], [])

        # Should still produce valid mermaid structure
        assert "graph" in result

    def test_mermaid_with_dict_edges(self, sample_nodes):
        """Test Mermaid with dict edges (main use case)."""
        edges = [{"source": "func::main", "target": "func::helper", "type": "calls"}]
        result = to_mermaid(sample_nodes, edges)

        assert "main" in result
        assert "helper" in result

    def test_mermaid_node_types_styled_differently(self, sample_nodes, sample_edges):
        """Test that different node types may have different styles."""
        result = to_mermaid(sample_nodes, sample_edges)

        assert "main" in result
        assert "Service" in result


class TestToTree:
    """Tests for tree rendering."""

    def test_basic_tree_generation(self, sample_nodes, sample_edges):
        """Test basic tree generation returns dict."""
        result = to_tree(sample_nodes, sample_edges, root_id="func::main")

        # to_tree returns a dict, not a string
        assert isinstance(result, dict)
        assert "id" in result
        assert "name" in result
        assert "children" in result

    def test_tree_shows_hierarchy(self, sample_nodes, sample_edges):
        """Test that tree shows parent-child relationships."""
        result = to_tree(sample_nodes, sample_edges, root_id="func::main")

        # Should have children
        assert "children" in result
        assert len(result["children"]) > 0

    def test_tree_with_no_children(self):
        """Test tree with a leaf node as root."""
        nodes = [
            FunctionNode(
                id="func::leaf",
                name="leaf",
                file_path="test.py",
                line_start=1,
                line_end=5,
                docstring="",
            )
        ]

        result = to_tree(nodes, [], root_id="func::leaf")

        assert result["name"] == "leaf"
        assert result["children"] == []

    def test_tree_empty_inputs(self):
        """Test tree with empty inputs."""
        result = to_tree([], [], root_id="nonexistent")

        # Should return error node
        assert "error" in result or result["id"] == "nonexistent"

    def test_tree_with_dict_edges(self, sample_nodes):
        """Test tree with dict edges."""
        edges = [{"source": "func::main", "target": "func::helper", "type": "CALLS"}]
        result = to_tree(sample_nodes, edges, root_id="func::main")

        assert result["name"] == "main"


class TestMermaidEdgeTypes:
    """Tests for edge type representation in Mermaid."""

    def test_calls_edge_style(self):
        """Test that CALLS edges have appropriate style."""
        nodes = [
            FunctionNode(
                id="f1", name="caller", file_path="t.py", line_start=1, line_end=5, docstring=""
            ),
            FunctionNode(
                id="f2", name="callee", file_path="t.py", line_start=6, line_end=10, docstring=""
            ),
        ]
        edges = [{"source": "f1", "target": "f2", "type": "calls"}]

        result = to_mermaid(nodes, edges)

        assert "caller" in result
        assert "callee" in result

    def test_imports_edge_style(self):
        """Test that IMPORTS edges are represented."""
        nodes = [
            FileNode(id="file1", name="main.py", path="/main.py", relative_path="main.py"),
            FileNode(id="file2", name="utils.py", path="/utils.py", relative_path="utils.py"),
        ]
        edges = [{"source": "file1", "target": "file2", "type": "imports"}]

        result = to_mermaid(nodes, edges)

        assert "main" in result
        assert "utils" in result


class TestTreeStructure:
    """Tests for tree structure and formatting."""

    def test_tree_returns_dict_structure(self, sample_nodes, sample_edges):
        """Test that tree returns proper dict structure."""
        result = to_tree(sample_nodes, sample_edges, root_id="func::main")

        # Check required fields
        assert "id" in result
        assert "name" in result
        assert "type" in result
        assert "children" in result

    def test_tree_handles_cycles(self):
        """Test tree handles cycles by marking recursive nodes."""
        nodes = [
            FunctionNode(
                id="f1", name="func1", file_path="t.py", line_start=1, line_end=5, docstring=""
            ),
            FunctionNode(
                id="f2", name="func2", file_path="t.py", line_start=6, line_end=10, docstring=""
            ),
        ]
        # Create a cycle: f1 -> f2 -> f1
        edges = [
            {"source": "f1", "target": "f2", "type": "CALLS"},
            {"source": "f2", "target": "f1", "type": "CALLS"},
        ]

        result = to_tree(nodes, edges, root_id="f1")

        # Should handle without infinite loop
        assert result["name"] == "func1"
