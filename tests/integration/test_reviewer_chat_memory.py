"""
Integration tests for Reviewer chat memory and history handling.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from codex_mesh.storage.chat_store import ChatStore
from codex_mesh.web.app import app

client = TestClient(app)


@pytest.fixture
def clean_chat_store(tmp_path):
    store = ChatStore(base_path=tmp_path)
    app.state.chat_store = store
    return store


@pytest.fixture
def mock_pm():
    pm = MagicMock()
    pm.project_path = "/test/project"

    # Add status for ProjectService checks
    from codex_mesh.api.manager import ProjectStatus

    pm.status = ProjectStatus.READY
    pm.progress = 100
    pm.server = MagicMock()

    app.state.project_manager = pm
    return pm


@pytest.fixture
def mock_gemini():
    settings = MagicMock()
    settings.has_key.return_value = True
    settings.model = "test-model"
    settings.temperature = 0.7
    settings.api_key = "fake-key"
    app.state.gemini_settings = settings
    return settings


# Patch the agent to avoid actual LLM calls
@pytest.fixture
def mock_reviewer_agent():
    with patch("codex_mesh.llm.reviewer.ReviewerAgent") as MockAgent:
        instance = MockAgent.return_value
        # Mock ask to return a fixed response
        instance.ask = AsyncMock(
            return_value={
                "answer": "I remember",
                "evidence": [],
                "checked_items": ["memory check"],
                "intent": "chat",
            }
        )
        yield instance


def test_reviewer_creates_chat_automatically(
    clean_chat_store, mock_pm, mock_gemini, mock_reviewer_agent
):
    # 1. Send request without chat_id
    payload = {"message": "Hello new chat", "mode": "standard"}

    with (
        patch("codex_mesh.web.routes.AnalysisService"),
        patch("codex_mesh.web.routes.FileSystemService"),
    ):
        resp = client.post("/api/reviewer/ask", json=payload)
        assert resp.status_code == 200
        data = resp.json()

        # Should return new chat_id
        assert "chat_id" in data
        chat_id = data["chat_id"]
        assert data["answer"] == "I remember"

        # Verify chat was created in store
        thread = clean_chat_store.get_thread(chat_id)
        assert thread is not None
        assert thread.title == "Hello new chat" or thread.title.startswith("Hello new chat")

        # Verify messages persisted
        msgs = clean_chat_store.list_messages(chat_id)
        assert len(msgs) == 2  # User + Agent
        assert msgs[0].role == "user"
        assert msgs[0].content == "Hello new chat"
        assert msgs[1].role == "agent"
        assert msgs[1].content == "I remember"


def test_reviewer_reuses_chat(clean_chat_store, mock_pm, mock_gemini, mock_reviewer_agent):
    # Create thread manually
    t = clean_chat_store.create_thread("Existing")

    payload = {"message": "Follow up", "chat_id": t.id}

    with (
        patch("codex_mesh.web.routes.AnalysisService"),
        patch("codex_mesh.web.routes.FileSystemService"),
    ):
        resp = client.post("/api/reviewer/ask", json=payload)
        assert resp.status_code == 200
        data = resp.json()

        assert data["chat_id"] == t.id

        # Verify history was passed to agent (requires introspection of mock call)
        # The route calls agent.ask(..., history=...)
        # We need to verify that call.

        call_args = mock_reviewer_agent.ask.call_args
        assert call_args is not None
        _, kwargs = call_args

        # Check history passed to agent
        # We expect empty history because we just created the thread (no msg)
        # Let's add one before

    # Retry with history
    clean_chat_store.append_message(t.id, "user", "Old msg")

    payload["message"] = "Follow up 2"

    with (
        patch("codex_mesh.web.routes.AnalysisService"),
        patch("codex_mesh.web.routes.FileSystemService"),
    ):
        client.post("/api/reviewer/ask", json=payload)

        # Now verify agent.ask called with history
        call_args = mock_reviewer_agent.ask.call_args
        _, kwargs = call_args
        history = kwargs.get("history", [])
        assert len(history) > 0
        # Should contain "Old msg" and previous "Follow up" cycle messages
        # Depending on how the test runs, at least "Old msg" should be there.
