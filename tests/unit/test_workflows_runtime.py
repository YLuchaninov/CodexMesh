from unittest.mock import MagicMock

import pytest

from codex_mesh.workflows.runtime import RuntimeFactory


@pytest.fixture
def tools():
    mock_analysis = MagicMock()
    mock_registry = MagicMock()
    return RuntimeFactory._build_tools(mock_analysis, mock_registry)


def test_resolve_seeds(tools):
    _resolve_seeds = tools["resolve_seeds"]

    # Test with semantic matches
    semantic_matches = {"matches": [{"id": "n1", "score": 0.8}, {"id": "n2", "score": 0.6}]}
    res = _resolve_seeds({"semantic_matches": semantic_matches})
    assert res["ids"] == ["n1", "n2"]

    # Test with lexical matches and hits
    lex_hits = [{"id": "n2", "score": 0.5}, {"id": "n3", "score": 0.5}]
    res = _resolve_seeds({"semantic_hits": semantic_matches, "lex_hits": lex_hits})
    # n2 gets +0.5, so n2 (1.1) > n1 (0.8) > n3 (0.5)
    assert res["ids"] == ["n2", "n1", "n3"]


def test_rank_subgraph_nodes(tools):
    _rank_subgraph_nodes = tools["rank_subgraph_nodes"]

    nodes = [
        {"id": "n1", "name": "Node1", "type": "function"},
        {"id": "n2", "name": "Node2", "type": "class"},
        {"id": "n3", "name": "Node3", "type": "file"},
    ]
    edges = [
        {"source": "n1", "target": "n2"},
        {"source": "n3", "target": "n2"},
        {"source": "n1", "target": "n3"},
    ]

    res = _rank_subgraph_nodes({"nodes": nodes, "edges": edges, "top_k": 2})
    assert len(res["top_n"]) == 2
    assert "Degree: 2" in res["markdown_list"]


def test_pick_best_entrypoint(tools):
    _pick_best_entrypoint = tools["pick_best_entrypoint"]

    eps = {"entrypoints": [{"id": "e1", "name": "main"}, {"id": "e2", "name": "serve"}]}

    # Query match
    res = _pick_best_entrypoint({"query": "serve", "entrypoints": eps})
    assert res["best"]["id"] == "e2"

    # Fallback to first
    res = _pick_best_entrypoint({"query": "missing", "entrypoints": eps})
    assert res["best"]["id"] == "e1"

    # No entrypoints
    assert _pick_best_entrypoint({"entrypoints": None})["best"] is None


def test_detect_cycles(tools):
    _detect_cycles = tools["detect_cycles"]

    # Cycle: n1 -> n2 -> n1
    edges = [
        {"source": "n1", "target": "n2", "type": "calls"},
        {"source": "n2", "target": "n1", "type": "calls"},
    ]
    res = _detect_cycles({"edges": edges})
    assert len(res["cycles"]) == 1
    assert "n1 -> n2 -> n1" in res["summary_md"]

    # No edges
    assert "No edges" in _detect_cycles({"edges": None})["summary_md"]


def test_summarize_hotspots(tools):
    _summarize_hotspots = tools["summarize_hotspots"]

    report = [
        {"node_id": "n1", "total": 10.5, "issues": [1, 2]},
        {"node_id": "n2", "total": 5.2, "issues": [1]},
    ]
    res = _summarize_hotspots({"report": report, "limit": 1})
    assert "n1" in res["markdown"]
    assert "10.50" in res["markdown"]
    assert "n2" not in res["markdown"]


def test_tracing_tools(tools):
    _trace_start = tools["trace_start"]
    _trace_wait = tools["trace_wait"]
    _trace_stop = tools["trace_stop"]

    res = _trace_start({"scenario": "test"})
    tid = res["id"]
    assert res["status"] == "started"

    res = _trace_wait({"trace_id": tid, "duration": 0.1})
    assert res["status"] == "done"

    res = _trace_stop({"trace_id": tid})
    assert res["status"] == "stopped"


def test_hotspot_in_scope(tools):
    _hotspot_in_scope = tools["hotspot_in_scope"]

    # Mock analysis is already in tools fixture, but let's re-examine if we can access it
    # Implementation uses `analysis.get_hotspot()`
    # We might need to mock it specifically if we want to check values

    nodes = [{"id": "n1"}, {"id": "n2"}]
    res = _hotspot_in_scope({"nodes": nodes})
    assert "report" in res
    assert "summary_md" in res


def test_join_hotspot_scores(tools):
    _join_hotspot_scores = tools["join_hotspot_scores"]

    ranked = [{"id": "n1", "name": "Node1"}, {"id": "n2", "name": "Node2"}]
    hotspots = [
        {"node_id": "n1", "total": 8.0, "issues": []},
        {"node_id": "n2", "total": 2.0, "issues": []},
    ]
    res = _join_hotspot_scores({"ranked": ranked, "hotspots": hotspots})
    assert res["joined"][0]["hotspot_score"] == 8.0
    assert "🔥" in res["top_markdown_list"]


def test_path_to_subgraph(tools):
    _path_to_subgraph = tools["path_to_subgraph"]

    path_result = {"path": [{"id": "n1"}, {"id": "n2"}, {"id": "n3"}]}
    res = _path_to_subgraph({"path_result": path_result})
    assert len(res["nodes"]) == 3
    assert len(res["edges"]) == 2
    assert res["edges"][0]["source"] == "n1"
    assert res["edges"][0]["target"] == "n2"


def test_render_graph(tools):
    _render_graph = tools["render_graph"]

    nodes = [{"id": "n1", "name": "N1", "type": "function"}]
    edges = []
    res = _render_graph({"nodes": nodes, "edges": edges})
    assert "graph" in res["content"]
    assert "N1" in res["content"]


def test_check_layering_rules(tools):
    _check_layering_rules = tools["check_layering_rules"]

    # Violation case
    module_graph = {
        "edges": [{"source": "src.core.logic", "target": "src.web.api", "type": "imports"}]
    }
    res = _check_layering_rules({"module_graph": module_graph})
    assert "Layering violations" in res["markdown"]

    # No violation case
    module_graph_ok = {
        "edges": [{"source": "src.web.api", "target": "src.core.logic", "type": "imports"}]
    }
    res = _check_layering_rules({"module_graph": module_graph_ok})
    assert "No obvious layering violations" in res["markdown"]


def test_rank_impact(tools):
    _rank_impact = tools["rank_impact"]

    up_nodes = [{"id": "n1", "name": "Impacted1"}, {"id": "n2"}]
    res = _rank_impact({"up_nodes": up_nodes})
    assert "Impacted1" in res["markdown_list"]


def test_summarize_security_hits(tools):
    _summarize_security_hits = tools["summarize_security_hits"]

    matches = [{"name": "SQL Injection", "content": "SELECT * FROM users WHERE id = " + "1"}]
    res = _summarize_security_hits({"matches": matches})
    assert "⚠️" in res["markdown"]
    assert "SQL Injection" in res["markdown"]
