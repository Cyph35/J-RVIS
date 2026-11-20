"""History, preferences and task log helpers."""
import sqlite3

from memory.database import connect


class Memory:
    def __init__(self, conn: sqlite3.Connection | None = None) -> None:
        self.conn = conn or connect()

    # conversation history (user/assistant text only, never audio)
    def add_message(self, role: str, content: str) -> None:
        self.conn.execute("INSERT INTO messages(role, content) VALUES (?, ?)", (role, content))
        self.conn.commit()

    def recent_messages(self, limit: int = 6) -> list[dict]:
        rows = self.conn.execute(
            "SELECT role, content FROM messages ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
        return [{"role": r, "content": c} for r, c in reversed(rows)]

    # persistent preferences
    def set_pref(self, key: str, value: str) -> None:
        self.conn.execute(
            "INSERT INTO preferences(key, value) VALUES (?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value, ts=CURRENT_TIMESTAMP", (key, value))
        self.conn.commit()

    def prefs(self) -> dict[str, str]:
        return dict(self.conn.execute("SELECT key, value FROM preferences ORDER BY key"))

    # task history: tool name + success, arguments truncated to limit private data
    def log_task(self, tool: str, args: dict, ok: bool) -> None:
        self.conn.execute("INSERT INTO task_log(tool, args, ok) VALUES (?, ?, ?)",
                          (tool, str(args)[:200], int(ok)))
        self.conn.commit()

    def forget_all(self) -> None:
        for table in ("messages", "preferences", "task_log"):
            self.conn.execute(f"DELETE FROM {table}")
        self.conn.commit()
