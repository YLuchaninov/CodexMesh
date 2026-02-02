"""
CodexMesh API module.

Contains MCP server, tools, and CLI interface.
"""

from .instance import CodexMeshServer
from .manager import ProjectManager
from .server import main
from .tools import register_tools

__all__ = [
    "CodexMeshServer",
    "ProjectManager",
    "main",
    "register_tools",
]
