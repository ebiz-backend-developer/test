"""SQLite access + versioned migration runner (stdlib sqlite3, no ORM)."""
from __future__ import annotations

import os
import sqlite3
from pathlib import Path

APP_ROOT = Path(__file__).resolve().parent
MIGRATIONS_DIR = APP_ROOT / "migrations"


def db_path() -> Path:
    return Path(os.environ.get("DATABASE_PATH", str(APP_ROOT.parent / "data" / "app.db")))


def connect() -> sqlite3.Connection:
    path = db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def applied_migrations(conn: sqlite3.Connection) -> set[str]:
    conn.execute(
        "CREATE TABLE IF NOT EXISTS schema_migrations (name TEXT PRIMARY KEY, applied_at TEXT NOT NULL)"
    )
    return {r[0] for r in conn.execute("SELECT name FROM schema_migrations")}


def migrate(conn: sqlite3.Connection | None = None) -> list[str]:
    """Apply pending *.sql migrations in filename order. Returns newly applied names."""
    own = conn is None
    conn = conn or connect()
    try:
        done = applied_migrations(conn)
        applied: list[str] = []
        for sql_file in sorted(MIGRATIONS_DIR.glob("*.sql")):
            if sql_file.name in done:
                continue
            with conn:
                conn.executescript(sql_file.read_text())
                conn.execute(
                    "INSERT INTO schema_migrations (name, applied_at) VALUES (?, datetime('now'))",
                    (sql_file.name,),
                )
            applied.append(sql_file.name)
        return applied
    finally:
        if own:
            conn.close()


def get_conn() -> sqlite3.Connection:
    conn = connect()
    migrate(conn)
    return conn
