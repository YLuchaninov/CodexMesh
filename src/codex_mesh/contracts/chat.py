"""
Chat contracts for storage and Web API.
"""

from typing import Any, Literal

from pydantic import BaseModel, Field

# --- Entities ---


class ChatThread(BaseModel):
    """A single conversation thread."""

    id: str = Field(..., description="Unique thread ID (UUID)")
    title: str = Field(..., description="Thread title")
    project_path: str | None = Field(None, description="Related project path")
    created_at: int = Field(..., description="Creation timestamp (epoch ms)")
    updated_at: int = Field(..., description="Last update timestamp (epoch ms)")
    pinned_context: str | None = Field(None, description="Always-included instructions for LLM")
    summary: str | None = Field(None, description="Conversation summary")
    deleted_at: int | None = Field(None, description="Soft-delete timestamp")


class ChatMessage(BaseModel):
    """A message within a thread."""

    id: str = Field(..., description="Unique message ID")
    thread_id: str = Field(..., description="Parent thread ID")
    role: Literal["user", "agent", "system"] = Field(..., description="Message role")
    content: str = Field(..., description="Message content")
    ts: int = Field(..., description="Timestamp (epoch ms)")
    evidence: list[dict[str, Any]] | None = Field(None, description="Optional grounding evidence")
    deleted_at: int | None = Field(None, description="Soft-delete timestamp")


# --- Request/Response Models ---


class ChatListRequest(BaseModel):
    """Request to list chat threads."""

    scope: Literal["current", "all"] = Field(
        "current", description="Filter by current project or show all"
    )
    limit: int = Field(50, ge=1, le=200)
    offset: int = Field(0, ge=0)


class ChatListResponse(BaseModel):
    """Response containing a list of chat threads."""

    threads: list[ChatThread]
    total: int = 0


class ChatCreateRequest(BaseModel):
    """Request to create a new chat thread."""

    title: str | None = Field(None, description="Initial title")
    project_path: str | None = Field(None, description="Project path override")


class ChatCreateResponse(BaseModel):
    """Response after creating a chat thread."""

    thread: ChatThread


class ChatRenameRequest(BaseModel):
    """Request to rename a chat thread."""

    title: str = Field(..., description="New title")


class ChatCloneRequest(BaseModel):
    """Request to clone a chat thread."""

    title: str | None = Field(None, description="Title for the clone")


class ChatGetResponse(BaseModel):
    """Response containing a single chat thread."""

    thread: ChatThread


class ChatDeleteRequest(BaseModel):
    """Request to delete a chat thread."""

    hard: bool = Field(False, description="Whether to perform a hard delete")


class ChatMessagesListRequest(BaseModel):
    """Request to list messages in a thread."""

    limit: int = Field(200, ge=1, le=1000)
    offset: int = Field(0, ge=0)
    include_deleted: bool = Field(False, description="Whether to include soft-deleted messages")


class ChatMessagesListResponse(BaseModel):
    """Response containing messages in a thread."""

    messages: list[ChatMessage]
    total: int = 0


class ChatMessageDeleteResponse(BaseModel):
    """Response after deleting a message."""

    ok: bool


class ChatPinnedContextSetRequest(BaseModel):
    """Request to update pinned context."""

    pinned_context: str | None = Field(None, description="New pinned context")


class ChatSummarySetRequest(BaseModel):
    """Request to update thread summary."""

    summary: str | None = Field(None, description="New summary")


class ChatBulkMessagesRequest(BaseModel):
    """Request to append multiple messages (useful for migrations)."""

    messages: list[dict[str, Any]] = Field(
        ..., description="List of messages to append (role, content, evidence?)"
    )
