"""
Unit tests for TracingService integration in JsonWorkflowRunner.
"""

from unittest.mock import Mock

from codex_mesh.services.tracing_service import TracingService
from codex_mesh.workflows.engine.runner import JsonWorkflowRunner, ToolExecutor


def test_workflow_runner_tracing():
    """Test that JsonWorkflowRunner correctly logs steps to TracingService."""
    # Setup
    mock_tool_fn = Mock(return_value={"status": "ok"})
    executor = ToolExecutor(tools={"test_tool": mock_tool_fn})

    tracing = TracingService()
    tracing.start_trace("wf-trace")

    runner = JsonWorkflowRunner(executor, tracing=tracing)

    workflow = {
        "steps": [
            {"action": "tool", "tool_name": "test_tool", "params": {"arg": "val"}, "save_as": "res"}
        ]
    }

    # Act
    res = runner.run(workflow, context={})

    # Assert
    assert res.success is True

    # Verify tracing session has the step
    graph = tracing.get_trace_subgraph("wf-trace")
    # Start + step_0
    assert len(graph["nodes"]) == 2

    tool_node = graph["nodes"][1]
    assert tool_node["name"] == "test_tool"
    assert tool_node["type"] == "tool"
    assert tool_node["data"]["input"] == {"arg": "val"}
    assert tool_node["data"]["output"] == {"status": "ok"}
