"""SQLite schema initialization and database access for Amber.

The database is an index/cache over the filesystem. It can be rebuilt
from the on-disk log structure at any time.
"""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Generator

_SCHEMA = """\
CREATE TABLE IF NOT EXISTS entries (
    id INTEGER PRIMARY KEY,
    date TEXT NOT NULL UNIQUE,
    video_path TEXT NOT NULL,
    transcript TEXT,
    duration_seconds REAL,
    file_size_bytes INTEGER,
    whisper_model TEXT,
    transcription_status TEXT NOT NULL DEFAULT 'pending',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS summaries (
    id INTEGER PRIMARY KEY,
    period_type TEXT NOT NULL,
    period_key TEXT NOT NULL,
    content TEXT,
    source_entry_ids TEXT,
    model_used TEXT,
    created_at TEXT NOT NULL,
    UNIQUE(period_type, period_key)
);
"""

# FTS5 virtual tables don't support IF NOT EXISTS, so we create them
# only when the table is missing.
_FTS_SCHEMA = """\
CREATE VIRTUAL TABLE transcripts_fts USING fts5(
    date,
    content
);
"""


def _fts_table_exists(conn: sqlite3.Connection) -> bool:
    row = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='transcripts_fts'"
    ).fetchone()
    return row is not None


def init_db(db_path: Path) -> None:
    """Initialize the database schema.

    Safe to call on every startup -- uses IF NOT EXISTS for regular tables
    and checks for the FTS table before creating it.
    """
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    try:
        conn.executescript(_SCHEMA)
        if not _fts_table_exists(conn):
            conn.executescript(_FTS_SCHEMA)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.commit()
    finally:
        conn.close()


@contextmanager
def get_db(db_path: Path) -> Generator[sqlite3.Connection, None, None]:
    """Context manager that yields a SQLite connection with row factory set.

    Usage:
        with get_db(db_path) as conn:
            conn.execute("SELECT ...")
    """
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
