"""
Project MCP Tools.
"""

from mcp.server.fastmcp import FastMCP

from ....services.logging import safe_tool
from ....services.project_service import ProjectService


def register_project_tools(server: FastMCP, project_service: ProjectService):
    @server.tool()
    @safe_tool
    async def connect_to_project(
        path: str,
        auto_index: bool = True,
        force_reindex: bool = False,
        enable_watcher: bool = False,
    ) -> str:
        """
        Connect to a project to analyze.

        Args:
            path: Absolute path to the project root
            auto_index: Whether to auto-index for semantic search
            force_reindex: Force reindexing even if index exists
            enable_watcher: Enable live file watching (experimental)
        """
        await project_service.connect(
            path,
            auto_index=auto_index,
            force_reindex=force_reindex,
            enable_watcher=enable_watcher,
        )
        return f"Connecting to project at {path}... Use get_server_status to check progress."

    @server.tool()
    @safe_tool
    async def project_switch(project_id: str) -> str:
        """Switch context (Simulated)."""
        return f"Switched active project to: {project_id} (Simulated)"

    @server.tool()
    @safe_tool
    async def get_server_status() -> str:
        """Get project status message."""
        return f"Status: {project_service.status.value}\nProgress: {project_service.progress}%\nMessage: {project_service.message}\nProject: {project_service.project_path or 'None'}"

    @server.tool()
    @safe_tool
    async def get_status_snapshot() -> dict:
        """Get structured status snapshot."""
        return project_service.get_status_snapshot()
