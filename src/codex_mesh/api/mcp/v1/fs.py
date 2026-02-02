"""
File System MCP Tools.
"""

from mcp.server.fastmcp import FastMCP

from ....services.fs_service import FileSystemService
from ....services.logging import safe_tool
from ....services.project_service import ProjectService


def register_fs_tools(
    server: FastMCP, fs_service: FileSystemService, project_service: ProjectService
):
    def ensure_ready():
        project_service.ensure_ready()

    @server.tool()
    @safe_tool
    async def read_file(path: str) -> str:
        """Read file contents."""
        ensure_ready()
        return fs_service.read_file(path)

    @server.tool()
    @safe_tool
    async def list_directory(path: str = ".") -> str:
        """List directory contents."""
        ensure_ready()
        return fs_service.list_directory(path)
