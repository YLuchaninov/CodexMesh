"""
CodexMesh MCP Server.

Entry point for the MCP server providing code analysis tools.
Per architecture.md: No global state - use dependency injection.
"""

import asyncio
import io
import logging
import os

# Initialize logging with sane defaults (INFO for production)
# Can be overridden via CODEX_MESH_LOG_LEVEL env var
import os as _os
import sys
from contextlib import asynccontextmanager
from pathlib import Path

import mcp.server.stdio
from mcp.server.fastmcp import FastMCP

from ..services.logging import setup_logging
from .manager import ProjectManager
from .tools import register_tools

_log_level = _os.environ.get("CODEX_MESH_LOG_LEVEL", "INFO")
setup_logging(level=_log_level, log_file="codex_mesh_mcp.log")
logger = logging.getLogger("codex_mesh")


class SafeJSONIOWrapper(io.TextIOWrapper):
    """
    Wrapper that filters out empty lines or non-JSON input to prevent
    validation errors in the MCP server when running in a terminal.

    HACK: This monkey-patches `mcp.server.stdio.TextIOWrapper` to allow
    interactive use or debugging without crashing on newlines/noise.
    Ideally, we should implement a clean transport layer or middleware,
    but this is the most robust way to handle FastMCP's internal stdio use.
    """

    def readline(self, *args, **kwargs):
        while True:
            line = super().readline(*args, **kwargs)
            # Propagate EOF
            if not line:
                return line

            stripped = line.strip()
            # 1. Skip empty lines (e.g. User pressing Enter)
            if not stripped:
                continue

            # 2. Skip obvious non-JSON (doesn't start with '{' or '[')
            # Both single objects and batch arrays are valid JSON-RPC
            if not stripped.startswith("{") and not stripped.startswith("["):
                continue

            return line


# Monkey-patch mcp.server.stdio to use our filtered wrapper
mcp.server.stdio.TextIOWrapper = SafeJSONIOWrapper  # type: ignore[misc, assignment]

if sys.stdin.isatty():
    logger.warning("Running in interactive mode. This server expects JSON-RPC via stdin.")
    logger.warning("If you are testing manually, type valid JSON-RPC messages.")
    logger.warning(
        "If you are using an MCP client (Claude/Cursor), this warning is expected if they use a PTY."
    )

# Initialize ProjectManager (Singleton for the process)
project_manager = ProjectManager()


@asynccontextmanager
async def lifespan(server: FastMCP):
    """
    Lifespan context manager for startup/shutdown logic.
    """
    # Startup logic
    env_root = os.environ.get("CODEX_MESH_PROJECT_ROOT")
    meta = project_manager.load_metadata()
    last_root = meta.get("last_project_path")

    if env_root:
        logger.info(f"Auto-connecting to project from env: {env_root}")
        asyncio.create_task(project_manager.connect(env_root, background=True))
    elif last_root:
        logger.info(f"Auto-reconnecting to last project: {last_root}")
        asyncio.create_task(project_manager.connect(last_root, background=True))
    else:
        # Default to CWD scan
        cwd = os.getcwd()
        if (Path(cwd) / ".git").exists() or (Path(cwd) / "pyproject.toml").exists():
            logger.info(f"Auto-connecting to current directory: {cwd}")
            asyncio.create_task(project_manager.connect(cwd, background=True))

    # Optional: start the Web UI in the same process (primarily for local dev / all-in-one runs).
    # IMPORTANT: The dedicated `web` service runs separately (see docker-compose.yml), so this is OFF by default.
    enable_web = os.environ.get("CODEX_MESH_ENABLE_WEB_UI", "").strip().lower() in (
        "1",
        "true",
        "yes",
        "on",
    )
    if enable_web:
        try:
            import threading

            from ..web.server import run_web_server
        except Exception as e:
            logger.warning("Web UI requested (CODEX_MESH_ENABLE_WEB_UI=1) but unavailable: %s", e)
        else:
            host = os.environ.get("CODEX_MESH_WEB_HOST", "0.0.0.0")
            port = int(os.environ.get("CODEX_MESH_WEB_PORT", "8000"))
            # Daemon thread so it dies when the main process dies
            web_thread = threading.Thread(
                target=run_web_server, kwargs={"host": host, "port": port}, daemon=True
            )
            web_thread.start()
            logger.info("Web UI started in background thread on %s:%s", host, port)

    yield

    # Shutdown logic
    if project_manager.server:
        await project_manager.server.stop_watcher()


# Create server instance at module level for uvicorn
mcp_server = FastMCP("CodexMesh", lifespan=lifespan)

# Register tools
register_tools(mcp_server, project_manager)


# Add server info resource
@mcp_server.resource("info://codex-mesh/stats")
async def get_stats() -> str:
    """Get statistics about the indexed codebase."""
    if project_manager.status.value != "READY" or not project_manager.server:
        return f"Server not ready. Status: {project_manager.status.value}"

    stats = project_manager.server.get_stats()
    project_root = project_manager.server.project_root

    return f"""# CodexMesh Server Statistics

Project: {project_root}

## Indexed Content
- Files: {stats["files"]}
- Classes: {stats["classes"]}
- Functions: {stats["functions"]}
- Total Nodes: {stats["total_nodes"]}
- Total Edges: {stats["total_edges"]}
"""


def main() -> None:
    """Main entry point for CLI usage."""
    try:
        # If running via CLI, lifespan might not auto-trigger depending on FastMCP version logic,
        # but usually .run() handles it.
        logger.info("Starting CodexMesh MCP server...")
        mcp_server.run()
    except KeyboardInterrupt:
        logger.info("Server stopped")
    except Exception as e:
        logger.error("Error: %s", e, exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
