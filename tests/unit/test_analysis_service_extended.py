"""
Extended unit tests for AnalysisService.

Tests additional methods not covered in test_services.py including
hotspot, repomap, semantic search, subgraph extraction, and more.
"""

from unittest.mock import MagicMock, PropertyMock

import pytest

from codex_mesh.core.nodes import FunctionNode, NodeType
from codex_mesh.embeddings.engine import SearchResult
from codex_mesh.services.analysis_service import AnalysisService


@pytest.fixture
def mock_manager():
    """Create a mock ProjectManager with server."""
    manager = MagicMock()
    server = MagicMock()
    server.graph_search.get_subgraph.return_value = ([], [])
    server.project_root = "/fake/project"
    manager.server = server
    manager.get_server.return_value = server
    return manager


class TestSemanticSearch:
    """Tests for semantic search methods."""

    def test_semantic_search_returns_results(self, mock_manager):
        """Test semantic_search returns formatted results."""
        service = AnalysisService(mock_manager)

        mock_result = SearchResult(
            node_id="func::test",
            name="test_func",
            file_path="test.py",
            content="def test_func():\n    pass",
            score=0.95,
            line_start=1,
            line_end=3,
        )
        mock_manager.server.vector_search.search.return_value = [mock_result]

        results = service.semantic_search("test function", k=5)

        assert len(results) == 1
        assert results[0]["name"] == "test_func"
        assert results[0]["score"] == 0.95
        assert results[0]["node_id"] == "func::test"

    def test_semantic_search_empty_results(self, mock_manager):
        """Test semantic_search with no results."""
        service = AnalysisService(mock_manager)
        mock_manager.server.vector_search.search.return_value = []

        results = service.semantic_search("nonexistent")

        assert results == []

    def test_semantic_search_md_format(self, mock_manager):
        """Test semantic_search_md returns markdown format."""
        service = AnalysisService(mock_manager)

        mock_result = SearchResult(
            node_id="func::test",
            name="test_func",
            file_path="test.py",
            content="def test_func():\n    pass",
            score=0.85,
            line_start=1,
            line_end=3,
        )
        mock_manager.server.vector_search.search.return_value = [mock_result]

        result = service.semantic_search_md("query")

        assert "Semantic search" in result
        assert "test_func" in result
        assert "85%" in result  # score as percentage

    def test_semantic_search_raw(self, mock_manager):
        """Test semantic_search_raw returns dict with matches."""
        service = AnalysisService(mock_manager)

        mock_result = SearchResult(
            node_id="func::test",
            name="test_func",
            file_path="test.py",
            content="def test_func(): pass",
            score=0.9,
            line_start=1,
            line_end=2,
        )
        mock_manager.server.vector_search.search.return_value = [mock_result]

        result = service.semantic_search_raw("query")

        assert "matches" in result
        assert "count" in result
        assert result["count"] == 1


class TestHotspot:
    """Tests for hotspot methods."""

    def test_get_hotspot_all_files(self, mock_manager):
        """Test get_hotspot for all files."""
        service = AnalysisService(mock_manager)

        mock_file = MagicMock()
        mock_file.relative_path = "test.py"
        mock_manager.server.graph_builder.get_files.return_value = [mock_file]

        mock_score = MagicMock()
        mock_score.node_id = "file::test.py"
        mock_score.total = 5.0
        mock_score.structural = 2.0
        mock_score.semantic = 2.0
        mock_score.issues = []
        mock_manager.server.hotspot_calc.get_high_hotspot_nodes.return_value = [mock_score]

        result = service.get_hotspot()

        assert "report" in result
        assert "summary" in result

    def test_get_hotspot_specific_path(self, mock_manager):
        """Test get_hotspot for a specific file."""
        service = AnalysisService(mock_manager)

        mock_score = MagicMock()
        mock_score.node_id = "file::specific.py"
        mock_score.total = 3.0
        mock_score.structural = 1.5
        mock_score.semantic = 1.5
        mock_score.issues = []
        mock_manager.server.hotspot_calc.calculate_file_hotspot.return_value = mock_score

        result = service.get_hotspot("specific.py")

        mock_manager.server.hotspot_calc.calculate_file_hotspot.assert_called_with("specific.py")
        assert len(result["report"]) == 1

    def test_get_hotspot_md(self, mock_manager):
        """Test get_hotspot_md returns markdown."""
        service = AnalysisService(mock_manager)

        mock_file = MagicMock()
        mock_file.relative_path = "hot.py"
        mock_manager.server.graph_builder.get_files.return_value = [mock_file]

        mock_score = MagicMock()
        mock_score.node_id = "file::hot.py"
        mock_score.total = 8.0
        mock_score.structural = 4.0
        mock_score.semantic = 4.0
        mock_score.issues = [{"type": "complexity", "message": "Too complex"}]
        mock_manager.server.hotspot_calc.get_high_hotspot_nodes.return_value = [mock_score]

        result = service.get_hotspot_md()

        assert "# Hotspot Report" in result
        assert "hot.py" in result

    def test_get_hotspot_raw(self, mock_manager):
        """Test get_hotspot_raw returns structured data."""
        service = AnalysisService(mock_manager)

        mock_file = MagicMock()
        mock_file.relative_path = "test.py"
        mock_manager.server.graph_builder.get_files.return_value = [mock_file]
        mock_manager.server.hotspot_calc.get_high_hotspot_nodes.return_value = []

        result = service.get_hotspot_raw()

        assert "report" in result


