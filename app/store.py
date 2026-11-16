"""SQLite store with file-based migrations. Stdlib only."""
from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

APP_ROOT = Path(__file__).resolve().parent.parent


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class Store:
    def __init__(self, path: str | Path = "data/school.db"):
        self.path = Path(path)
        if str(self.path) != ":memory:":
            self.path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(self.path), check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")
        self.migrate()

    def migrate(self, migrations_dir: str | Path | None = None) -> list[str]:
        directory = Path(migrations_dir) if migrations_dir else APP_ROOT / "migrations"
        applied = []
        with self.conn:
            self.conn.execute(
                "CREATE TABLE IF NOT EXISTS schema_migrations"
                " (version TEXT PRIMARY KEY, applied_at TEXT NOT NULL)"
            )
            done = {
                r[0]
                for r in self.conn.execute("SELECT version FROM schema_migrations")
            }
            for sql_file in sorted(directory.glob("*.sql")):
                if sql_file.stem in done:
                    continue
                self.conn.executescript(sql_file.read_text(encoding="utf-8"))
                self.conn.execute(
                    "INSERT INTO schema_migrations (version, applied_at) VALUES (?, ?)",
                    (sql_file.stem, utcnow()),
                )
                applied.append(sql_file.stem)
        return applied

    def query(self, sql: str, params: tuple = ()) -> list[dict]:
        return [dict(r) for r in self.conn.execute(sql, params)]

    def query_one(self, sql: str, params: tuple = ()) -> dict | None:
        row = self.conn.execute(sql, params).fetchone()
        return dict(row) if row is not None else None

    def execute(self, sql: str, params: tuple = ()) -> int:
        with self.conn:
            cur = self.conn.execute(sql, params)
            return cur.lastrowid or 0

    def close(self) -> None:
        self.conn.close()
