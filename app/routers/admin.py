"""Admin + ops endpoints: users, audit log, service status."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from ..auth import Actor, current_actor, require_roles
from ..db import get_conn
from ..services import notify, payments

router = APIRouter(tags=["admin"])


@router.get("/me")
def me(actor: Annotated[Actor, Depends(current_actor)]):
    return actor.dict()


@router.get("/status")
def status():
    return {
        "service": "integrations-reports",
        "version": "0.1.0",
        "payment_providers": payments.provider_names(),
        "notification_gateways": sorted(notify.GATEWAYS),
        "report_types": ["transactions", "refunds", "notifications", "access_audit", "revenue_daily"],
    }


@router.get("/admin/users")
def users(actor: Annotated[Actor, Depends(require_roles("admin"))]):
    conn = get_conn()
    try:
        rows = conn.execute(
            "SELECT id, email, name, role, active, created_at FROM users ORDER BY id"
        ).fetchall()
        return {"users": [dict(r) for r in rows]}
    finally:
        conn.close()


@router.get("/admin/audit")
def audit_log(limit: int = 100, actor: Annotated[Actor, Depends(require_roles("admin", "auditor"))] = None):
    conn = get_conn()
    try:
        rows = conn.execute(
            "SELECT * FROM audit_log ORDER BY id DESC LIMIT ?", (min(limit, 500),)
        ).fetchall()
        return {"entries": [dict(r) for r in rows]}
    finally:
        conn.close()