class TestRepoMap:
    """Tests for repo map methods."""

    def test_get_repo_map(self, mock_manager):
        """Test get_repo_map returns string."""
        service = AnalysisService(mock_manager)

        mock_manager.server.repomap_gen = MagicMock()
        mock_manager.server.repomap_gen.generate.return_value = (
            "# Repository Map\n\n## src/main.py\n  ⚡ main()"
        )

        result = service.get_repo_map(token_budget=1024)

        assert "Repository Map" in result
        mock_manager.server.repomap_gen.generate.assert_called_once()

    def test_get_repo_map_no_generator(self, mock_manager):
        """Test get_repo_map when generator not initialized."""
        service = AnalysisService(mock_manager)
        mock_manager.server.repomap_gen = None

        result = service.get_repo_map()

        assert "not initialized" in result.lower()

    def test_get_repo_map_raw(self, mock_manager):
        """Test get_repo_map_raw returns dict with map and token_count."""
        service = AnalysisService(mock_manager)

        mock_manager.server.repomap_gen = MagicMock()
        mock_manager.server.repomap_gen.generate.return_value = "map content"

        result = service.get_repo_map_raw(token_budget=1600)

        assert "map" in result
        assert "token_count" in result
        assert result["map"] == "map content"


class TestSubgraph:
    """Tests for subgraph extraction."""

    def test_get_subgraph_single_root(self, mock_manager):
        """Test get_subgraph with single root."""
        service = AnalysisService(mock_manager)

        mock_node = MagicMock()
        mock_node.id = "func::main"
        mock_node.name = "main"
        mock_node.node_type = NodeType.FUNCTION

        mock_manager.server.graph_search.get_subgraph.return_value = ([mock_node], [])

        result = service.get_subgraph("func::main", depth=1)

        assert "nodes" in result
        assert "edges" in result
        assert "mermaid" in result
        assert "stats" in result

    def test_get_subgraph_multiple_roots(self, mock_manager):
        """Test get_subgraph with multiple roots."""
        service = AnalysisService(mock_manager)

        mock_node1 = MagicMock()
        mock_node1.id = "func::a"
        mock_node1.name = "a"
        mock_node1.node_type = NodeType.FUNCTION

        mock_node2 = MagicMock()
        mock_node2.id = "func::b"
        mock_node2.name = "b"
        mock_node2.node_type = NodeType.FUNCTION

        mock_manager.server.graph_search.get_subgraph.side_effect = [
            ([mock_node1], []),
            ([mock_node2], []),
        ]

        result = service.get_subgraph(["func::a", "func::b"])

        assert len(result["nodes"]) == 2

    def test_get_subgraph_max_nodes(self, mock_manager):
        """Test get_subgraph respects max_nodes limit."""
        service = AnalysisService(mock_manager)

        # Create more nodes than max
        mock_nodes = []
        for i in range(300):
            node = MagicMock()
            node.id = f"func::{i}"
            node.name = f"func_{i}"
            node.node_type = NodeType.FUNCTION
            mock_nodes.append(node)

        mock_manager.server.graph_search.get_subgraph.return_value = (mock_nodes, [])

        result = service.get_subgraph("func::0", max_nodes=200)

        assert len(result["nodes"]) <= 200


