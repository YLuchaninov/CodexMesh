"""
Review API Router.
"""

import os
import time
from typing import Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from ....llm.gemini_settings import GeminiSettings
from ....services.analysis_service import AnalysisService
from ....services.chat_service import ChatService
from ....services.fs_service import FileSystemService
from ...dependencies import (
    get_analysis_service,
    get_chat_service,
    get_fs_service,
    get_gemini_settings,
    get_intent_registry,
)

router = APIRouter(prefix="/reviewer", tags=["review"])


class ReviewRequest(BaseModel):
    message: str
    mode: Literal["quick", "standard", "deep", "autopilot"] = "standard"
    chat_id: str | None = None
    title: str | None = None
    include_history: bool = True


class GeminiConfigRequest(BaseModel):
    api_key: str | None = None
    model: str | None = None
    temperature: float | None = None


@router.get("/gemini")
async def get_gemini_config(settings: GeminiSettings = Depends(get_gemini_settings)):
    return settings.public_view()


@router.post("/gemini")
async def set_gemini_config(
    req: GeminiConfigRequest, settings: GeminiSettings = Depends(get_gemini_settings)
):
    settings.update(api_key=req.api_key, model=req.model, temperature=req.temperature)
    return settings.public_view()


@router.post("/gemini/test")
async def test_gemini(settings: GeminiSettings = Depends(get_gemini_settings)):
    if not settings.has_key():
        return {"ok": False, "error": "Gemini API key is not configured"}

    from ....llm.routing import LLMFactory, LLMProfile

    t0 = time.time()
    try:
        # Pass API key directly to LLMProfile (P1 fix: avoid mutating os.environ)
        profile = LLMProfile(
            name="test_config",
            model=settings.model,
            temperature=settings.temperature,
            provider="google",
            api_key=settings.api_key or os.environ.get("GOOGLE_API_KEY"),
            api_key_env="GOOGLE_API_KEY",
        )

        llm = LLMFactory.create(profile)
        if not llm:
            return {"ok": False, "error": "Failed to create LLM client"}

        from langchain_core.messages import HumanMessage

        resp = await llm.ainvoke([HumanMessage(content="ping")])
        dt = int((time.time() - t0) * 1000)
        return {
            "ok": True,
            "latency_ms": dt,
            "model": settings.model,
            "sample": (resp.content or "")[:80],
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}


@router.post("/ask")
async def ask_reviewer(
    req: ReviewRequest,
    analysis: AnalysisService = Depends(get_analysis_service),
    fs: FileSystemService = Depends(get_fs_service),
    settings: GeminiSettings = Depends(get_gemini_settings),
    cs: ChatService = Depends(get_chat_service),
    reg=Depends(get_intent_registry),
):
    try:
        from ....llm.reviewer import ReviewerAgent

        thread_id: str | None = req.chat_id
        if not thread_id:
            title = req.title or (
                req.message[:60] + "..." if len(req.message) > 60 else req.message
            )
            thread = cs.create_thread(title=title)
            thread_id = thread.id
        else:
            _t = cs.get_thread(thread_id)
            if not _t:
                thread = cs.create_thread(title="New Chat")
                thread_id = thread.id
            else:
                thread = _t

        assert thread_id is not None
        user_msg = cs.append_message(thread_id, role="user", content=req.message)

        history = []
        pinned_context = None
        summary = None

        if req.include_history:
            history_objs = cs.list_messages(thread_id, limit=100)
            history = [h.model_dump() for h in history_objs if h.id != user_msg.id]
            thread_full = cs.get_thread(thread_id)
            if thread_full:
                pinned_context = thread_full.pinned_context
                summary = thread_full.summary

        if req.mode == "autopilot":
            # Autopilot logic: Agent will self-configure using _resolve_profile
            # which aligns with ReviewerAgent capabilities (server context, settings, env, base)
            from ....llm.autopilot_agent import AutopilotAgent

            auto_agent = AutopilotAgent(analysis, reg, settings=settings, fs=fs)

            # Autopilot handling
            res_data = await auto_agent.ask(
                req.message, history=history, pinned_context=pinned_context
            )

            agent_msg = cs.append_message(
                thread_id,
                role="agent",
                content=res_data.get("answer", ""),
                evidence=res_data.get("evidence"),  # Structure trace/evidence
            )

            response = res_data
            response["chat_id"] = thread_id
            response["user_message_id"] = user_msg.id
            response["agent_message_id"] = agent_msg.id

            return response

        # Standard mode
        agent = ReviewerAgent(analysis, fs, settings=settings)
        response = await agent.ask(
            req.message,
            mode=req.mode,
            history=history,
            pinned_context=pinned_context,
            summary=summary,
        )

        agent_msg = cs.append_message(
            thread_id,
            role="agent",
            content=response.get("answer", ""),
            evidence=response.get("evidence"),
        )

        response["chat_id"] = thread_id
        response["user_message_id"] = user_msg.id
        response["agent_message_id"] = agent_msg.id

        return response
    except Exception as e:
        import traceback

        traceback.print_exc()
        from ....contracts.errors import ApiError

        raise ApiError(500, "ReviewError", str(e)) from e
