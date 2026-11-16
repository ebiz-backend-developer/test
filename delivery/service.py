"""Business logic: role checks, validation, prioritization, approval workflow."""
from __future__ import annotations

import sqlite3

from . import models
from .models import (
    AcceptanceCriterion,
    Approval,
    ArchDecision,
    Milestone,
    Module,
    Risk,
    Scope,
    _utcnow,
)
from .store import dumps, loads

READ_ROLES = set(models.ROLES)

# resource -> action -> roles allowed
PERMISSIONS: dict[str, dict[str, set[str]]] = {
    "scope": {
        "read": set(models.ROLES),
        "write": {"admin", "product_owner"},
    },
    "modules": {
        "read": set(models.ROLES),
        "write": {"admin", "product_owner"},
        "progress": {"admin", "product_owner", "tech_lead", "developer"},
    },
    "architecture": {
        "read": set(models.ROLES),
        "write": {"admin", "tech_lead"},
    },
    "milestones": {
        "read": set(models.ROLES),
        "write": {"admin", "product_owner", "tech_lead"},
        "progress": {"admin", "product_owner", "tech_lead", "developer"},
    },
    "risks": {
        "read": set(models.ROLES),
        "write": {"admin", "product_owner", "tech_lead", "developer"},
    },
    "criteria": {
        "read": set(models.ROLES),
        "write": {"admin", "product_owner", "tech_lead", "developer"},
    },
    "approvals": {
        "read": set(models.ROLES),
        "write": {"admin", "product_owner"},
    },
}


class AuthError(PermissionError):
    pass


class ValidationError(ValueError):
    def __init__(self, errors: list[str]):
        super().__init__("; ".join(errors))
        self.errors = errors


def require_role(role: str) -> str:
    if role not in models.ROLES:
        raise AuthError(f"unknown role '{role}'; expected one of {models.ROLES}")
    return role


def check(resource: str, action: str, role: str) -> None:
    require_role(role)
    allowed = PERMISSIONS[resource][action]
    if role not in allowed:
        raise AuthError(f"role '{role}' may not {action} {resource}")


def _raise_if(errors: list[str]) -> None:
    if errors:
        raise ValidationError(errors)


# ---- roles & scope (c1) ----

def list_roles(conn: sqlite3.Connection) -> list[dict]:
    rows = conn.execute("SELECT name, description FROM roles ORDER BY name").fetchall()
    if rows:
        return [dict(r) for r in rows]
    return [{"name": n, "description": models.ROLE_DESCRIPTIONS[n]} for n in models.ROLES]


def get_scope(conn: sqlite3.Connection) -> dict | None:
    row = conn.execute("SELECT * FROM scopes ORDER BY id DESC LIMIT 1").fetchone()
    return _scope_row(row) if row else None


def save_scope(conn: sqlite3.Connection, scope: Scope, role: str) -> dict:
    check("scope", "write", role)
    _raise_if(scope.validate())
    scope.updated_at = _utcnow()
    existing = conn.execute("SELECT id FROM scopes ORDER BY id DESC LIMIT 1").fetchone()
    if existing:
        conn.execute(
            "UPDATE scopes SET vision=?, in_scope=?, out_of_scope=?, assumptions=?,"
            " constraints_list=?, updated_at=? WHERE id=?",
            (scope.vision, dumps(scope.in_scope), dumps(scope.out_of_scope),
             dumps(scope.assumptions), dumps(scope.constraints), scope.updated_at, existing["id"]),
        )
        scope.id = existing["id"]
    else:
        cur = conn.execute(
            "INSERT INTO scopes (vision, in_scope, out_of_scope, assumptions, constraints_list, updated_at)"
            " VALUES (?, ?, ?, ?, ?, ?)",
            (scope.vision, dumps(scope.in_scope), dumps(scope.out_of_scope),
             dumps(scope.assumptions), dumps(scope.constraints), scope.updated_at),
        )
        scope.id = cur.lastrowid
    conn.commit()
    return scope.to_dict()


def _scope_row(row: sqlite3.Row) -> dict:
    return {
        "id": row["id"],
        "vision": row["vision"],
        "in_scope": loads(row["in_scope"]),
        "out_of_scope": loads(row["out_of_scope"]),
        "assumptions": loads(row["assumptions"]),
        "constraints": loads(row["constraints_list"]),
        "updated_at": row["updated_at"],
    }


