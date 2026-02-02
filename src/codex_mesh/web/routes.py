"""
CodexMesh Web API Routes.
"""

from fastapi import APIRouter

# Re-exports for integration tests
from ..services.analysis_service import AnalysisService as AnalysisService  # noqa: F401
from ..services.fs_service import FileSystemService as FileSystemService  # noqa: F401
from .api.v1 import (
    analysis,
    chats,
    fs,
    graph,
    intents,
    project,
    review,
    system,
    tools,
    tools_detailed,
)

# --- Routers ---

router = APIRouter()  # Included at /api in app.py
router_v1 = APIRouter()  # Included at /api/v1 in app.py

# Include sub-routers
router_v1.include_router(project.router)
router_v1.include_router(fs.router)
router_v1.include_router(analysis.router)
router_v1.include_router(graph.router)
router_v1.include_router(review.router)
router_v1.include_router(intents.router)
router_v1.include_router(chats.router)
router_v1.include_router(system.router)
router_v1.include_router(tools.router)
router_v1.include_router(tools_detailed.router)

# Special case for SSE (/events) if not in project router
router_v1.add_api_route("/events", project.events, methods=["GET"])

# Legacy Exports for Tests
get_system_config = system.get_system_config
update_system_config = system.update_system_config
_get_intent_registry = intents._get_intent_registry

# Legacy /api/reviewer/ask -> /api/v1/reviewer/ask
router.post("/reviewer/ask")(review.ask_reviewer)
router.get("/llm/gemini")(review.get_gemini_config)
router.post("/llm/gemini")(review.set_gemini_config)
router.post("/llm/gemini/test")(review.test_gemini)
