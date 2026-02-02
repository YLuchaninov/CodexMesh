"""
Integration tests for Web API v1 chats.
"""

from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from codex_mesh.storage.chat_store import ChatStore
from codex_mesh.web.app import app

client = TestClient(app)


@pytest.fixture
def clean_chat_store(tmp_path):
    """Create a fresh ChatStore for each test."""
    store = ChatStore(base_path=tmp_path)
    # Inject into app state
    app.state.chat_store = store
    return store


@pytest.fixture
def mock_pm():
    """Mock ProjectManager."""
    pm = MagicMock()
    pm.project_path = "/test/project"
    app.state.project_manager = pm
    return pm


def test_chat_lifecycle(clean_chat_store, mock_pm):
    # 1. List - empty
    resp = client.get("/api/v1/chats")
    assert resp.status_code == 200
    assert resp.json()["total"] == 0
    assert resp.json()["threads"] == []

    # 2. Create
    resp = client.post("/api/v1/chats", json={"title": "My Chat"})
    assert resp.status_code == 200
    thread = resp.json()["thread"]
    assert thread["title"] == "My Chat"
    thread_id = thread["id"]

    # 3. Get
    resp = client.get(f"/api/v1/chats/{thread_id}")
    assert resp.status_code == 200
    assert resp.json()["thread"]["id"] == thread_id

    # 4. Rename
    resp = client.patch(f"/api/v1/chats/{thread_id}", json={"title": "Renamed Chat"})
    assert resp.status_code == 200
    assert resp.json()["thread"]["title"] == "Renamed Chat"

    # 5. List - found
    resp = client.get("/api/v1/chats")
    assert resp.json()["total"] == 1
    assert resp.json()["threads"][0]["title"] == "Renamed Chat"

    # 6. Delete
    resp = client.delete(f"/api/v1/chats/{thread_id}")
    assert resp.status_code == 200

    # 7. List - empty (soft deleted)
    resp = client.get("/api/v1/chats")
    assert resp.json()["total"] == 0


def test_chat_messages(clean_chat_store, mock_pm):
    # Create thread
    t_resp = client.post("/api/v1/chats", json={"title": "Msg Test"}).json()
    thread_id = t_resp["thread"]["id"]

    # 1. Bulk append (migration scenario)
    msgs = [{"role": "user", "content": "Hello"}, {"role": "agent", "content": "Hi"}]
    resp = client.post(f"/api/v1/chats/{thread_id}/messages/bulk", json={"messages": msgs})
    assert resp.status_code == 200
    assert resp.json()["total"] == 2

    mid = resp.json()["messages"][0]["id"]

    # 2. List
    resp = client.get(f"/api/v1/chats/{thread_id}/messages")
    assert len(resp.json()["messages"]) == 2

    # 3. Delete message
    resp = client.delete(f"/api/v1/chats/{thread_id}/messages/{mid}")
    assert resp.status_code == 200

    # 4. List again
    resp = client.get(f"/api/v1/chats/{thread_id}/messages")
    assert len(resp.json()["messages"]) == 1


def test_chat_clone(clean_chat_store, mock_pm):
    # Setup source
    t1 = client.post("/api/v1/chats", json={"title": "Source"}).json()["thread"]
    client.post(
        f"/api/v1/chats/{t1['id']}/messages/bulk",
        json={"messages": [{"role": "user", "content": "A"}]},
    )

    # Clone
    resp = client.post(f"/api/v1/chats/{t1['id']}/clone", json={"title": "Cloned"})
    assert resp.status_code == 200
    t2 = resp.json()["thread"]
    assert t2["title"] == "Cloned"

    # Verify messages copied
    m_resp = client.get(f"/api/v1/chats/{t2['id']}/messages")
    assert len(m_resp.json()["messages"]) == 1
    assert m_resp.json()["messages"][0]["content"] == "A"


def test_pinned_context(clean_chat_store, mock_pm):
    t = client.post("/api/v1/chats", json={"title": "C"}).json()["thread"]

    resp = client.put(
        f"/api/v1/chats/{t['id']}/pinned_context", json={"pinned_context": "ADMIN MODE"}
    )
    assert resp.status_code == 200
    assert resp.json()["thread"]["pinned_context"] == "ADMIN MODE"


def test_chat_scope_filtering(clean_chat_store, mock_pm):
    # Create chat in current project
    t1 = clean_chat_store.create_thread(title="P1", project_path="/test/project")
    # Create chat in other project
    t2 = clean_chat_store.create_thread(title="P2", project_path="/other/project")

    # 1. Scope = current (default)
    # mock_pm.project_path is /test/project
    resp = client.get("/api/v1/chats?scope=current")
    threads = resp.json()["threads"]
    ids = [t["id"] for t in threads]
    assert t1.id in ids
    assert t2.id not in ids

    # 2. Scope = all
    resp = client.get("/api/v1/chats?scope=all")
    threads = resp.json()["threads"]
    ids = [t["id"] for t in threads]
    assert t1.id in ids
    assert t2.id in ids


def test_chat_hard_delete(clean_chat_store, mock_pm):
    t = clean_chat_store.create_thread("To delete")
    tid = t.id

    # 1. Soft delete
    client.delete(f"/api/v1/chats/{tid}?hard=false")
    # Should be gone from list
    # The API returns 404 for soft-deleted threads too unless we peek in DB
    assert client.get(f"/api/v1/chats/{tid}").status_code == 404

    # But exists in DB marked deleted
    with clean_chat_store._get_conn() as conn:
        raw = conn.execute("SELECT * FROM chat_threads WHERE id=?", (tid,)).fetchone()
        assert raw["deleted_at"] is not None

    # 2. Hard delete
    client.delete(f"/api/v1/chats/{tid}?hard=true")
    # Should be gone from DB
    with clean_chat_store._get_conn() as conn:
        raw = conn.execute("SELECT * FROM chat_threads WHERE id=?", (tid,)).fetchone()
        assert raw is None
