"""History, preferences and task log helpers (thread-safe)."""
import sqlite3
import threading

from memory.database import connect


class Memory:
    def __init__(self, conn: sqlite3.Connection | None = None) -> None:
        self.conn = conn or connect()
        self._lock = threading.Lock()

    def _write(self, sql: str, params: tuple = ()) -> None:
        with self._lock:
            self.conn.execute(sql, params)
            self.conn.commit()

    def _read(self, sql: str, params: tuple = ()) -> list:
        with self._lock:
            return self.conn.execute(sql, params).fetchall()

    # conversation history (user/assistant text only, never audio)
    def add_message(self, role: str, content: str) -> None:
        self._write("INSERT INTO messages(role, content) VALUES (?, ?)", (role, content))

    def recent_messages(self, limit: int = 6) -> list[dict]:
        rows = self._read("SELECT role, content FROM messages ORDER BY id DESC LIMIT ?", (limit,))
        return [{"role": r, "content": c} for r, c in reversed(rows)]

    # persistent preferences
    def set_pref(self, key: str, value: str) -> None:
        self._write("INSERT INTO preferences(key, value) VALUES (?, ?) "
                    "ON CONFLICT(key) DO UPDATE SET value=excluded.value, ts=CURRENT_TIMESTAMP", (key, value))

    def prefs(self) -> dict[str, str]:
        return dict(self._read("SELECT key, value FROM preferences ORDER BY key"))

    # task history: tool name + success, arguments truncated to limit private data
    def log_task(self, tool: str, args: dict, ok: bool) -> None:
        self._write("INSERT INTO task_log(tool, args, ok) VALUES (?, ?, ?)", (tool, str(args)[:200], int(ok)))

    def forget_all(self) -> None:
        for table in ("messages", "preferences", "task_log"):
            self._write(f"DELETE FROM {table}")
