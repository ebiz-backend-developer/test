"""Runtime configuration: database location and server defaults."""
from __future__ import annotations

import os
from pathlib import Path

APP_NAME = "delivery-milestones"
DEFAULT_PORT = 8471
DEFAULT_DB_PATH = Path("data") / "delivery.db"


def db_path(explicit: str | None = None) -> Path:
    raw = explicit or os.environ.get("DELIVERY_DB") or str(DEFAULT_DB_PATH)
    path = Path(raw)
    if path.parent != Path(".") and str(path.parent):
        path.parent.mkdir(parents=True, exist_ok=True)
    return path
