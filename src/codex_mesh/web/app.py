"""
CodexMesh Web API Application.
"""

from datetime import UTC
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from ..api.manager import ProjectManager
from ..llm.gemini_settings import GeminiSettings
from ..services.logging import setup_logging
from ..storage.chat_store import ChatStore
from .errors import install_error_handlers
from .routes import router, router_v1

setup_logging(level="DEBUG", log_file="codex_mesh_web.log")


def create_app() -> FastAPI:
    """Create and configure the FastAPI app."""
    app = FastAPI(title="CodexMesh Control Plane", version="0.1.0")

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:5173",
            "http://localhost:3000",
            "http://localhost:8000",
            "http://127.0.0.1:5173",
            "http://127.0.0.1:3000",
            "http://127.0.0.1:8000",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def log_requests(request: Request, call_next):
        import logging
        import time

        logger = logging.getLogger("codex_mesh.web.access")
        start_time = time.time()

        response = await call_next(request)

        process_time = time.time() - start_time
        logger.info(
            f"{request.method} {request.url.path} - {response.status_code} - {process_time:.4f}s"
        )
        return response

    @app.middleware("http")
    async def no_cache_index(request: Request, call_next):
        response = await call_next(request)
        path = request.url.path
        if path == "/" or path.endswith("index.html"):
            response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"
        return response

    # Install error handlers
    install_error_handlers(app)

    # Initialize global ProjectManager
    # In a real app, we might use dependency injection overriding
    app.state.project_manager = ProjectManager()
    app.state.gemini_settings = GeminiSettings()

    # Initialize ChatStore
    import os

    env_path = os.getenv("CODEX_MESH_STORAGE_PATH")
    storage_path = Path(env_path) if env_path else Path.cwd() / "data"
    app.state.chat_store = ChatStore(base_path=storage_path)

    # Mount API routes
    app.include_router(router, prefix="/api")
    app.include_router(router_v1, prefix="/api/v1")

    # Health endpoint (P2-2: must be before static files mount)
    @app.get("/health")
    async def health_check():
        """
        Health check endpoint with semantic index stale detection.
        Returns system status, LLM provider availability, and index freshness.
        """
        import hashlib
        import json
        import os
        from datetime import datetime

        from ..llm.routing import providers_available

        env_path = os.getenv("CODEX_MESH_STORAGE_PATH")
        storage_path = Path(env_path) if env_path else Path.cwd() / "data"

        # Get current project path from ProjectManager (P1 fix: use actual project ID)
        pm: ProjectManager = app.state.project_manager
        project_path = pm.project_path
        project_id = None
        project_storage = None

        if project_path:
            # Generate project ID the same way as instance.py
            project_id = hashlib.sha1(
                str(Path(project_path).resolve()).encode("utf-8")
            ).hexdigest()[:12]
            project_storage = storage_path / "projects" / project_id

        # Check semantic index metadata using actual project path
        index_meta = None
        index_stale = False
        index_exists = False

        if project_storage and project_storage.exists():
            index_meta_path = project_storage / "index_meta.json"
            graph_snapshot_path = project_storage / "graph_snapshot.json"

            if index_meta_path.exists():
                try:
                    index_meta = json.loads(index_meta_path.read_text(encoding="utf-8"))
                    index_exists = True

                    # Check if stale: graph snapshot newer than index
                    if graph_snapshot_path.exists():
                        graph_mtime = graph_snapshot_path.stat().st_mtime
                        index_ts = index_meta.get("updated_at_ts", 0)
                        if graph_mtime > index_ts:
                            index_stale = True
                except Exception:
                    pass

        return {
            "ok": True,
            "timestamp": datetime.now(UTC).isoformat(),
            "project": {
                "path": project_path,
                "project_id": project_id,
                "storage_path": str(storage_path),
                "storage_exists": storage_path.exists(),
                "status": pm.status.value,
            },
            "semantic_index": {
                "exists": index_exists,
                "stale": index_stale,
                "chunks_indexed": index_meta.get("chunks_indexed") if index_meta else None,
                "updated_at": index_meta.get("updated_at") if index_meta else None,
            },
            "llm_providers": providers_available(),
        }

    # Mount static files
    static_dir = Path(__file__).parent / "static"
    dist_dir = static_dir / "dist"

    if dist_dir.exists():
        app.mount("/", StaticFiles(directory=str(dist_dir), html=True), name="static")
    elif static_dir.exists():
        app.mount("/", StaticFiles(directory=str(static_dir), html=True), name="static")

    return app


app = create_app()
