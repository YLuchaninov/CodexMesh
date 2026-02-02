from unittest.mock import MagicMock

import pytest

from codex_mesh.core.nodes import FileNode, FunctionNode, NodeType
from codex_mesh.services.analysis_service import AnalysisService


@pytest.fixture
def mock_manager():
    manager = MagicMock()
    manager.server = MagicMock()
    return manager


def test_analysis_service_resolve_symbol(mock_manager):
    service = AnalysisService(mock_manager)
    mock_node = MagicMock(spec=FunctionNode)
    mock_node.id = "f1"
    mock_node.name = "MyFunc"
    mock_node.node_type = NodeType.FUNCTION
    mock_node.file_path = "a.py"

    mock_manager.server.graph_search.search_by_name.return_value = [mock_node]

    res = service.resolve_symbol("MyFunc")
    assert res["best"]["id"] == "f1"
    assert res["best"]["qualified_name"] == "a.py::MyFunc"
    assert res["count"] == 1
    assert res["confidence"] == 1.0


def test_analysis_service_find_path_not_found(mock_manager):
    service = AnalysisService(mock_manager)
    mock_manager.server.graph_search.find_path.return_value = None

    res = service.find_path("a", "b")
    assert res["found"] is False
    assert res["path_length"] == 0


def test_analysis_service_get_dependency_tree(mock_manager):
    service = AnalysisService(mock_manager)

    n1 = MagicMock(spec=FunctionNode)
    n1.id = "n1"
    n1.name = "n1"
    n1.node_type = NodeType.FUNCTION

    mock_manager.server.graph_search.get_subgraph.return_value = ([n1], [])

    res = service.get_dependency_tree("n1")
    assert "tree" in res
    assert len(res["nodes"]) == 1
    assert res["nodes"][0]["id"] == "n1"


def test_analysis_service_find_dead_code(mock_manager):
    service = AnalysisService(mock_manager)

    n1 = MagicMock(spec=FunctionNode)
    n1.id = "n1"
    n1.name = "n1"
    n1.file_path = "src/a.py"
    n1.line_start = 1
    n2 = MagicMock(spec=FunctionNode)
    n2.id = "n2"
    n2.name = "n2"
    n2.file_path = "src/b.py"
    n2.line_start = 10

    mock_manager.server.graph_builder.graph.nodes.return_value = [n1, n2]

    # Reachable: only n1
    res = service.find_dead_code(["n1"])
    assert res["count"] == 1
    assert res["ids"] == ["n2"]
    assert "n2" in res["likely_dead_md"]


def test_analysis_service_build_module_graph(mock_manager):
    service = AnalysisService(mock_manager)

    f1 = MagicMock(spec=FileNode)
    f1.id = "f1"
    f1.relative_path = "pkg/a.py"

    mock_manager.server.graph_builder.get_files.return_value = [f1]
    mock_manager.server.graph_builder._node_id_to_index = {"f1": 0}
    mock_manager.server.graph_builder.graph.out_edges.return_value = []

    res = service.build_module_graph()
    assert len(res["nodes"]) == 1
    assert res["nodes"][0]["id"] == "pkg"
    assert res["nodes"][0]["type"] == "module"
