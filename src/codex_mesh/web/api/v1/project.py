"""
Project API Router.
"""

import asyncio
import json

from fastapi import APIRouter, Depends, Request
from sse_starlette.sse import EventSourceResponse

from ....api.manager import ProjectManager
from ....contracts.status import (
    ConnectRequest,
    ConnectResponse,
    StatusSnapshot,
)
from ....services.project_service import ProjectService
from ...dependencies import get_project_manager, get_project_service

router = APIRouter(prefix="/project", tags=["project"])


@router.get("/status", response_model=dict[str, StatusSnapshot])
async def project_status(ps: ProjectService = Depends(get_project_service)):
    """Get current project status."""
    snapshot = ps.get_status_snapshot()
    return {"status": StatusSnapshot(**snapshot)}


@router.post("/connect", response_model=ConnectResponse)
async def project_connect(req: ConnectRequest, ps: ProjectService = Depends(get_project_service)):
    """Connect to a project."""
    await ps.connect(
        req.project_path,
        background=True,
        auto_index=req.options.auto_index,
        force_reindex=req.options.force_reindex,
        enable_watcher=req.options.watch,
    )
    snapshot = ps.get_status_snapshot()
    return ConnectResponse(ok=True, status=StatusSnapshot(**snapshot))


@router.get("/events")
async def events(request: Request, pm: ProjectManager = Depends(get_project_manager)):
    """SSE stream for status updates."""

    async def gen():
        last = None
        while True:
            if await request.is_disconnected():
                break
            snap = {
                "status": pm.status.value,
                "progress": pm.progress,
                "message": pm.message,
                "project_path": pm.project_path,
            }
            if snap != last:
                yield {"event": "progress", "data": json.dumps(snap)}
                last = snap
            await asyncio.sleep(0.5)

    return EventSourceResponse(gen(), ping=None)
