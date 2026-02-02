"""
Project Service.

Wraps ProjectManager to provide high-level project operations.
"""

from typing import Any

from ..api.manager import ProjectManager, ProjectStatus
from ..contracts.errors import ApiError


class ProjectService:
    def __init__(self, project_manager: ProjectManager):
        self.manager = project_manager

    @property
    def status(self) -> ProjectStatus:
        return self.manager.status

    @property
    def progress(self) -> int:
        return self.manager.progress

    @property
    def message(self) -> str:
        return self.manager.message

    @property
    def project_path(self) -> str | None:
        return self.manager.project_path

    async def connect(
        self,
        path: str,
        background: bool = True,
        *,
        auto_index: bool = True,
        force_reindex: bool = False,
        enable_watcher: bool = False,
    ) -> dict[str, Any]:
        """
        Connect to a project at the given path.

        Args:
            path: Absolute path to the project root.
            background: Whether to perform initialization in the background.
            auto_index: Whether to auto-index for semantic search.
            force_reindex: Force reindex even if index exists.
            enable_watcher: Enable live file watching (experimental).

        Returns:
            A dictionary containing the current status and progress.
        """
        await self.manager.connect(
            path,
            background=background,
            auto_index=auto_index,
            force_reindex=force_reindex,
            enable_watcher=enable_watcher,
        )

        return self.get_status_snapshot()

    def get_status_snapshot(self) -> dict[str, Any]:
        """Get current status as a dict."""
        p = self.manager.project_path
        return {
            "status": self.manager.status.value,
            "progress": self.manager.progress,
            "message": self.manager.message,
            "project_path": p,
            "project": p,  # Backward-compat, can be removed later
        }

    def ensure_ready(self) -> None:
        """
        Ensure the project is ready to serve requests.

        Raises:
            ApiError(503): If server is not ready (loading or error).
        """
        if not self.manager.server:
            if self.manager.status == ProjectStatus.LOADING:
                raise ApiError(
                    503,
                    "ServiceUnavailable",
                    "Server is busy",
                    details={"progress": self.manager.progress, "message": self.manager.message},
                )
            elif self.manager.status == ProjectStatus.ERROR:
                raise ApiError(500, "Internal", f"Project Error: {self.manager.message}")
            else:
                raise ApiError(409, "NotReady", "No project connected")

        if self.manager.status != ProjectStatus.READY:
            raise ApiError(
                503,
                "ServiceUnavailable",
                "Server is busy",
                details={"progress": self.manager.progress, "message": self.manager.message},
            )

    def get_stats(self) -> dict[str, Any]:
        """Get project statistics."""
        self.ensure_ready()
        if not self.manager.server:
            return {}
        return self.manager.server.get_stats()
