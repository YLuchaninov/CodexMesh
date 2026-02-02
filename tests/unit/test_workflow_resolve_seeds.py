from codex_mesh.services.workflow_tool_service import WorkflowToolService


class DummyAnalysis:
    pass


class DummyTracing:
    pass


def test_resolve_seeds_normalizes_node_id_and_id():
    svc = WorkflowToolService(DummyAnalysis(), DummyTracing())

    # Semantic search payloads often use node_id; lexical payloads may use id.
    semantic = [{"node_id": "N1", "score": 0.9}]
    lex = [{"id": "N1"}]

    out = svc.resolve_seeds(semantic_hits=semantic, lex_hits=lex, max_seeds=5)
    assert out["ids"] == ["N1"]
    assert out["root_ids"] == ["N1"]
    assert out["count"] == 1


def test_resolve_seeds_lex_only_node_id():
    svc = WorkflowToolService(DummyAnalysis(), DummyTracing())

    out = svc.resolve_seeds(lex_hits=[{"node_id": "N2"}], max_seeds=5)
    assert out["ids"] == ["N2"]
