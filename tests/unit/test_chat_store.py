import pytest

from codex_mesh.services.chat_service import ChatService
from codex_mesh.storage.chat_store import ChatStore


@pytest.fixture
def chat_store(tmp_path):
    return ChatStore(base_path=tmp_path)


@pytest.fixture
def chat_service(chat_store):
    from unittest.mock import MagicMock

    mock_ps = MagicMock()
    mock_ps.project_path = "/test"
    return ChatService(chat_store, mock_ps)


def test_chat_thread_lifecycle(chat_service):
    # 1. Create
    thread = chat_service.create_thread(title="Test Thread", project_path="/test")
    assert thread.title == "Test Thread"
    assert thread.project_path == "/test"

    # 2. Get
    fetched = chat_service.get_thread(thread.id)
    assert fetched.id == thread.id

    # 3. Rename
    updated = chat_service.rename_thread(thread.id, "New Title")
    assert updated.title == "New Title"

    # 4. List
    threads = chat_service.list_threads(scope="all")
    assert len(threads) >= 1
    assert any(t.id == thread.id for t in threads)

    # 5. Delete (soft)
    success = chat_service.delete_thread(thread.id, hard=False)
    assert success is True
    assert chat_service.get_thread(thread.id) is None

    # Verify count excludes deleted
    assert chat_service.count_threads(scope="all") == 0


def test_chat_message_ops(chat_service):
    thread = chat_service.create_thread(title="Msg Test")

    # 1. Append
    m1 = chat_service.append_message(thread.id, role="user", content="Hello")
    m2 = chat_service.append_message(
        thread.id,
        role="agent",
        content="Hi there",
        evidence=[{"kind": "test", "title": "T", "content": "C"}],
    )

    assert m1.role == "user"
    assert m2.role == "agent"
    assert len(m2.evidence) == 1

    # 2. List
    messages = chat_service.list_messages(thread.id)
    assert len(messages) == 2
    assert messages[0].content == "Hello"
    assert messages[1].content == "Hi there"

    # 3. Delete
    chat_service.delete_message(thread.id, m1.id)
    messages_after = chat_service.list_messages(thread.id)
    assert len(messages_after) == 1
    assert messages_after[0].id == m2.id


def test_pinned_context_and_summary(chat_service):
    thread = chat_service.create_thread(title="Context Test")

    chat_service.store.update_thread(
        thread.id, pinned_context="System rules", summary="A brief chat"
    )

    updated = chat_service.get_thread(thread.id)
    assert updated.pinned_context == "System rules"
    assert updated.summary == "A brief chat"


def test_clone_thread(chat_service):
    source = chat_service.create_thread(title="Source")
    chat_service.append_message(source.id, role="user", content="Clone me")
    chat_service.store.update_thread(source.id, pinned_context="Pinned")

    cloned = chat_service.clone_thread(source.id, "Clone")
    assert cloned.title == "Clone"
    assert cloned.pinned_context == "Pinned"

    messages = chat_service.list_messages(cloned.id)
    assert len(messages) == 1
    assert messages[0].content == "Clone me"
    assert messages[0].thread_id == cloned.id
