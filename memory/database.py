"""SQLite connection and schema. The database file lives in data/ (git-ignored)."""
import sqlite3
from pathlib import Path

import config

SCHEMA = """
CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY, ts TEXT DEFAULT CURRENT_TIMESTAMP,
    role TEXT NOT NULL, content TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS preferences (
    key TEXT PRIMARY KEY, value TEXT NOT NULL, ts TEXT DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS task_log (
    id INTEGER PRIMARY KEY, ts TEXT DEFAULT CURRENT_TIMESTAMP,
    tool TEXT NOT NULL, args TEXT, ok INTEGER NOT NULL);
"""


def connect(path: str | Path = config.DB_PATH) -> sqlite3.Connection:
    if str(path) != ":memory:":
        Path(path).parent.mkdir(parents=True, exist_ok=True)
    # The GUI uses the assistant from several threads; Memory serializes access with a lock.
    conn = sqlite3.connect(path, check_same_thread=False)
    conn.executescript(SCHEMA)
    return conn
