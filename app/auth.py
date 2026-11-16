"""API-key auth + role-based access control."""
from __future__ import annotations

import sqlite3
from typing import Annotated

from fastapi import Depends, Header, HTTPException, status

from .db import get_conn

ALL_ROLES = ("admin", "finance", "support", "auditor", "developer", "user")


class Actor:
    def __init__(self, row: sqlite3.Row):
        self.id = row["id"]
        self.email = row["email"]
        self.name = row["name"]
        self.role = row["role"]

    def dict(self) -> dict:
        return {"id": self.id, "email": self.email, "name": self.name, "role": self.role}


def _lookup(api_key: str) -> sqlite3.Row | None:
    conn = get_conn()
    try:
        return conn.execute(
            "SELECT * FROM users WHERE api_key = ? AND active = 1", (api_key,)
        ).fetchone()
    finally:
        conn.close()


def current_actor(
    x_api_key: Annotated[str | None, Header()] = None,
    authorization: Annotated[str | None, Header()] = None,
) -> Actor:
    key = (x_api_key or "").strip()
    if not key and authorization and authorization.lower().startswith("bearer "):
        key = authorization[7:].strip()
    if not key:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Missing API key")
    row = _lookup(key)
    if row is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid API key")
    return Actor(row)


def require_roles(*roles: str):
    def guard(actor: Annotated[Actor, Depends(current_actor)]) -> Actor:
        if actor.role not in roles and actor.role != "admin":
            raise HTTPException(status.HTTP_403_FORBIDDEN, f"Requires role: {'/'.join(roles)}")
        return actor

    return guard


def audit(actor: Actor | None, action: str, resource: str = "", detail: str = "") -> None:
    conn = get_conn()
    try:
        with conn:
            conn.execute(
                "INSERT INTO audit_log (actor_email, actor_role, action, resource, detail)"
                " VALUES (?, ?, ?, ?, ?)",
                (actor.email if actor else "", actor.role if actor else "", action, resource, detail),
            )
    finally:
        conn.close()
