from unittest.mock import MagicMock

from codex_mesh.core.nodes import FunctionNode, NodeType
from codex_mesh.services.analysis_service import AnalysisService


def test_get_subgraph_limits():
    mock_pm = MagicMock()
    service = AnalysisService(mock_pm)
    mock_server = mock_pm.server

    # Mock subgraph result with many nodes
    nodes = [
        FunctionNode(
            id=f"n{i}",
            name=f"f{i}",
            file_path="f.py",
            line_start=1,
            line_end=2,
            node_type=NodeType.FUNCTION,
        )
        for i in range(10)
    ]
    edges = []
    mock_server.graph_search.get_subgraph.return_value = (nodes, edges)

    # Call with max_nodes=5
    result = service.get_subgraph("n0", max_nodes=5)

    # Should be truncated
    assert len(result["nodes"]) == 5
    assert result["stats"]["node_count"] == 5


def test_resolve_symbol_no_matches():
    mock_pm = MagicMock()
    service = AnalysisService(mock_pm)
    mock_server = mock_pm.server

    mock_server.graph_search.search_by_name.return_value = []

    res = service.resolve_symbol("unknown")

    assert res["best"] is None
    assert res["count"] == 0
    assert res["confidence"] == 0.0


def test_resolve_symbol_prefer_types():
    mock_pm = MagicMock()
    service = AnalysisService(mock_pm)
    mock_server = mock_pm.server

    # 1 function, 1 file with same name
    f_node = FunctionNode(
        id="func:1",
        name="foo",
        file_path="x.py",
        line_start=1,
        line_end=1,
        node_type=NodeType.FUNCTION,
    )
    # Mocking file node slightly differently if needed, but BaseNode is enough for logic check
    # But AnalysisService checks node_type.value

    mock_server.graph_search.search_by_name.return_value = [f_node]

    res = service.resolve_symbol("foo", prefer_types=["function"])

    # Just verify it runs and applies logic
    assert res["best"]["type"] == "function"
    assert res["best"]["score"] > 1.0  # 1.0 base + 0.2 boost