# ---- modules & MVP (c2) ----

def _module_row(row: sqlite3.Row) -> dict:
    return {
        "id": row["id"],
        "name": row["name"],
        "description": row["description"],
        "priority": row["priority"],
        "mvp": bool(row["mvp"]),
        "effort_points": row["effort_points"],
        "status": row["status"],
        "depends_on": loads(row["depends_on"]),
        "updated_at": row["updated_at"],
    }


def list_modules(conn: sqlite3.Connection, mvp_only: bool = False) -> list[dict]:
    sql = "SELECT * FROM modules"
    if mvp_only:
        sql += " WHERE mvp = 1"
    sql += " ORDER BY CASE priority WHEN 'P0' THEN 0 WHEN 'P1' THEN 1 ELSE 2 END, name"
    return [_module_row(r) for r in conn.execute(sql).fetchall()]


def create_module(conn: sqlite3.Connection, module: Module, role: str) -> dict:
    check("modules", "write", role)
    _raise_if(module.validate())
    _check_module_deps(conn, module)
    module.updated_at = _utcnow()
    try:
        cur = conn.execute(
            "INSERT INTO modules (name, description, priority, mvp, effort_points, status, depends_on, updated_at)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (module.name.strip(), module.description, module.priority, int(module.mvp),
             module.effort_points, module.status, dumps(module.depends_on), module.updated_at),
        )
    except sqlite3.IntegrityError:
        raise ValidationError([f"module '{module.name}' already exists"])
    conn.commit()
    module.id = cur.lastrowid
    return module.to_dict()


def update_module(conn: sqlite3.Connection, module_id: int, patch: dict, role: str) -> dict:
    row = conn.execute("SELECT * FROM modules WHERE id = ?", (module_id,)).fetchone()
    if not row:
        raise ValidationError([f"module {module_id} not found"])
    current = _module_row(row)
    structural = {"name", "description", "priority", "mvp", "effort_points", "depends_on"}
    if structural & set(patch):
        check("modules", "write", role)
    elif set(patch) <= {"status"}:
        check("modules", "progress", role)
    else:
        check("modules", "write", role)
    merged = {**current, **patch}
    module = Module(
        name=merged["name"], description=merged.get("description", ""),
        priority=merged["priority"], mvp=bool(merged["mvp"]),
        effort_points=int(merged["effort_points"]), status=merged["status"],
        depends_on=list(merged.get("depends_on", [])), id=module_id,
    )
    _raise_if(module.validate())
    _check_module_deps(conn, module, exclude_id=module_id)
    module.updated_at = _utcnow()
    try:
        conn.execute(
            "UPDATE modules SET name=?, description=?, priority=?, mvp=?, effort_points=?,"
            " status=?, depends_on=?, updated_at=? WHERE id=?",
            (module.name.strip(), module.description, module.priority, int(module.mvp),
             module.effort_points, module.status, dumps(module.depends_on),
             module.updated_at, module_id),
        )
    except sqlite3.IntegrityError:
        raise ValidationError([f"module '{module.name}' already exists"])
    conn.commit()
    return module.to_dict()


def _check_module_deps(conn: sqlite3.Connection, module: Module, exclude_id: int | None = None) -> None:
    if not module.depends_on:
        return
    names = [r["name"] for r in conn.execute("SELECT id, name FROM modules").fetchall()
              if r["id"] != exclude_id]
    missing = [d for d in module.depends_on if d not in names and d != module.name]
    if missing:
        raise ValidationError([f"unknown module dependencies: {missing}"])


def mvp_summary(conn: sqlite3.Connection) -> dict:
    rows = list_modules(conn, mvp_only=True)
    by_status: dict[str, int] = {}
    for r in rows:
        by_status[r["status"]] = by_status.get(r["status"], 0) + 1
    return {
        "total": len(rows),
        "points": sum(r["effort_points"] for r in rows),
        "done": sum(1 for r in rows if r["status"] == "done"),
        "by_status": by_status,
        "modules": rows,
    }


# ---- architecture / tech stack (c3) ----

