"""
Project Manager for CodexMesh.

Handles dynamic project switching, initialization, and status reporting.
"""

import asyncio
import contextlib
import enum
import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ..config import CodexMeshConfig
from ..core.context import AppContext
from ..core.events import EventBus
from .instance import CodexMeshServer

logger = logging.getLogger(__name__)


class ProjectStatus(str, enum.Enum):
    """Status of the current project connection."""

    IDLE = "IDLE"  # No project connected
    LOADING = "LOADING"  # Connecting and indexing
    READY = "READY"  # Connected and ready to use
    ERROR = "ERROR"  # Failed to connect


@dataclass
class ProjectState:
    """Current state of the project manager."""

    status: ProjectStatus = ProjectStatus.IDLE
    project_path: str | None = None
    progress: int = 0
    message: str = "Waiting for project connection..."
    error: str | None = None
    server: CodexMeshServer | None = None


class ProjectManager:
    """
    Manages the lifecycle of the CodexMeshServer instance.
    Allows dynamic switching between projects and reports status.
    Shared instance (Singleton) across the application.
    """

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._state = ProjectState()
        self._lock = asyncio.Lock()
        self._init_task: asyncio.Task | None = None
        self._loop: asyncio.AbstractEventLoop | None = None
        self._initialized = True

    def _get_meta_path(self) -> Path:
        """Path for project manager metadata (last project etc)."""
        return Path.home() / ".codex-mesh-meta.json"

    def _get_config_path(self) -> Path:
        """Path for global user configuration."""
        return Path.home() / ".codex-mesh.json"

    def _save_metadata(self) -> None:
        """Persist project manager metadata."""
        try:
            data = {
                "last_project_path": self._state.project_path,
            }
            self._get_meta_path().write_text(json.dumps(data, indent=2))
        except Exception:
            logger.warning("Failed to save project metadata", exc_info=True)

    def load_metadata(self) -> dict[str, Any]:
        """Load project manager metadata."""
        path = self._get_meta_path()
        if path.exists():
            try:
                return json.loads(path.read_text())
            except Exception:
                pass
        return {}

    def load_user_config(self) -> CodexMeshConfig:
        """Load global user configuration or return defaults."""
        config = CodexMeshConfig()
        path = self._get_config_path()
        if path.exists():
            try:
                data = json.loads(path.read_text())
                config.update_from_dict(data)
                logger.debug(f"Loaded user config from {path}")
            except Exception:
                logger.warning(f"Failed to load user config from {path}", exc_info=True)

        # Apply environment overrides last (highest precedence)
        config.update_from_env()
        return config

    def save_user_config(self) -> None:
        """Save the current server configuration to global path."""
        if self.server:
            try:
                self.server.context.config.save_to_file(self._get_config_path())
                logger.info(f"Saved user config to {self._get_config_path()}")
            except Exception:
                logger.warning("Failed to save user config", exc_info=True)

    @classmethod
    def _reset_singleton(cls):
        """Reset the singleton instance for testing purposes."""
        cls._instance = None

    @property
    def status(self) -> ProjectStatus:
        return self._state.status

    @property
    def progress(self) -> int:
        return self._state.progress

    @property
    def message(self) -> str:
        return self._state.message

    @property
    def server(self) -> CodexMeshServer | None:
        return self._state.server

    @property
    def project_path(self) -> str | None:
        return self._state.project_path

    async def connect(
        self,
        path: str,
        *,
        background: bool = True,
        auto_index: bool = True,
        force_reindex: bool = False,
        enable_watcher: bool = False,
        docs_enabled: bool | None = None,
    ) -> None:
        """
        Connect to a new project.

        Args:
            path: Path to the project root
            background: If True, run initialization in background task.
                       If False, await initialization.
            auto_index: Whether to auto-index for semantic search
            force_reindex: Force reindex even if index exists
        """
        async with self._lock:
            self._loop = asyncio.get_running_loop()

            # Cancel any existing connection process
            if self._init_task and not self._init_task.done():
                self._init_task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await self._init_task

            # Stop any previously running server (important when reconnecting)
            old_server = self._state.server

            # Reset state
            self._state = ProjectState(
                status=ProjectStatus.LOADING,
                project_path=path,
                progress=0,
                message=f"Initializing project at {path}...",
            )

            # Start initialization task
            self._init_task = asyncio.create_task(
                self._initialize_project(
                    path,
                    auto_index=auto_index,
                    force_reindex=force_reindex,
                    enable_watcher=enable_watcher,
                    docs_enabled=docs_enabled,
                )
            )

        # Cleanup old server outside the lock
        if old_server is not None:
            try:
                await old_server.shutdown()
            except Exception:
                logger.warning("Failed to shutdown previous server", exc_info=True)

        if not background and self._init_task:
            await self._init_task

    async def _initialize_project(
        self,
        path: str,
        *,
        auto_index: bool,
        force_reindex: bool,
        enable_watcher: bool,
        docs_enabled: bool | None = None,
    ) -> None:
        """Background initialization task."""
        try:
            logger.info(f"Starting initialization for {path}")

            # progress 10%: Validation
            self._update_progress(10, "Validating project path...")
            project_root = Path(path).resolve()

            if not project_root.exists() or not project_root.is_dir():
                raise ValueError(f"Invalid project path: {path}")

            # progress 20%: creating server instance
            self._update_progress(20, "Creating server instance...")

            # Run blocking init in thread
            server = await asyncio.to_thread(
                self._create_and_init_server,
                str(project_root),
                auto_index,
                force_reindex,
                docs_enabled,
            )

            # Optionally start file watcher
            if enable_watcher:
                self._update_progress(95, "Starting file watcher...")
                try:
                    await server.start_watcher()
                except Exception:
                    logger.warning("Failed to start watcher", exc_info=True)

            # progress 100%: Ready
            self._state.server = server
            self._state.status = ProjectStatus.READY
            self._state.progress = 100
            self._state.message = f"Ready. Connected to {project_root.name}"

            # Persist successful connection
            self._save_metadata()

            logger.info(f"Project {path} initialized successfully")

        except asyncio.CancelledError:
            logger.info(f"Initialization cancelled for {path}")
            self._state.status = ProjectStatus.IDLE
            self._state.message = "Connection cancelled"
            self._state.server = None
            raise

        except Exception as e:
            logger.error(f"Failed to initialize project {path}: {e}", exc_info=True)
            self._state.status = ProjectStatus.ERROR
            self._state.error = str(e)
            self._state.message = f"Error: {e}"
            self._state.server = None

    def _create_and_init_server(
        self,
        path: str,
        auto_index: bool,
        force_reindex: bool,
        docs_enabled: bool | None,
    ) -> CodexMeshServer:
        """Blocking initialization function to be run in a thread."""
        # Load user config (which already applies default -> file -> env)
        config = self.load_user_config()

        bus = EventBus()
        context = AppContext(config=config, event_bus=bus)

        if docs_enabled is not None:
            config.docs.enabled = docs_enabled

        server = CodexMeshServer(path, context)

        # We perform internal initialization which includes building graph,
        # calculating hotspot, and indexing for vector search.
        # This can take time.
        self._update_progress_sync(30, "Initializing project components...")

        server.initialize(auto_index=auto_index, force_reindex=force_reindex)

        return server

    def _update_progress(self, progress: int, message: str) -> None:
        """Update progress safely."""
        self._state.progress = progress
        self._state.message = message

    def _update_progress_sync(self, progress: int, message: str) -> None:
        """Update progress from sync thread using call_soon_threadsafe for thread safety."""
        if self._loop and self._loop.is_running():
            self._loop.call_soon_threadsafe(self._update_progress, progress, message)
        else:
            self._state.progress = progress
            self._state.message = message
