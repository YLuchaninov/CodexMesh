"""
Chat Service.

Provides high-level operations for managing chat threads and messages.
"""

from typing import Any, Literal

from ..contracts.chat import ChatMessage, ChatThread
from ..storage.chat_store import ChatStore
from .project_service import ProjectService


class ChatService:
    """Service layer for chat-related operations."""

    def __init__(self, chat_store: ChatStore, project_service: ProjectService):
        self.store = chat_store
        self.project_service = project_service

    def list_threads(
        self, scope: Literal["current", "all"] = "current", limit: int = 50, offset: int = 0
    ) -> list[ChatThread]:
        project_path = self.project_service.project_path if scope == "current" else None
        return self.store.list_threads(project_path=project_path, limit=limit, offset=offset)

    def count_threads(self, scope: Literal["current", "all"] = "current") -> int:
        project_path = self.project_service.project_path if scope == "current" else None
        return self.store.count_threads(project_path=project_path)

    def create_thread(
        self, title: str | None = None, project_path: str | None = None
    ) -> ChatThread:
        if not title:
            title = "New chat"
        if not project_path:
            project_path = self.project_service.project_path
        return self.store.create_thread(title=title, project_path=project_path)

    def get_thread(self, thread_id: str) -> ChatThread | None:
        return self.store.get_thread(thread_id)

    def rename_thread(self, thread_id: str, title: str) -> ChatThread | None:
        if self.store.update_thread(thread_id, title=title):
            return self.store.get_thread(thread_id)
        return None

    def delete_thread(self, thread_id: str, hard: bool = False) -> bool:
        return self.store.delete_thread(thread_id, hard=hard)

    def clone_thread(self, thread_id: str, title: str | None = None) -> ChatThread | None:
        source = self.get_thread(thread_id)
        if not source:
            return None

        new_title = title or f"{source.title} (copy)"
        new_thread = self.create_thread(title=new_title, project_path=source.project_path)

        # Copy pinned context and summary
        self.store.update_thread(
            new_thread.id, pinned_context=source.pinned_context, summary=source.summary
        )

        # Copy messages
        messages = self.list_messages(thread_id, limit=1000)  # Load a lot for cloning
        for msg in messages:
            self.store.append_message(
                new_thread.id, role=msg.role, content=msg.content, evidence=msg.evidence
            )

        return self.get_thread(new_thread.id)

    def list_messages(
        self, thread_id: str, limit: int = 200, offset: int = 0, include_deleted: bool = False
    ) -> list[ChatMessage]:
        return self.store.list_messages(
            thread_id, limit=limit, offset=offset, include_deleted=include_deleted
        )

    def count_messages(self, thread_id: str, include_deleted: bool = False) -> int:
        return self.store.count_messages(thread_id, include_deleted=include_deleted)

    def delete_message(self, thread_id: str, message_id: str) -> bool:
        return self.store.delete_message(thread_id, message_id)

    def append_message(
        self,
        thread_id: str,
        role: Literal["user", "agent", "system"],
        content: str,
        evidence: list[dict] | None = None,
    ) -> ChatMessage:
        return self.store.append_message(thread_id, role, content, evidence=evidence)

    def bulk_append_messages(
        self, thread_id: str, messages: list[dict[str, Any]]
    ) -> list[ChatMessage]:
        return self.store.bulk_append_messages(thread_id, messages)

    def set_pinned_context(self, thread_id: str, pinned_context: str | None) -> bool:
        return self.store.update_thread(thread_id, pinned_context=pinned_context)

    def set_summary(self, thread_id: str, summary: str | None) -> bool:
        return self.store.update_thread(thread_id, summary=summary)