class TestSymbolInfo:
    """Tests for symbol info retrieval."""

    def test_get_symbol_info_found(self, mock_manager):
        """Test get_symbol_info when node is found."""
        service = AnalysisService(mock_manager)

        mock_node = MagicMock(spec=FunctionNode)
        mock_node.id = "func::test"
        mock_node.name = "test"
        mock_node.node_type = NodeType.FUNCTION
        mock_node.file_path = "test.py"
        mock_node.line_start = 10
        mock_node.line_end = 20

        mock_manager.server.graph_builder.get_node_by_id.return_value = mock_node

        result = service.get_symbol_info("func::test")

        assert result["found"] is True
        assert result["name"] == "test"
        assert result["type"] == "function"

    def test_get_symbol_info_not_found(self, mock_manager):
        """Test get_symbol_info when node not found."""
        service = AnalysisService(mock_manager)
        mock_manager.server.graph_builder.get_node_by_id.return_value = None

        result = service.get_symbol_info("nonexistent")

        assert result["found"] is False
        assert "error" in result

    def test_get_symbol_info_with_body(self, mock_manager):
        """Test get_symbol_info with include_body=True."""
        service = AnalysisService(mock_manager)

        mock_node = MagicMock(spec=FunctionNode)
        mock_node.id = "func::test"
        mock_node.name = "test"
        mock_node.node_type = NodeType.FUNCTION
        mock_node.file_path = "test.py"
        mock_node.line_start = 1
        mock_node.line_end = 3

        mock_manager.server.graph_builder.get_node_by_id.return_value = mock_node
        mock_manager.server.project_root = "/fake/project"

        result = service.get_symbol_info("func::test", include_body=True)

        assert "body" in result


class TestEntrypoints:
    """Tests for entrypoints listing."""

    def test_entrypoints_list_finds_main(self, mock_manager):
        """Test entrypoints_list finds main functions."""
        service = AnalysisService(mock_manager)

        mock_main = MagicMock(spec=FunctionNode)
        mock_main.id = "func::main"
        mock_main.name = "main"
        mock_main.file_path = "app.py"
        mock_main.line_start = 1
        mock_main.line_end = 10
        type(mock_main).node_type = PropertyMock(return_value=NodeType.FUNCTION)

        mock_manager.server.graph_search.search_by_name.return_value = [mock_main]

        result = service.entrypoints_list()

        assert "entrypoints" in result
        assert "count" in result

    def test_entrypoints_list_respects_limit(self, mock_manager):
        """Test entrypoints_list respects limit parameter."""
        service = AnalysisService(mock_manager)

        # Create actual FunctionNode instances (not mocks) for reliable behavior
        mock_funcs = []
        for i in range(5):
            f = FunctionNode(
                id=f"func::main_{i}",
                name="main",
                file_path="app.py",
                line_start=i,
                line_end=i + 5,
                docstring="",
            )
            mock_funcs.append(f)

        # Return same batch for each search call
        mock_manager.server.graph_search.search_by_name.return_value = mock_funcs

        result = service.entrypoints_list(limit=5)

        # Should be limited
        assert len(result["entrypoints"]) <= 5


class TestFindPath:
    """Tests for path finding."""

    def test_find_path_found(self, mock_manager):
        """Test find_path when path exists."""
        service = AnalysisService(mock_manager)

        mock_node1 = MagicMock()
        mock_node1.id = "a"
        mock_node1.name = "a"
        mock_node1.node_type = NodeType.FUNCTION

        mock_node2 = MagicMock()
        mock_node2.id = "b"
        mock_node2.name = "b"
        mock_node2.node_type = NodeType.FUNCTION

        mock_manager.server.graph_search.find_path.return_value = [mock_node1, mock_node2]

        result = service.find_path("a", "b")

        assert result["found"] is True
        assert result["length"] == 2
        assert result["path_length"] == 1  # hops = length - 1

    def test_find_path_not_found(self, mock_manager):
        """Test find_path when no path exists."""
        service = AnalysisService(mock_manager)
        mock_manager.server.graph_search.find_path.return_value = None

        result = service.find_path("a", "b")

        assert result["found"] is False
        assert result["path_length"] == 0
