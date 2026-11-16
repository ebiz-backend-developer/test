"""SQLite store with versioned migrations for the delivery-milestones app."""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path

SCHEMA_VERSION = 2


def connect(db_path: str | Path) -> sqlite3.Connection:
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def current_version(conn: sqlite3.Connection) -> int:
    conn.execute(
        "CREATE TABLE IF NOT EXISTS schema_migrations (version INTEGER PRIMARY KEY, applied_at TEXT NOT NULL)"
    )
    row = conn.execute("SELECT COALESCE(MAX(version), 0) AS v FROM schema_migrations").fetchone()
    return int(row["v"])


def migrate(conn: sqlite3.Connection) -> int:
    """Apply pending migrations. Returns the schema version."""
    version = current_version(conn)
    if version < 1:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS roles (
                name TEXT PRIMARY KEY,
                description TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS scopes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                vision TEXT NOT NULL,
                in_scope TEXT NOT NULL DEFAULT '[]',
                out_of_scope TEXT NOT NULL DEFAULT '[]',
                assumptions TEXT NOT NULL DEFAULT '[]',
                constraints_list TEXT NOT NULL DEFAULT '[]',
                updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS modules (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                description TEXT NOT NULL DEFAULT '',
                priority TEXT NOT NULL DEFAULT 'P2',
                mvp INTEGER NOT NULL DEFAULT 0,
                effort_points INTEGER NOT NULL DEFAULT 1,
                status TEXT NOT NULL DEFAULT 'backlog',
                depends_on TEXT NOT NULL DEFAULT '[]',
                updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS arch_decisions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category TEXT NOT NULL,
                option_name TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'proposed',
                rationale TEXT NOT NULL DEFAULT '',
                decided_by TEXT NOT NULL DEFAULT '',
                updated_at TEXT NOT NULL,
                UNIQUE (category, option_name)
            );
            CREATE TABLE IF NOT EXISTS milestones (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                phase TEXT NOT NULL,
                description TEXT NOT NULL DEFAULT '',
                start_date TEXT NOT NULL DEFAULT '',
                end_date TEXT NOT NULL DEFAULT '',
                status TEXT NOT NULL DEFAULT 'draft',
                owner_role TEXT NOT NULL DEFAULT 'product_owner',
                updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS risks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                milestone_id INTEGER REFERENCES milestones(id) ON DELETE SET NULL,
                title TEXT NOT NULL,
                likelihood TEXT NOT NULL DEFAULT 'medium',
                impact TEXT NOT NULL DEFAULT 'medium',
                mitigation TEXT NOT NULL DEFAULT '',
                status TEXT NOT NULL DEFAULT 'open',
                updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS acceptance_criteria (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                milestone_id INTEGER NOT NULL REFERENCES milestones(id) ON DELETE CASCADE,
                description TEXT NOT NULL,
                verification_method TEXT NOT NULL DEFAULT '',
                status TEXT NOT NULL DEFAULT 'pending',
                updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS approvals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                milestone_id INTEGER NOT NULL REFERENCES milestones(id) ON DELETE CASCADE,
                approver_role TEXT NOT NULL,
                decision TEXT NOT NULL,
                comment TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL
            );
            """
        )
        conn.execute(
            "INSERT INTO schema_migrations (version, applied_at) VALUES (1, datetime('now'))"
        )
        conn.commit()
        version = 1
    if version < 2:
        # v2: index hot lookup paths.
        conn.executescript(
            """
            CREATE INDEX IF NOT EXISTS idx_modules_priority ON modules(priority);
            CREATE INDEX IF NOT EXISTS idx_modules_mvp ON modules(mvp);
            CREATE INDEX IF NOT EXISTS idx_milestones_phase ON milestones(phase);
            CREATE INDEX IF NOT EXISTS idx_milestones_status ON milestones(status);
            CREATE INDEX IF NOT EXISTS idx_risks_milestone ON risks(milestone_id);
            CREATE INDEX IF NOT EXISTS idx_criteria_milestone ON acceptance_criteria(milestone_id);
            CREATE INDEX IF NOT EXISTS idx_approvals_milestone ON approvals(milestone_id);
            """
        )
        conn.execute(
            "INSERT INTO schema_migrations (version, applied_at) VALUES (2, datetime('now'))"
        )
        conn.commit()
        version = 2
    return version


def init_db(db_path: str | Path) -> sqlite3.Connection:
    conn = connect(db_path)
    migrate(conn)
    return conn


def dumps(value) -> str:
    return json.dumps(value or [])


def loads(raw: str | None):
    if not raw:
        return []
    try:
        return json.loads(raw)
    except (ValueError, TypeError):
        return []
