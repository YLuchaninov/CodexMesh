"""Unit tests for the workflow engine."""

from unittest.mock import MagicMock

from codex_mesh.workflows.engine.registry import IntentRegistry
from codex_mesh.workflows.engine.runner import JsonWorkflowRunner, ToolExecutor


def test_intent_registry_load(tmp_path):
    # Create a dummy intent file
    intents_dir = tmp_path / "intents"
    intents_dir.mkdir()
    intent_file = intents_dir / "test_intent.json"
    intent_file.write_text('{"id": "test", "title": "Test Intent", "workflow": {"steps": []}}')

    registry = IntentRegistry(str(intents_dir))
    registry.load()

    assert len(registry.list()) == 1
    assert registry.get("test").title == "Test Intent"


def test_workflow_runner_simple_step():
    executor = MagicMock(spec=ToolExecutor)
    executor.call.return_value = {"result": "hello"}

    runner = JsonWorkflowRunner(executor)
    workflow = {
        "steps": [
            {"action": "tool", "tool_name": "echo", "params": {"msg": "hello"}, "save_as": "out"}
        ]
    }

    res = runner.run(workflow, context={})
    assert res.success
    assert res.changes["context"]["out"]["result"] == "hello"
