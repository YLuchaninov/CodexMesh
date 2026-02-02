"""
Status contracts.

Models for project status and connection.
"""

from typing import Literal

from pydantic import BaseModel, Field

ProjectStatus = Literal["IDLE", "LOADING", "READY", "ERROR"]


class StatusSnapshot(BaseModel):
    """Current project status snapshot."""

    status: ProjectStatus = Field(..., description="Current project status")
    progress: float = Field(0.0, ge=0.0, le=100.0, description="Progress percentage 0-100")
    message: str = Field("", description="Status message")
    project_path: str | None = Field(None, description="Connected project path")


class ConnectOptions(BaseModel):
    """Options for project connection."""

    auto_index: bool = Field(True, description="Whether to auto-index for semantic search")
    force_reindex: bool = Field(False, description="Force reindex even if index exists")
    watch: bool = Field(False, description="Enable live file watching (experimental)")
    docs_enabled: bool | None = Field(
        None, description="Enable docs extraction and indexing (overrides config)"
    )


class ConnectRequest(BaseModel):
    """Request to connect to a project."""

    project_path: str = Field(..., description="Absolute path to project root")
    options: ConnectOptions = Field(default_factory=lambda: ConnectOptions())


class ConnectResponse(BaseModel):
    """Response after connect request."""

    ok: bool = Field(True)
    status: StatusSnapshot
