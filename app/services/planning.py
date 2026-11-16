"""Planning data access: scope, roles, modules, tech decisions, milestones."""
from __future__ import annotations

import json

from ..db import get_conn


def list_scope() -> list[dict]:
    conn = get_conn()
    try:
        return [dict(r) for r in conn.execute("SELECT * FROM scope_items ORDER BY area, id")]
    finally:
        conn.close()


def list_roles() -> list[dict]:
    conn = get_conn()
    try:
        out = []
        for r in conn.execute("SELECT * FROM role_definitions ORDER BY id"):
            d = dict(r)
            d["permissions"] = json.loads(d.pop("permissions_json") or "[]")
            out.append(d)
        return out
    finally:
        conn.close()


def list_modules(mvp_only: bool = False) -> list[dict]:
    conn = get_conn()
    try:
        q = "SELECT * FROM modules"
        if mvp_only:
            q += " WHERE mvp = 1"
        q += " ORDER BY CASE priority WHEN 'P0' THEN 0 WHEN 'P1' THEN 1 ELSE 2 END, id"
        return [dict(r) for r in conn.execute(q)]
    finally:
        conn.close()


def update_module(name: str, status: str | None, priority: str | None) -> dict | None:
    conn = get_conn()
    try:
        with conn:
            if status:
                conn.execute("UPDATE modules SET status=? WHERE name=?", (status, name))
            if priority:
                conn.execute("UPDATE modules SET priority=? WHERE name=?", (priority, name))
            row = conn.execute("SELECT * FROM modules WHERE name=?", (name,)).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def list_tech() -> list[dict]:
    conn = get_conn()
    try:
        return [dict(r) for r in conn.execute("SELECT * FROM tech_decisions ORDER BY id")]
    finally:
        conn.close()


def propose_tech(area: str, choice: str, rationale: str) -> dict:
    conn = get_conn()
    try:
        with conn:
            cur = conn.execute(
                "INSERT INTO tech_decisions (area, choice, rationale, status) VALUES (?, ?, ?, 'proposed')",
                (area, choice, rationale),
            )
            row = conn.execute("SELECT * FROM tech_decisions WHERE id=?", (cur.lastrowid,)).fetchone()
        return dict(row)
    finally:
        conn.close()


def list_milestones() -> list[dict]:
    conn = get_conn()
    try:
        return [dict(r) for r in conn.execute("SELECT * FROM milestones ORDER BY id")]
    finally:
        conn.close()


def create_milestone(title: str, description: str, due_date: str) -> dict:
    conn = get_conn()
    try:
        with conn:
            cur = conn.execute(
                "INSERT INTO milestones (title, description, due_date) VALUES (?, ?, ?)",
                (title, description, due_date),
            )
            row = conn.execute("SELECT * FROM milestones WHERE id=?", (cur.lastrowid,)).fetchone()
        return dict(row)
    finally:
        conn.close()


def approve_milestone(milestone_id: int, approver_id: int) -> tuple[dict | None, bool]:
    """Returns (milestone, transitioned). transitioned=False means it wasn't 'proposed'."""
    conn = get_conn()
    try:
        with conn:
            cur = conn.execute(
                "UPDATE milestones SET status='approved', approved_by=?, approved_at=datetime('now')"
                " WHERE id=? AND status='proposed'",
                (approver_id, milestone_id),
            )
            row = conn.execute("SELECT * FROM milestones WHERE id=?", (milestone_id,)).fetchone()
        if row is None:
            return None, False
        return dict(row), cur.rowcount == 1
    finally:
        conn.close()


def complete_milestone(milestone_id: int) -> tuple[dict | None, bool]:
    conn = get_conn()
    try:
        with conn:
            cur = conn.execute(
                "UPDATE milestones SET status='done' WHERE id=? AND status='approved'", (milestone_id,)
            )
            row = conn.execute("SELECT * FROM milestones WHERE id=?", (milestone_id,)).fetchone()
        if row is None:
            return None, False
        return dict(row), cur.rowcount == 1
    finally:
        conn.close()
