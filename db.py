"""SQLite database connection + upsert helpers.

The schema lives at ``data/schema.sql``. The DB file is at
``data/critics_impact.db`` (committed). See ``config.py`` for paths.
"""
from __future__ import annotations

import sqlite3
import re
from pathlib import Path
from typing import Optional

from config import DB_PATH, ROOT

_SCHEMA_PATH = ROOT / "data" / "schema.sql"


def get_connection(db_path: Path = DB_PATH) -> sqlite3.Connection:
    """Return a connection with row_factory and FK enforcement."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def initialize_db(db_path: Path = DB_PATH) -> None:
    """Create all tables if they don't exist."""
    with get_connection(db_path) as conn:
        conn.executescript(_SCHEMA_PATH.read_text())
    print(f"Database initialized at {db_path}")


def upsert_publication(conn: sqlite3.Connection, name: str) -> int:
    """Insert or return existing publication_id."""
    norm = _norm(name)
    conn.execute(
        "INSERT OR IGNORE INTO publications(name, normalized_name) VALUES(?,?)",
        (name.strip(), norm),
    )
    row = conn.execute(
        "SELECT publication_id FROM publications WHERE normalized_name=?", (norm,)
    ).fetchone()
    return row["publication_id"]


def upsert_critic(
    conn: sqlite3.Connection, name: str, publication_id: Optional[int] = None
) -> int:
    """Insert or return existing critic_id."""
    norm = _norm(name)
    conn.execute(
        "INSERT OR IGNORE INTO critics(name, normalized_name, primary_publication_id) VALUES(?,?,?)",
        (name.strip(), norm, publication_id),
    )
    row = conn.execute(
        "SELECT critic_id FROM critics "
        "WHERE normalized_name=? "
        "  AND (primary_publication_id=? OR primary_publication_id IS NULL)",
        (norm, publication_id),
    ).fetchone()
    return row["critic_id"]


def _norm(s: str) -> str:
    """Lowercase, strip, collapse whitespace."""
    return re.sub(r"\s+", " ", s.lower().strip())
