"""SQLite store: connections plus file-based migrations."""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

MIGRATIONS_DIR = Path(__file__).with_name("migrations")


def dumps(value: list[str]) -> str:
    return json.dumps(value)


def loads(raw: str | None) -> list[str]:
    if not raw:
        return []
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return []
    return data if isinstance(data, list) else []


#: Shared-cache URI so every thread of the dev server sees one :memory: db.
SHARED_MEMORY_URI = "file:delivery-memdb?mode=memory&cache=shared"


def connect(path: str = ":memory:", uri: bool = False) -> sqlite3.Connection:
    """Private connection per call; tests get isolation, the server opts
    into SHARED_MEMORY_URI explicitly (see delivery.server)."""
    conn = sqlite3.connect(path, uri=uri, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA busy_timeout = 5000")
    return conn


def server_connect(db_path: str) -> sqlite3.Connection:
    """Connection for server threads: shared-cache when in-memory."""
    if db_path == ":memory:":
        return connect(SHARED_MEMORY_URI, uri=True)
    return connect(db_path)


def migrate(conn: sqlite3.Connection) -> list[str]:
    """Apply pending migrations in filename order; return applied versions."""
    conn.execute(
        "CREATE TABLE IF NOT EXISTS schema_migrations"
        " (version TEXT PRIMARY KEY, applied_at TEXT NOT NULL)"
    )
    applied = {
        row["version"] for row in conn.execute("SELECT version FROM schema_migrations")
    }
    done: list[str] = []
    for path in sorted(MIGRATIONS_DIR.glob("*.sql")):
        version = path.stem
        if version in applied:
            continue
        conn.executescript(path.read_text())
        conn.execute(
            "INSERT INTO schema_migrations (version, applied_at) VALUES (?, ?)",
            (version, datetime.now(timezone.utc).isoformat()),
        )
        conn.commit()
        done.append(version)
    return done


def applied_versions(conn: sqlite3.Connection) -> list[str]:
    migrate(conn)  # ensure the tracking table exists
    rows = conn.execute("SELECT version FROM schema_migrations ORDER BY version")
    return [row["version"] for row in rows]
