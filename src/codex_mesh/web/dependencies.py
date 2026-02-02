"""
FastAPI Dependencies for CodexMesh Web API.
"""

from pathlib import Path

from fastapi import Depends, Request

from ..api.manager import ProjectManager
from ..contracts.errors import ApiError
from ..llm.gemini_settings import GeminiSettings
from ..services.analysis_service import AnalysisService
from ..services.chat_service import ChatService
from ..services.fs_service import FileSystemService
from ..services.project_service import ProjectService


def get_intent_registry(request: Request):
    reg = getattr(request.app.state, "intent_registry", None)
    if reg is None:
        from ..workflows.engine.registry import IntentRegistry

        intents_dir = str(Path(__file__).resolve().parents[1] / "workflows" / "definitions")
        reg = IntentRegistry(intents_dir)
        reg.load()
        request.app.state.intent_registry = reg
    return reg


def get_project_manager(request: Request) -> ProjectManager:
    """Get ProjectManager from app state."""
    pm = getattr(request.app.state, "project_manager", None)
    if not pm:
        raise ApiError(500, "Internal", "ProjectManager not initialized")
    return pm


def get_project_service(pm: ProjectManager = Depends(get_project_manager)) -> ProjectService:
    """Get ProjectService instance."""
    return ProjectService(pm)


def get_fs_service(pm: ProjectManager = Depends(get_project_manager)) -> FileSystemService:
    """Get FileSystemService instance."""
    return FileSystemService(pm)


def get_analysis_service(pm: ProjectManager = Depends(get_project_manager)) -> AnalysisService:
    """Get AnalysisService instance."""
    return AnalysisService(pm)


def get_chat_service(
    request: Request, ps: ProjectService = Depends(get_project_service)
) -> ChatService:
    """Get ChatService instance."""
    store = getattr(request.app.state, "chat_store", None)
    if not store:
        raise ApiError(500, "Internal", "ChatStore not initialized")
    return ChatService(store, ps)


def get_gemini_settings(request: Request) -> GeminiSettings:
    """Get GeminiSettings from app state."""
    settings = getattr(request.app.state, "gemini_settings", None)
    if not settings:
        # Fallback if not initialized (though app.py initializes it)
        settings = GeminiSettings()
        request.app.state.gemini_settings = settings
    return settings
