import logging

import pytest

from codex_mesh.services.logging import safe_tool


# Mock coroutine that fails
async def failing_tool():
    raise ValueError("Something went wrong")


# Mock coroutine that succeeds
async def succeeding_tool():
    return "Success"


@pytest.mark.asyncio
async def test_safe_tool_handles_exception(caplog):
    # Setup logging to capture stderr/logs
    caplog.set_level(logging.INFO)

    # Wrap the failing tool
    wrapped = safe_tool(failing_tool)

    # Execute
    result = await wrapped()

    # Verify result is a JSON string with structured error (P0 fix: MCP compatible)
    import json

    assert isinstance(result, str)
    error_data = json.loads(result)
    assert error_data["ok"] is False
    assert "error" in error_data
    assert error_data["error"]["tool"] == "failing_tool"
    assert error_data["error"]["type"] == "ValueError"
    assert "Something went wrong" in error_data["error"]["message"]

    # Verify log was captured
    # Note: safe_tool logs at ERROR level
    assert any("Error in tool 'failing_tool'" in record.message for record in caplog.records)
    assert any("ValueError: Something went wrong" in record.message for record in caplog.records)


@pytest.mark.asyncio
async def test_safe_tool_passes_success():
    wrapped = safe_tool(succeeding_tool)
    result = await wrapped()
    assert result == "Success"
