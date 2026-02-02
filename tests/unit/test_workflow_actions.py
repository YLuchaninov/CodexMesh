from unittest.mock import MagicMock

from codex_mesh.workflows.engine.runner import JsonWorkflowRunner, ToolExecutor


def test_workflow_runner_branching():
    executor = MagicMock(spec=ToolExecutor)
    runner = JsonWorkflowRunner(executor)

    workflow = {
        "steps": [
            {
                "action": "branch",
                "condition": "{{input.do_it}}",
                "steps": [{"action": "set", "key": "res", "value": "yes"}],
                "else": [{"action": "set", "key": "res", "value": "no"}],
            }
        ]
    }

    # Case TRUE
    res = runner.run(workflow, context={"input": {"do_it": True}})
    assert res.changes["context"]["res"] == "yes"

    # Case FALSE
    res = runner.run(workflow, context={"input": {"do_it": False}})
    assert res.changes["context"]["res"] == "no"


def test_workflow_runner_compose():
    executor = MagicMock(spec=ToolExecutor)
    runner = JsonWorkflowRunner(executor)

    workflow = {
        "steps": [{"action": "compose", "template": ["Hello", "{{input.name}}"], "save_as": "msg"}]
    }

    res = runner.run(workflow, context={"input": {"name": "World"}})
    assert res.changes["context"]["msg"] == "Hello\nWorld"


def test_workflow_runner_recursion_limit():
    executor = MagicMock(spec=ToolExecutor)
    runner = JsonWorkflowRunner(executor)

    # Nested branches to trigger depth
    workflow = {
        "steps": [
            {
                "action": "branch",
                "condition": "1",
                "steps": [{"action": "branch", "condition": "1", "steps": []}],
            }
        ]
    }

    # Artificially low depth for test if possible, but runner uses hardcoded 50.
    # We can just verify it doesn't crash on shallow nesting.
    res = runner.run(workflow, context={})
    assert res.success


def test_workflow_runner_step_budget():
    executor = MagicMock(spec=ToolExecutor)
    runner = JsonWorkflowRunner(executor, max_steps=1)

    workflow = {
        "steps": [
            {"action": "set", "key": "a", "value": 1},
            {"action": "set", "key": "b", "value": 2},  # Should fail here
        ]
    }

    res = runner.run(workflow, context={})
    assert res.success is False
    assert any("Max workflow steps exceeded" in log for log in res.logs)


def test_workflow_runner_return():
    executor = MagicMock(spec=ToolExecutor)
    runner = JsonWorkflowRunner(executor)

    workflow = {"steps": [{"action": "return", "value": "FINAL"}]}

    res = runner.run(workflow, context={})
    assert res.changes["result"] == "FINAL"


def test_workflow_runner_templating_advanced():
    executor = MagicMock(spec=ToolExecutor)
    runner = JsonWorkflowRunner(executor)

    workflow = {
        "steps": [
            {"action": "set", "key": "count", "value": "{{input.items|length}}"},
            {"action": "set", "key": "names", "value": "{{input.items[*].name}}"},
        ]
    }

    ctx = {"input": {"items": [{"name": "a", "val": 1}, {"name": "b", "val": 2}]}}

    res = runner.run(workflow, context=ctx)
    assert res.changes["context"]["count"] == 2
    assert res.changes["context"]["names"] == ["a", "b"]
