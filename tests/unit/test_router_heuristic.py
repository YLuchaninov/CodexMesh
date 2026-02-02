import pytest

from codex_mesh.workflows.engine.router import IntentRouter


# Mock objects needed for router to function without full model
@pytest.fixture
def router():
    r = IntentRouter(model_name="dummy")
    r._embedder = None  # Disable embedder explicitly
    return r


def test_router_heuristic_fallback(router):
    # Setup some basic intents
    intents = [
        {"id": "intent.dead_code", "description": "find dead code", "examples": ["unused code"]},
        {
            "id": "intent.hotspots_report",
            "description": "find hotspots",
            "examples": ["complex code"],
        },
    ]
    router.build_index(intents)

    # 1. Exact phrase match from heuristic map
    m = router.match("find dead code")
    assert m is not None
    assert m.intent_id == "intent.dead_code"

    # 2. Heuristic map keyword
    m = router.match("show unused")
    assert m is not None
    assert m.intent_id == "intent.dead_code"

    # 3. Simple token overlap (fallback)
    m = router.match("report hotspots")
    assert m is not None
    assert m.intent_id == "intent.hotspots_report"


def test_router_no_match(router):
    intents = [{"id": "intent.foo", "description": "bar", "examples": []}]
    router.build_index(intents)

    # Non-matching nonsense
    m = router.match("completely unrelated query about weather")
    assert m is None