def _arch_row(row: sqlite3.Row) -> dict:
    return {k: row[k] for k in ("id", "category", "option_name", "status", "rationale", "decided_by", "updated_at")}


def list_arch(conn: sqlite3.Connection, selected_only: bool = False) -> list[dict]:
    sql = "SELECT * FROM arch_decisions"
    if selected_only:
        sql += " WHERE status = 'selected'"
    sql += " ORDER BY category, option_name"
    return [_arch_row(r) for r in conn.execute(sql).fetchall()]


def save_arch(conn: sqlite3.Connection, decision: ArchDecision, role: str) -> dict:
    check("architecture", "write", role)
    _raise_if(decision.validate())
    decision.updated_at = _utcnow()
    decision.decided_by = decision.decided_by or role
    if decision.status == "selected":
        # One selected option per category: demote previous selections.
        conn.execute(
            "UPDATE arch_decisions SET status='rejected', updated_at=? WHERE category=? AND status='selected'",
            (decision.updated_at, decision.category),
        )
    try:
        cur = conn.execute(
            "INSERT INTO arch_decisions (category, option_name, status, rationale, decided_by, updated_at)"
            " VALUES (?, ?, ?, ?, ?, ?)"
            " ON CONFLICT (category, option_name) DO UPDATE SET status=excluded.status,"
            " rationale=excluded.rationale, decided_by=excluded.decided_by, updated_at=excluded.updated_at",
            (decision.category.strip(), decision.option_name.strip(), decision.status,
             decision.rationale, decision.decided_by, decision.updated_at),
        )
    except sqlite3.IntegrityError as exc:
        raise ValidationError([str(exc)])
    conn.commit()
    row = conn.execute(
        "SELECT * FROM arch_decisions WHERE category=? AND option_name=?",
        (decision.category.strip(), decision.option_name.strip()),
    ).fetchone()
    decision.id = row["id"]
    return _arch_row(row)


# ---- milestones, risks, criteria, approvals (c4) ----

def _milestone_row(row: sqlite3.Row) -> dict:
    return {k: row[k] for k in ("id", "name", "phase", "description", "start_date",
                                "end_date", "status", "owner_role", "updated_at")}


def list_milestones(conn: sqlite3.Connection) -> list[dict]:
    rows = conn.execute(
        "SELECT * FROM milestones ORDER BY start_date, end_date, id"
    ).fetchall()
    out = []
    for r in rows:
        item = _milestone_row(r)
        item["acceptance"] = readiness(conn, r["id"])
        out.append(item)
    return out


def get_milestone(conn: sqlite3.Connection, milestone_id: int) -> dict:
    row = conn.execute("SELECT * FROM milestones WHERE id = ?", (milestone_id,)).fetchone()
    if not row:
        raise ValidationError([f"milestone {milestone_id} not found"])
    item = _milestone_row(row)
    item["risks"] = list_risks(conn, milestone_id)
    item["criteria"] = list_criteria(conn, milestone_id)
    item["approvals"] = list_approvals(conn, milestone_id)
    item["acceptance"] = readiness(conn, milestone_id)
    return item


def create_milestone(conn: sqlite3.Connection, milestone: Milestone, role: str) -> dict:
    check("milestones", "write", role)
    _raise_if(milestone.validate())
    milestone.updated_at = _utcnow()
    try:
        cur = conn.execute(
            "INSERT INTO milestones (name, phase, description, start_date, end_date, status, owner_role, updated_at)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (milestone.name.strip(), milestone.phase, milestone.description, milestone.start_date,
             milestone.end_date, milestone.status, milestone.owner_role, milestone.updated_at),
        )
    except sqlite3.IntegrityError:
        raise ValidationError([f"milestone '{milestone.name}' already exists"])
    conn.commit()
    milestone.id = cur.lastrowid
    return milestone.to_dict()


