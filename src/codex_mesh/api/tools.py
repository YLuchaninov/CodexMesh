"""MCP tool registry for CodexMesh."""

from mcp.server.fastmcp import FastMCP

from ..api.manager import ProjectManager
from ..services.analysis_service import AnalysisService
from ..services.fs_service import FileSystemService
from ..services.project_service import ProjectService
from .mcp.v1 import (
    analysis as analysis_mcp,
)
from .mcp.v1 import (
    fs as fs_mcp,
)
from .mcp.v1 import (
    graph as graph_mcp,
)
from .mcp.v1 import (
    intents as intents_mcp,
)
from .mcp.v1 import (
    project as project_mcp,
)


def register_tools(
    server: FastMCP,
    project_manager: ProjectManager,
) -> None:
    """
    Register all MCP tools with the server.
    """

    # Initialize services
    project_service = ProjectService(project_manager)
    fs_service = FileSystemService(project_manager)
    analysis_service = AnalysisService(project_manager)

    # Register groups
    project_mcp.register_project_tools(server, project_service)
    fs_mcp.register_fs_tools(server, fs_service, project_service)
    analysis_mcp.register_analysis_tools(server, analysis_service, project_service)
    graph_mcp.register_graph_tools(server, analysis_service, project_service)
    intents_mcp.register_intent_tools(server, analysis_service, project_service)
