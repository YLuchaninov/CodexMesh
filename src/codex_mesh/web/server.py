"""
CodexMesh Web Server Entry Point.
"""

import logging

import uvicorn

logger = logging.getLogger(__name__)


def run_web_server(host: str = "0.0.0.0", port: int = 8000, reload: bool = False):
    """Run the uvicorn server."""
    logger.info("Starting CodexMesh Web UI at http://%s:%s", host, port)

    # Auto-connect handling (simplified for web)
    # The actual connection happens inside the app state logic or via UI

    uvicorn.run("codex_mesh.web.app:app", host=host, port=port, reload=reload, log_level="info")


if __name__ == "__main__":
    run_web_server()
