"""
Unit tests for the Intent Router.
"""

from unittest.mock import MagicMock, patch

import pytest

from codex_mesh.workflows.engine.router import IntentRouter, _cosine


def test_cosine_similarity():
    """Test the internal cosine similarity function."""
    a = [1.0, 0.0, 0.0]
    b = [1.0, 0.0, 0.0]
    assert _cosine(a, b) == pytest.approx(1.0)

    c = [0.0, 1.0, 0.0]
    assert _cosine(a, c) == pytest.approx(0.0)

    d = [1.0, 1.0, 0.0]
    # Similarity should be 1/sqrt(2) ~= 0.707
    assert _cosine(a, d) == pytest.approx(0.70710678)


@pytest.fixture
def mock_embedder():
    """Fixture to mock TextEmbedding with HAS_FASTEMBED=True."""
    with (
        patch("codex_mesh.workflows.engine.router.HAS_FASTEMBED", True),
        patch("codex_mesh.workflows.engine.router.TextEmbedding") as mock_class,
    ):
        embedder = MagicMock()
        mock_class.return_value = embedder
        # Default side effect: return zero vector
        embedder.embed.side_effect = lambda texts: iter([[0.0] * 384 for _ in texts])
        yield embedder


def test_router_init(mock_embedder):
    """Test router initialization."""
    router = IntentRouter(threshold=0.7)
    assert router._threshold == 0.7
    assert router._embedder is mock_embedder


def test_router_build_index(mock_embedder):
    """Test building the intent index."""
    router = IntentRouter()

    intents = [
        {"id": "search", "description": "Search code", "examples": ["find something"]},
        {"id": "review", "description": "Review quality", "examples": ["check code"]},
    ]

    # Mock examples to return specific vectors
    vec_search = [1.0] + [0.0] * 383
    vec_review = [0.0, 1.0] + [0.0] * 382

    # Simple side effect logic for building index
    def side_effect(texts):
        results = []
        for t in texts:
            if "Search" in t:
                results.append(vec_search)
            else:
                results.append(vec_review)
        return iter(results)

    mock_embedder.embed.side_effect = side_effect

    router.build_index(intents)

    assert len(router._index) == 2
    assert router._index[0][0] == "search"
    assert router._index[1][0] == "review"


def test_router_match_success(mock_embedder):
    """Test matching a query to an intent."""
    router = IntentRouter(threshold=0.5)

    # Pre-populate index with mock vectors
    vec_search = [1.0] + [0.0] * 383
    vec_review = [0.0, 1.0] + [0.0] * 382
    router._index = [("search", vec_search), ("review", vec_review)]

    # Mock query embedding to match 'search' exactly
    mock_embedder.embed.side_effect = lambda texts: iter([vec_search for _ in texts])

    match = router.match("find function")

    assert match is not None
    assert match.intent_id == "search"
    assert match.score == pytest.approx(1.0)


def test_router_match_below_threshold(mock_embedder):
    """Test that matches below threshold are ignored."""
    router = IntentRouter(threshold=0.9)

    vec_search = [1.0] + [0.0] * 383
    router._index = [("search", vec_search)]

    # Mock query embedding with low similarity (perpendicular)
    vec_query = [0.0, 1.0] + [0.0] * 382
    mock_embedder.embed.side_effect = lambda texts: iter([vec_query for _ in texts])

    match = router.match("random text")
    assert match is None


def test_router_route_compatibility(mock_embedder):
    """Test legacy route() method."""
    router = IntentRouter(threshold=0.1)

    vec_search = [1.0] + [0.0] * 383
    router._index = [("search", vec_search)]

    # Match search
    mock_embedder.embed.side_effect = lambda texts: iter([vec_search for _ in texts])

    intent_id, slots = router.route("find it")
    assert intent_id == "search"
    assert slots == {}
