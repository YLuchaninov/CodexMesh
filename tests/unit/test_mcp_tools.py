from unittest.mock import MagicMock, patch

import pytest
from mcp.server.fastmcp import FastMCP

from codex_mesh.api.manager import ProjectManager, ProjectStatus
from codex_mesh.api.tools import register_tools


@pytest.fixture
def mock_pm():
    pm = MagicMock(spec=ProjectManager)
    pm.status = ProjectStatus.READY
    pm.project_path = "/mock"
    pm.progress = 100
    pm.message = "Ready"
    pm.server = MagicMock()
    return pm


@pytest.fixture
def mcp_server():
    return FastMCP("TestServer")


@pytest.mark.asyncio
async def test_register_tools(mcp_server, mock_pm):
    register_tools(mcp_server, mock_pm)
    tools_list = await mcp_server.list_tools()
    tool_names = [t.name for t in tools_list]
    assert "connect_to_project" in tool_names
    assert "get_server_status" in tool_names
    assert "read_file" in tool_names


@pytest.mark.asyncio
async def test_tool_invocation_get_status(mcp_server, mock_pm):
    register_tools(mcp_server, mock_pm)
    res = await mcp_server.call_tool("get_server_status", arguments={})
    assert any("Status: READY" in str(c) for c in res)


@pytest.mark.asyncio
async def test_tool_read_file_error(mcp_server, mock_pm):
    with patch("codex_mesh.api.tools.FileSystemService") as MockFS:
        mock_fs = MockFS.return_value
        mock_fs.read_file.side_effect = Exception("File not readable")
        register_tools(mcp_server, mock_pm)
        res = await mcp_server.call_tool("read_file", arguments={"path": "missing.txt"})
        assert any("File not readable" in str(c) for c in res)


@pytest.mark.asyncio
async def test_ensure_ready_fail(mcp_server, mock_pm):
    with patch("codex_mesh.api.tools.ProjectService") as MockPS:
        mock_ps = MockPS.return_value
        mock_ps.ensure_ready.side_effect = RuntimeError("Server is busy")
        register_tools(mcp_server, mock_pm)
        res = await mcp_server.call_tool("read_file", arguments={"path": "test.py"})
        assert any("Server is busy" in str(c) for c in res)


@pytest.mark.asyncio
async def test_execute_intent_tool(mcp_server, mock_pm):
    with patch("codex_mesh.workflows.engine.runner.JsonWorkflowRunner") as MockRunner:
        runner = MockRunner.return_value
        runner.run.return_value = MagicMock(success=True, changes={"result": "it worked"}, logs=[])

        # Patch IntentRegistry AT SOURCE
        with (
            patch("codex_mesh.workflows.engine.input_prep.prepare_intent_input", return_value={}),
            patch("codex_mesh.workflows.engine.registry.IntentRegistry") as MockReg,
        ):
            mock_reg_inst = MockReg.return_value
            mock_reg_inst.get.return_value = MagicMock(id="test_id")

            register_tools(mcp_server, mock_pm)
            res = await mcp_server.call_tool(
                "execute_intent", arguments={"intent_id": "test_id", "args": {"query": "test"}}
            )
            assert any("it worked" in str(c) for c in res)