def update_milestone(conn: sqlite3.Connection, milestone_id: int, patch: dict, role: str) -> dict:
    row = conn.execute("SELECT * FROM milestones WHERE id = ?", (milestone_id,)).fetchone()
    if not row:
        raise ValidationError([f"milestone {milestone_id} not found"])
    current = _milestone_row(row)
    if set(patch) <= {"status"}:
        check("milestones", "progress", role)
    else:
        check("milestones", "write", role)
    merged = {**current, **patch}
    milestone = Milestone(
        name=merged["name"], phase=merged["phase"], description=merged.get("description", ""),
        start_date=merged.get("start_date", ""), end_date=merged.get("end_date", ""),
        status=merged["status"], owner_role=merged.get("owner_role", "product_owner"),
        id=milestone_id,
    )
    _raise_if(milestone.validate())
    if current["status"] == "approved" and milestone.status != "approved" and role != "admin":
        raise AuthError("only admin can move a milestone out of 'approved'")
    milestone.updated_at = _utcnow()
    try:
        conn.execute(
            "UPDATE milestones SET name=?, phase=?, description=?, start_date=?, end_date=?,"
            " status=?, owner_role=?, updated_at=? WHERE id=?",
            (milestone.name.strip(), milestone.phase, milestone.description, milestone.start_date,
             milestone.end_date, milestone.status, milestone.owner_role,
             milestone.updated_at, milestone_id),
        )
    except sqlite3.IntegrityError:
        raise ValidationError([f"milestone '{milestone.name}' already exists"])
    conn.commit()
    return milestone.to_dict()


def _risk_row(row: sqlite3.Row) -> dict:
    risk = Risk(
        title=row["title"], likelihood=row["likelihood"], impact=row["impact"],
        mitigation=row["mitigation"], status=row["status"],
        milestone_id=row["milestone_id"], id=row["id"], updated_at=row["updated_at"],
    )
    return risk.to_dict()


def list_risks(conn: sqlite3.Connection, milestone_id: int | None = None) -> list[dict]:
    if milestone_id is None:
        rows = conn.execute("SELECT * FROM risks ORDER BY id").fetchall()
    else:
        rows = conn.execute("SELECT * FROM risks WHERE milestone_id = ? ORDER BY id", (milestone_id,)).fetchall()
    risks = [_risk_row(r) for r in rows]
    risks.sort(key=lambda r: -r["exposure"])
    return risks


def save_risk(conn: sqlite3.Connection, risk: Risk, role: str) -> dict:
    check("risks", "write", role)
    _raise_if(risk.validate())
    if risk.milestone_id is not None:
        exists = conn.execute("SELECT id FROM milestones WHERE id = ?", (risk.milestone_id,)).fetchone()
        if not exists:
            raise ValidationError([f"milestone {risk.milestone_id} not found"])
    risk.updated_at = _utcnow()
    if risk.id:
        conn.execute(
            "UPDATE risks SET milestone_id=?, title=?, likelihood=?, impact=?, mitigation=?, status=?, updated_at=?"
            " WHERE id=?",
            (risk.milestone_id, risk.title.strip(), risk.likelihood, risk.impact,
             risk.mitigation, risk.status, risk.updated_at, risk.id),
        )
    else:
        cur = conn.execute(
            "INSERT INTO risks (milestone_id, title, likelihood, impact, mitigation, status, updated_at)"
            " VALUES (?, ?, ?, ?, ?, ?, ?)",
            (risk.milestone_id, risk.title.strip(), risk.likelihood, risk.impact,
             risk.mitigation, risk.status, risk.updated_at),
        )
        risk.id = cur.lastrowid
    conn.commit()
    return risk.to_dict()


def _criterion_row(row: sqlite3.Row) -> dict:
    return {k: row[k] for k in ("id", "milestone_id", "description", "verification_method", "status", "updated_at")}


def list_criteria(conn: sqlite3.Connection, milestone_id: int | None = None) -> list[dict]:
    if milestone_id is None:
        rows = conn.execute("SELECT * FROM acceptance_criteria ORDER BY id").fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM acceptance_criteria WHERE milestone_id = ? ORDER BY id", (milestone_id,)
        ).fetchall()
    return [_criterion_row(r) for r in rows]


