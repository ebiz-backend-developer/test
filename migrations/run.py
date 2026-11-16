"""Versioned schema migrations (schema-as-code, no external runner needed).

Usage: ``python -m migrations.run`` — applies pending migrations in order and
records them in the ``schema_version`` table.
"""

from __future__ import annotations

MIGRATIONS = ["0001_initial"]


def get_applied(engine) -> set[str]:
    from sqlalchemy import text

    with engine.begin() as conn:
        conn.execute(text(
            "CREATE TABLE IF NOT EXISTS schema_version "
            "(version TEXT PRIMARY KEY, applied_at TEXT NOT NULL)"
        ))
        rows = conn.execute(text("SELECT version FROM schema_version")).fetchall()
    return {row[0] for row in rows}


def apply_migration(engine, version: str) -> None:
    from sqlalchemy import text
    import datetime as dt

    if version == "0001_initial":
        from schoolms.database import Base
        import schoolms.models  # noqa: F401 — register models on Base.metadata

        Base.metadata.create_all(bind=engine)
    else:
        raise ValueError(f"Unknown migration: {version}")

    with engine.begin() as conn:
        conn.execute(
            text("INSERT OR IGNORE INTO schema_version (version, applied_at) VALUES (:v, :t)"),
            {"v": version, "t": dt.datetime.now(dt.timezone.utc).isoformat()},
        )


def run() -> list[str]:
    from schoolms.database import engine

    applied_before = get_applied(engine)
    applied_now: list[str] = []
    for version in MIGRATIONS:
        if version not in applied_before:
            apply_migration(engine, version)
            applied_now.append(version)
    return applied_now


if __name__ == "__main__":
    done = run()
    print(f"Applied migrations: {done or 'none pending'}")
