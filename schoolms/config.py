"""Application configuration (c3: tech stack selection lives in docs/ARCHITECTURE.md)."""

from __future__ import annotations

import os
from functools import lru_cache


class Settings:
    app_name: str = "SchoolMS"
    api_prefix: str = "/api/v1"
    database_url: str = os.environ.get("SCHOOLMS_DATABASE_URL", "sqlite:///./schoolms.db")
    jwt_secret: str = os.environ.get("SCHOOLMS_JWT_SECRET", "dev-secret-change-me")
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = int(os.environ.get("SCHOOLMS_JWT_EXPIRE_MINUTES", "720"))


@lru_cache
def get_settings() -> Settings:
    return Settings()