def save_criterion(conn: sqlite3.Connection, criterion: AcceptanceCriterion, role: str) -> dict:
    check("criteria", "write", role)
    _raise_if(criterion.validate())
    exists = conn.execute("SELECT id FROM milestones WHERE id = ?", (criterion.milestone_id,)).fetchone()
    if not exists:
        raise ValidationError([f"milestone {criterion.milestone_id} not found"])
    criterion.updated_at = _utcnow()
    if criterion.id:
        conn.execute(
            "UPDATE acceptance_criteria SET milestone_id=?, description=?, verification_method=?, status=?, updated_at=?"
            " WHERE id=?",
            (criterion.milestone_id, criterion.description.strip(), criterion.verification_method,
             criterion.status, criterion.updated_at, criterion.id),
        )
    else:
        cur = conn.execute(
            "INSERT INTO acceptance_criteria (milestone_id, description, verification_method, status, updated_at)"
            " VALUES (?, ?, ?, ?, ?)",
            (criterion.milestone_id, criterion.description.strip(), criterion.verification_method,
             criterion.status, criterion.updated_at),
        )
        criterion.id = cur.lastrowid
    conn.commit()
    out = criterion.to_dict()
    return out


def readiness(conn: sqlite3.Connection, milestone_id: int) -> dict:
    criteria = list_criteria(conn, milestone_id)
    open_risks = [r for r in list_risks(conn, milestone_id) if r["status"] != "closed"]
    high_open = [r for r in open_risks if r["exposure"] >= 6]
    met = sum(1 for c in criteria if c["status"] == "met")
    return {
        "criteria_total": len(criteria),
        "criteria_met": met,
        "criteria_pending": sum(1 for c in criteria if c["status"] == "pending"),
        "criteria_failed": sum(1 for c in criteria if c["status"] == "failed"),
        "open_risks": len(open_risks),
        "high_exposure_open_risks": len(high_open),
        "ready": bool(criteria) and met == len(criteria) and not high_open,
    }


def list_approvals(conn: sqlite3.Connection, milestone_id: int | None = None) -> list[dict]:
    if milestone_id is None:
        rows = conn.execute("SELECT * FROM approvals ORDER BY id").fetchall()
    else:
        rows = conn.execute("SELECT * FROM approvals WHERE milestone_id = ? ORDER BY id", (milestone_id,)).fetchall()
    return [{k: r[k] for k in ("id", "milestone_id", "approver_role", "decision", "comment", "created_at")} for r in rows]


def record_approval(conn: sqlite3.Connection, approval: Approval, role: str) -> dict:
    """Approve a milestone. The caller's role must be an approver role."""
    check("approvals", "write", role)
    if approval.approver_role not in ("admin", "product_owner"):
        raise AuthError("only admin or product_owner can approve milestones")
    _raise_if(approval.validate())
    row = conn.execute("SELECT * FROM milestones WHERE id = ?", (approval.milestone_id,)).fetchone()
    if not row:
        raise ValidationError([f"milestone {approval.milestone_id} not found"])
    if approval.decision == "approved":
        ready = readiness(conn, approval.milestone_id)
        if not ready["ready"]:
            raise ValidationError([
                "milestone is not ready: "
                f"{ready['criteria_met']}/{ready['criteria_total']} criteria met, "
                f"{ready['high_exposure_open_risks']} high-exposure open risks"
            ])
        conn.execute(
            "UPDATE milestones SET status='approved', updated_at=? WHERE id=?",
            (_utcnow(), approval.milestone_id),
        )
    approval.created_at = approval.created_at or _utcnow()
    cur = conn.execute(
        "INSERT INTO approvals (milestone_id, approver_role, decision, comment, created_at)"
        " VALUES (?, ?, ?, ?, ?)",
        (approval.milestone_id, approval.approver_role, approval.decision,
         approval.comment, approval.created_at),
    )
    conn.commit()
    approval.id = cur.lastrowid
    return approval.to_dict()


def roadmap(conn: sqlite3.Connection) -> dict:
    """Phase-by-phase timeline rollup for the UI overview."""
    milestones = list_milestones(conn)
    phases: dict[str, list[dict]] = {p: [] for p in models.PHASES}
    for m in milestones:
        phases[m["phase"]].append(m)
    return {
        "phases": [
            {"phase": p, "milestones": phases[p],
             "approved": sum(1 for m in phases[p] if m["status"] == "approved"),
             "total": len(phases[p])}
            for p in models.PHASES
        ],
        "mvp": mvp_summary(conn),
        "stack": list_arch(conn, selected_only=True),
    }
