"""
SQLite storage for chat threads and messages.
"""

import json
import sqlite3
import time
import uuid
from pathlib import Path
from typing import Any, Literal

from ..contracts.chat import ChatMessage, ChatThread


class ChatStore:
    """Persistent storage for chats using SQLite."""

    def __init__(self, base_path: Path):
        self.db_path = base_path / "control_plane" / "chats.sqlite"
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        """Initialize the database schema."""
        with self._get_conn() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS chat_threads (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    project_path TEXT,
                    created_at INTEGER NOT NULL,
                    updated_at INTEGER NOT NULL,
                    pinned_context TEXT,
                    summary TEXT,
                    deleted_at INTEGER
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS chat_messages (
                    id TEXT PRIMARY KEY,
                    thread_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    ts INTEGER NOT NULL,
                    evidence_json TEXT,
                    deleted_at INTEGER,
                    FOREIGN KEY (thread_id) REFERENCES chat_threads(id) ON DELETE CASCADE
                )
            """)
            # Indices
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_threads_project_updated ON chat_threads(project_path, updated_at DESC)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_messages_thread_ts ON chat_messages(thread_id, ts ASC)"
            )
            conn.commit()

    # --- Thread Operations ---

    def create_thread(self, title: str, project_path: str | None = None) -> ChatThread:
        now = int(time.time() * 1000)
        thread = ChatThread(
            id=str(uuid.uuid4()),
            title=title,
            project_path=project_path,
            created_at=now,
            updated_at=now,
        )
        with self._get_conn() as conn:
            conn.execute(
                "INSERT INTO chat_threads (id, title, project_path, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
                (
                    thread.id,
                    thread.title,
                    thread.project_path,
                    thread.created_at,
                    thread.updated_at,
                ),
            )
            conn.commit()
        return thread

    def get_thread(self, thread_id: str) -> ChatThread | None:
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT * FROM chat_threads WHERE id = ? AND deleted_at IS NULL", (thread_id,)
            ).fetchone()
            if row:
                return ChatThread(**dict(row))
        return None

    def list_threads(
        self, project_path: str | None = None, limit: int = 50, offset: int = 0
    ) -> list[ChatThread]:
        query = "SELECT * FROM chat_threads WHERE deleted_at IS NULL"
        params: list[Any] = []
        if project_path:
            query += " AND (project_path = ? OR project_path IS NULL)"
            params.append(project_path)

        query += " ORDER BY updated_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        with self._get_conn() as conn:
            rows = conn.execute(query, tuple(params)).fetchall()
            return [ChatThread(**dict(row)) for row in rows]

    def count_threads(self, project_path: str | None = None) -> int:
        query = "SELECT COUNT(*) FROM chat_threads WHERE deleted_at IS NULL"
        params = []
        if project_path:
            query += " AND (project_path = ? OR project_path IS NULL)"
            params.append(project_path)

        with self._get_conn() as conn:
            return conn.execute(query, tuple(params)).fetchone()[0]

    def update_thread(self, thread_id: str, **kwargs) -> bool:
        if not kwargs:
            return False

        kwargs["updated_at"] = int(time.time() * 1000)
        keys = [f"{k} = ?" for k in kwargs]
        query = f"UPDATE chat_threads SET {', '.join(keys)} WHERE id = ?"
        params = list(kwargs.values()) + [thread_id]

        with self._get_conn() as conn:
            cursor = conn.execute(query, tuple(params))
            conn.commit()
            return cursor.rowcount > 0

    def delete_thread(self, thread_id: str, hard: bool = False) -> bool:
        with self._get_conn() as conn:
            if hard:
                cursor = conn.execute("DELETE FROM chat_threads WHERE id = ?", (thread_id,))
            else:
                now = int(time.time() * 1000)
                cursor = conn.execute(
                    "UPDATE chat_threads SET deleted_at = ? WHERE id = ?", (now, thread_id)
                )
            conn.commit()
            return cursor.rowcount > 0

    # --- Message Operations ---

    def append_message(
        self,
        thread_id: str,
        role: Literal["user", "agent", "system"],
        content: str,
        evidence: list[dict] | None = None,
    ) -> ChatMessage:
        now = int(time.time() * 1000)
        msg = ChatMessage(
            id=str(uuid.uuid4()),
            thread_id=thread_id,
            role=role,
            content=content,
            ts=now,
            evidence=evidence,
        )
        evidence_json = json.dumps(evidence) if evidence else None

        with self._get_conn() as conn:
            conn.execute(
                "INSERT INTO chat_messages (id, thread_id, role, content, ts, evidence_json) VALUES (?, ?, ?, ?, ?, ?)",
                (msg.id, msg.thread_id, msg.role, msg.content, msg.ts, evidence_json),
            )
            # Update thread's updated_at
            conn.execute("UPDATE chat_threads SET updated_at = ? WHERE id = ?", (now, thread_id))
            conn.commit()
        return msg

    def bulk_append_messages(
        self, thread_id: str, messages: list[dict[str, Any]]
    ) -> list[ChatMessage]:
        now = int(time.time() * 1000)
        results = []
        with self._get_conn() as conn:
            for m in messages:
                msg = ChatMessage(
                    id=str(uuid.uuid4()),
                    thread_id=thread_id,
                    role=m["role"],
                    content=m["content"],
                    ts=m.get("ts", now),
                    evidence=m.get("evidence"),
                )
                evidence_json = json.dumps(msg.evidence) if msg.evidence else None
                conn.execute(
                    "INSERT INTO chat_messages (id, thread_id, role, content, ts, evidence_json) VALUES (?, ?, ?, ?, ?, ?)",
                    (msg.id, msg.thread_id, msg.role, msg.content, msg.ts, evidence_json),
                )
                results.append(msg)

            # Update thread's updated_at to the latest message ts or now
            latest_ts = max([r.ts for r in results] + [now])
            conn.execute(
                "UPDATE chat_threads SET updated_at = ? WHERE id = ?", (latest_ts, thread_id)
            )
            conn.commit()
        return results

    def list_messages(
        self, thread_id: str, limit: int = 200, offset: int = 0, include_deleted: bool = False
    ) -> list[ChatMessage]:
        query = "SELECT * FROM chat_messages WHERE thread_id = ?"
        params: list[Any] = [thread_id]
        if not include_deleted:
            query += " AND deleted_at IS NULL"

        query += " ORDER BY ts ASC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        with self._get_conn() as conn:
            rows = conn.execute(query, tuple(params)).fetchall()
            results = []
            for row in rows:
                d = dict(row)
                ev = d.pop("evidence_json")
                if ev:
                    d["evidence"] = json.loads(ev)
                results.append(ChatMessage(**d))
            return results

    def count_messages(self, thread_id: str, include_deleted: bool = False) -> int:
        query = "SELECT COUNT(*) FROM chat_messages WHERE thread_id = ?"
        params = [thread_id]
        if not include_deleted:
            query += " AND deleted_at IS NULL"

        with self._get_conn() as conn:
            return conn.execute(query, tuple(params)).fetchone()[0]

    def delete_message(self, thread_id: str, message_id: str) -> bool:
        """Soft-delete a message."""
        now = int(time.time() * 1000)
        with self._get_conn() as conn:
            cursor = conn.execute(
                "UPDATE chat_messages SET deleted_at = ? WHERE id = ? AND thread_id = ?",
                (now, message_id, thread_id),
            )
            conn.commit()
            return cursor.rowcount > 0
