import pytest

from codex_mesh.workflows.engine.input_prep import prepare_intent_input


@pytest.fixture
def mock_intent_def():
    class MockIntent:
        def __init__(self, props):
            self.input_schema = {"properties": props}

    return MockIntent


def test_input_prep_applies_defaults(mock_intent_def):
    props = {
        "depth": {"type": "integer", "default": 5},
        "mode": {"type": "string", "default": "standard"},
    }
    intent = mock_intent_def(props)

    # 1. Empty slots -> defaults
    res = prepare_intent_input(intent, query="test", slots={})
    assert res["depth"] == 5
    assert res["mode"] == "standard"


def test_input_prep_overrides_defaults(mock_intent_def):
    props = {"depth": {"type": "integer", "default": 5}}
    intent = mock_intent_def(props)

    # 2. Slot overrides default
    res = prepare_intent_input(intent, query="test", slots={"depth": 10})
    assert res["depth"] == 10


def test_input_prep_fills_single_required_from_query(mock_intent_def):
    props = {"symbol": {"type": "string"}}
    intent = mock_intent_def(props)

    # 3. Query fills 'symbol'
    res = prepare_intent_input(intent, query="MyClass", slots={})
    assert res["symbol"] == "MyClass"


def test_input_prep_heuristics_numbers(mock_intent_def):
    props = {"depth": {"type": "integer", "default": 1}}
    intent = mock_intent_def(props)

    # 4. Number in query fills depth
    res = prepare_intent_input(intent, query="check depth 8", slots={})
    assert res["depth"] == 8


def test_input_prep_graph_path_parsing(mock_intent_def):
    props = {"from": {"type": "string"}, "to": {"type": "string"}}
    intent = mock_intent_def(props)

    # 5. "from X to Y" pattern
    res = prepare_intent_input(intent, query="find path from Auth to User", slots={})
    assert res["from"] == "Auth"
    assert res["to"] == "User"


def test_input_prep_inline_json(mock_intent_def):
    props = {"depth": {"type": "integer"}}
    intent = mock_intent_def(props)

    # 6. Inline JSON
    res = prepare_intent_input(intent, query='analyze {"depth": 42}', slots={})
    assert res["depth"] == 42
