"""
System API Router.
"""

from dataclasses import asdict
from typing import Any

from fastapi import APIRouter, Depends

from ....api.manager import ProjectManager
from ...dependencies import get_project_manager

router = APIRouter(prefix="/system", tags=["system"])


@router.get("/config")
async def get_system_config(pm: ProjectManager = Depends(get_project_manager)):
    """Get current system configuration."""
    if pm.server:
        return pm.server.context.config.to_dict()
    # Fallback to global user config
    return pm.load_user_config().to_dict()


@router.post("/config")
async def update_system_config(
    updates: dict[str, Any], pm: ProjectManager = Depends(get_project_manager)
):
    """Update system configuration."""
    if pm.server:
        pm.server.context.config.update_from_dict(updates)
        pm.save_user_config()
        return pm.server.context.config.to_dict()

    # Update global config file even if no project connected
    config = pm.load_user_config()
    config.update_from_dict(updates)
    config.save_to_file(pm._get_config_path())
    return config.to_dict()


@router.get("/diagnostics")
async def get_diagnostics(pm: ProjectManager = Depends(get_project_manager)):
    """Get system health and diagnostics."""
    if not pm.server:
        return {
            "status": "IDLE",
            "message": "No project connected",
            "errors": [],
            "components": {},
        }

    server = pm.server
    reg = server.graph_builder.registry

    return {
        "status": pm.status,
        "project": str(server.project_root),
        "errors": getattr(reg, "validation_errors", []),
        "components": {
            "extractors": {
                "active": list(reg.supported_extensions()),
                "stats": asdict(reg.stats()),
            },
            "embedding": {
                "model": server.context.config.embedding.model,
                "has_index": server.vector_search.has_index(),
                "docs_enabled": server.context.config.docs.enabled,
            },
            "watcher": {"active": hasattr(server, "watcher") and server.watcher is not None},
        },
    }
