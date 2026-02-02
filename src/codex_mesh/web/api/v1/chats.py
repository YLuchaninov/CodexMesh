"""
Chats API Router.
"""

from typing import Literal

from fastapi import APIRouter, Depends

from ....contracts.chat import (
    ChatBulkMessagesRequest,
    ChatCloneRequest,
    ChatCreateRequest,
    ChatCreateResponse,
    ChatGetResponse,
    ChatListResponse,
    ChatMessageDeleteResponse,
    ChatMessagesListResponse,
    ChatPinnedContextSetRequest,
    ChatRenameRequest,
)
from ....services.chat_service import ChatService
from ...dependencies import get_chat_service

router = APIRouter(prefix="/chats", tags=["chat"])


@router.get("", response_model=ChatListResponse)
async def chats_list(
    scope: Literal["current", "all"] = "current",
    limit: int = 50,
    offset: int = 0,
    cs: ChatService = Depends(get_chat_service),
):
    """List chat threads."""
    threads = cs.list_threads(scope=scope, limit=limit, offset=offset)
    total = cs.count_threads(scope=scope)
    return ChatListResponse(threads=threads, total=total)


@router.post("", response_model=ChatCreateResponse)
async def chat_create(req: ChatCreateRequest, cs: ChatService = Depends(get_chat_service)):
    """Create a new chat thread."""
    thread = cs.create_thread(title=req.title, project_path=req.project_path)
    return ChatCreateResponse(thread=thread)


@router.get("/{chat_id}", response_model=ChatGetResponse)
async def chat_get(chat_id: str, cs: ChatService = Depends(get_chat_service)):
    """Get chat thread details."""
    thread = cs.get_thread(chat_id)
    if not thread:
        from ....contracts.errors import ApiError

        raise ApiError(404, "NotFound", f"Chat {chat_id} not found")
    return ChatGetResponse(thread=thread)


@router.patch("/{chat_id}", response_model=ChatGetResponse)
async def chat_rename_legacy(
    chat_id: str, req: ChatRenameRequest, cs: ChatService = Depends(get_chat_service)
):
    """Rename chat thread (Legacy PATCH)."""
    thread = cs.rename_thread(chat_id, req.title)
    if not thread:
        from ....contracts.errors import ApiError

        raise ApiError(404, "NotFound", f"Chat {chat_id} not found")
    return ChatGetResponse(thread=thread)


@router.post("/{chat_id}/rename", response_model=ChatGetResponse)
async def chat_rename(
    chat_id: str, req: ChatRenameRequest, cs: ChatService = Depends(get_chat_service)
):
    """Rename chat thread."""
    thread = cs.rename_thread(chat_id, req.title)
    return ChatGetResponse(thread=thread)


@router.post("/{chat_id}/clone", response_model=ChatCreateResponse)
async def chat_clone(
    chat_id: str, req: ChatCloneRequest, cs: ChatService = Depends(get_chat_service)
):
    """Clone chat thread."""
    thread = cs.clone_thread(chat_id, req.title)
    return ChatCreateResponse(thread=thread)


@router.delete("/{chat_id}")
async def chat_delete(
    chat_id: str, hard: bool = False, cs: ChatService = Depends(get_chat_service)
):
    """Delete chat thread."""
    cs.delete_thread(chat_id, hard=hard)
    return {"ok": True}


@router.get("/{chat_id}/messages", response_model=ChatMessagesListResponse)
async def chat_messages_list(
    chat_id: str, limit: int = 100, offset: int = 0, cs: ChatService = Depends(get_chat_service)
):
    """List messages in thread."""
    msgs = cs.list_messages(chat_id, limit=limit, offset=offset)
    return ChatMessagesListResponse(messages=msgs)


@router.post("/{chat_id}/messages/bulk")
async def chat_messages_bulk(
    chat_id: str, req: ChatBulkMessagesRequest, cs: ChatService = Depends(get_chat_service)
):
    msgs = cs.bulk_append_messages(chat_id, req.messages)
    return {"messages": msgs, "total": len(msgs)}


@router.delete("/{chat_id}/messages/{message_id}", response_model=ChatMessageDeleteResponse)
async def chat_message_delete(
    chat_id: str, message_id: str, cs: ChatService = Depends(get_chat_service)
):
    """Delete a message."""
    cs.delete_message(chat_id, message_id)
    return ChatMessageDeleteResponse(ok=True)


@router.post("/{chat_id}/pinned-context")
@router.put("/{chat_id}/pinned_context")
@router.put("/{chat_id}/pinned-context")
async def chat_pinned_context_set(
    chat_id: str, req: ChatPinnedContextSetRequest, cs: ChatService = Depends(get_chat_service)
):
    """Set pinned context for thread."""
    cs.set_pinned_context(chat_id, req.pinned_context)
    thread = cs.get_thread(chat_id)
    return {"thread": thread}
