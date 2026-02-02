"""
Validation tests for intent JSON files.
"""

import json
from pathlib import Path

import pytest


def get_intent_files():
    """Get all intent JSON files from the source directory."""
    base_dir = Path(__file__).parent.parent.parent
    intents_dir = base_dir / "src" / "codex_mesh" / "workflows" / "definitions"
    return list(intents_dir.glob("*.json"))


@pytest.mark.parametrize("intent_file", get_intent_files())
def test_intent_file_validity(intent_file):
    """Verify that each intent file is valid JSON and has required fields."""
    with open(intent_file) as f:
        data = json.load(f)

    # Required top-level fields
    assert "id" in data
    assert "name" in data
    assert "description" in data
    assert "steps" in data

    # ID should match filename (convention)
    # intent.change_impact.json -> intent.change_impact
    expected_id = intent_file.stem
    assert data["id"] == expected_id

    # Steps should be a list
    assert isinstance(data["steps"], list)
    assert len(data["steps"]) > 0

    # Each step should have an action
    for step in data["steps"]:
        assert "action" in step
        assert step["action"] in ["tool", "branch", "loop", "return", "compose", "llm"]


def test_no_duplicate_intent_ids():
    """Verify that all intent IDs are unique."""
    files = get_intent_files()
    ids = []
    for f in files:
        with open(f) as f_in:
            data = json.load(f_in)
            ids.append(data["id"])

    assert len(ids) == len(set(ids)), f"Duplicate intent IDs found: {ids}"
