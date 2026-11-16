"""SQLite store with versioned migrations."""
from __future__ import annotations

import sqlite3
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
MIGRATIONS_DIR = REPO_ROOT / "migrations"


class Store:
    def __init__(self, path: str | Path = ":memory:") -> None:
        self.path = str(path)
        # Shared across HTTP worker threads; app.server.Handler.lock serializes use.
        self.conn = sqlite3.connect(self.path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")
        self.migrate()

    def migrate(self) -> list[str]:
        applied = [r[0] for r in self.conn.execute(
            "SELECT version FROM schema_migrations"
        )] if self._has_migrations_table() else []
        done: list[str] = []
        for sql_file in sorted(MIGRATIONS_DIR.glob("*.sql")):
            version = sql_file.stem
            if version in applied:
                continue
            self.conn.executescript(sql_file.read_text(encoding="utf-8"))
            self.conn.execute(
                "INSERT OR IGNORE INTO schema_migrations (version) VALUES (?)", (version,))
            self.conn.commit()
            done.append(version)
        return done

    def _has_migrations_table(self) -> bool:
        row = self.conn.execute(
            "SELECT name FROM sqlite_master WHERE name='schema_migrations'").fetchone()
        return row is not None

    def close(self) -> None:
        self.conn.close()
