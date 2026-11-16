"""Business logic: role checks, validation, prioritization, approval workflow."""
from __future__ import annotations

import sqlite3

from . import models
from .config import ARCH_CATEGORIES, PHASE_ORDER, ROLES
from .models import (
    AcceptanceCriterion,
    Approval,
    ArchDecision,
    Milestone,
    Module,
    Risk,
    Scope,
    utcnow,
)
from .store import dumps, loads


class AuthError(PermissionError):
    """Raised when a role is unknown or lacks permission."""


class ValidationError(ValueError):
    def __init__(self, errors: list[str]):
        super().__init__("; ".join(errors))
        self.errors = errors


class NotFoundError(LookupError):
    pass


# resource -> action -> roles allowed
PERMISSIONS: dict[str, dict[str, set[str]]] = {
    "scope": {
        "read": set(ROLES),
        "write": {"admin", "product_owner"},
    },
    "modules": {
        "read": {"admin", "product_owner", "tech_lead", "developer", "stakeholder"},
        "write": {"admin", "product_owner"},
        "progress": {"admin", "product_owner", "tech_lead", "developer"},
    },
    "architecture": {
        "read": {"admin", "product_owner", "tech_lead", "developer", "stakeholder"},
        "write": {"admin", "tech_lead"},
    },
    "milestones": {
        "read": {"admin", "product_owner", "tech_lead", "developer", "stakeholder"},
        "write": {"admin", "product_owner", "tech_lead"},
        "progress": {"admin", "product_owner", "tech_lead", "developer"},
    },
    "risks": {
        "read": {"admin", "product_owner", "tech_lead", "developer", "stakeholder"},
        "write": {"admin", "product_owner", "tech_lead", "developer"},
    },
    "criteria": {
        "read": {"admin", "product_owner", "tech_lead", "developer", "stakeholder"},
        "write": {"admin", "product_owner", "tech_lead", "developer"},
    },
    "approvals": {
        "read": {"admin", "product_owner", "tech_lead", "developer", "stakeholder"},
        "write": {"admin", "product_owner"},
    },
}

_ROLES = ROLES


def require_role(role: str) -> str:
    if role not in _ROLES:
        raise AuthError(f"unknown role '{role}'; expected one of {_ROLES}")
    return role


def check(resource: str, action: str, role: str) -> None:
    require_role(role)
    if role not in PERMISSIONS[resource][action]:
        raise AuthError(f"role '{role}' may not {action} {resource}")


def _raise_if(errors: list[str]) -> None:
    if errors:
        raise ValidationError(errors)


# ------------------------------------------------------------- c1: roles


def list_roles(conn: sqlite3.Connection) -> list[dict]:
    rows = conn.execute("SELECT name, description FROM roles ORDER BY name").fetchall()
    if rows:
        return [dict(r) for r in rows]
    from .config import ROLE_DESCRIPTIONS

    return [{"name": n, "description": ROLE_DESCRIPTIONS[n]} for n in _ROLES]


# ------------------------------------------------------------- c1: scope


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


def get_scope(conn: sqlite3.Connection) -> dict | None:
    row = conn.execute("SELECT * FROM scopes ORDER BY id DESC LIMIT 1").fetchone()
    return _scope_row(row) if row else None


def save_scope(conn: sqlite3.Connection, scope: Scope, role: str) -> dict:
    check("scope", "write", role)
    _raise_if(scope.validate())
    scope.updated_at = utcnow()
    existing = conn.execute("SELECT id FROM scopes ORDER BY id DESC LIMIT 1").fetchone()
    if existing:
        conn.execute(
            "UPDATE scopes SET vision=?, in_scope=?, out_of_scope=?, assumptions=?,"
            " constraints_list=?, updated_at=? WHERE id=?",
            (
                scope.vision,
                dumps(scope.in_scope),
                dumps(scope.out_of_scope),
                dumps(scope.assumptions),
                dumps(scope.constraints),
                scope.updated_at,
                existing["id"],
            ),
        )
        scope.id = existing["id"]
    else:
        cur = conn.execute(
            "INSERT INTO scopes (vision, in_scope, out_of_scope, assumptions,"
            " constraints_list, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
            (
                scope.vision,
                dumps(scope.in_scope),
                dumps(scope.out_of_scope),
                dumps(scope.assumptions),
                dumps(scope.constraints),
                scope.updated_at,
            ),
        )
        scope.id = cur.lastrowid
    conn.commit()
    return scope.to_dict()


# ------------------------------------------------- c2: modules and MVP


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


def list_modules(conn: sqlite3.Connection) -> list[dict]:
    rows = conn.execute("SELECT * FROM modules ORDER BY name").fetchall()
    return [_module_row(r) for r in rows]


def get_module(conn: sqlite3.Connection, module_id: int) -> dict:
    row = conn.execute("SELECT * FROM modules WHERE id=?", (module_id,)).fetchone()
    if row is None:
        raise NotFoundError(f"module {module_id} not found")
    return _module_row(row)


def _module_names(conn: sqlite3.Connection, exclude: str = "") -> set[str]:
    rows = conn.execute("SELECT name FROM modules WHERE name != ?", (exclude,)).fetchall()
    return {r["name"] for r in rows}


def _dependency_errors(conn: sqlite3.Connection, module: Module) -> list[str]:
    known = _module_names(conn, exclude=module.name)
    errors = [f"unknown dependency '{d}'" for d in module.depends_on if d not in known]
    if errors:
        return errors
    # cycle check over the graph as it would look after this write
    graph: dict[str, list[str]] = {}
    for row in conn.execute("SELECT name, depends_on FROM modules"):
        graph[row["name"]] = loads(row["depends_on"])
    graph[module.name] = list(module.depends_on)
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(node: str, trail: list[str]) -> list[str] | None:
        if node in visiting:
            return trail + [node]
        if node in visited:
            return None
        visiting.add(node)
        for dep in graph.get(node, []):
            cycle = visit(dep, trail + [node])
            if cycle:
                return cycle
        visiting.discard(node)
        visited.add(node)
        return None

    cycle = visit(module.name, [])
    if cycle:
        return [f"dependency cycle detected: {' -> '.join(cycle)}"]
    return []


def create_module(conn: sqlite3.Connection, module: Module, role: str) -> dict:
    check("modules", "write", role)
    _raise_if(module.validate())
    _raise_if(_dependency_errors(conn, module))
    module.updated_at = utcnow()
    try:
        cur = conn.execute(
            "INSERT INTO modules (name, description, priority, mvp, effort_points,"
            " status, depends_on, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                module.name,
                module.description,
                module.priority,
                int(module.mvp),
                module.effort_points,
                module.status,
                dumps(module.depends_on),
                module.updated_at,
            ),
        )
    except sqlite3.IntegrityError:
        raise ValidationError([f"module '{module.name}' already exists"])
    conn.commit()
    module.id = cur.lastrowid
    return module.to_dict()


def update_module_status(
    conn: sqlite3.Connection, module_id: int, status: str, role: str
) -> dict:
    check("modules", "progress", role)
    current = get_module(conn, module_id)
    if status not in models.MODULE_STATUSES:
        raise ValidationError([f"status must be one of {models.MODULE_STATUSES}"])
    allowed = models.MODULE_TRANSITIONS[current["status"]]
    if status != current["status"] and status not in allowed:
        raise ValidationError(
            [f"cannot move module from {current['status']} to {status}"]
        )
    if status == "done":
        # dependencies must be done first
        rows = conn.execute("SELECT name, status FROM modules").fetchall()
        by_name = {r["name"]: r["status"] for r in rows}
        open_deps = [d for d in current["depends_on"] if by_name.get(d) != "done"]
        if open_deps:
            raise ValidationError(
                [f"dependencies not done yet: {sorted(open_deps)}"]
            )
    conn.execute(
        "UPDATE modules SET status=?, updated_at=? WHERE id=?",
        (status, utcnow(), module_id),
    )
    conn.commit()
    return get_module(conn, module_id)


def update_module_plan(
    conn: sqlite3.Connection, module_id: int, fields: dict, role: str
) -> dict:
    """Owner-level edit: priority, mvp flag, effort, description, depends_on."""
    check("modules", "write", role)
    current = get_module(conn, module_id)
    merged = {**current, **{k: v for k, v in fields.items() if k in current}}
    module = Module(
        name=merged["name"],
        description=merged.get("description", ""),
        priority=merged.get("priority", "P2"),
        mvp=bool(merged.get("mvp", False)),
        effort_points=merged.get("effort_points", 1),
        status=current["status"],  # status moves only via update_module_status
        depends_on=list(merged.get("depends_on", [])),
        id=module_id,
    )
    _raise_if(module.validate())
    _raise_if(_dependency_errors(conn, module))
    conn.execute(
        "UPDATE modules SET description=?, priority=?, mvp=?, effort_points=?,"
        " depends_on=?, updated_at=? WHERE id=?",
        (
            module.description,
            module.priority,
            int(module.mvp),
            module.effort_points,
            dumps(module.depends_on),
            utcnow(),
            module_id,
        ),
    )
    conn.commit()
    return get_module(conn, module_id)


def _priority_rank(priority: str) -> int:
    return {"P0": 0, "P1": 1, "P2": 2}.get(priority, 3)


def mvp_modules(conn: sqlite3.Connection) -> list[dict]:
    """MVP modules ordered by priority, then effort, then name."""
    rows = conn.execute("SELECT * FROM modules WHERE mvp=1").fetchall()
    mods = [_module_row(r) for r in rows]
    mods.sort(
        key=lambda m: (_priority_rank(m["priority"]), m["effort_points"], m["name"])
    )
    return mods


def mvp_readiness(conn: sqlite3.Connection) -> dict:
    """Effort-weighted MVP completion plus per-module state."""
    mods = mvp_modules(conn)
    total = sum(m["effort_points"] for m in mods)
    done = sum(m["effort_points"] for m in mods if m["status"] == "done")
    return {
        "total_modules": len(mods),
        "done_modules": sum(1 for m in mods if m["status"] == "done"),
        "total_points": total,
        "done_points": done,
        "percent": round(100 * done / total, 1) if total else 100.0,
        "modules": mods,
    }


def build_order(conn: sqlite3.Connection) -> list[str]:
    """Topological build order over module dependencies (MVP first)."""
    rows = conn.execute(
        "SELECT name, mvp, priority, depends_on FROM modules"
    ).fetchall()
    graph = {r["name"]: loads(r["depends_on"]) for r in rows}
    meta = {r["name"]: (not r["mvp"], _priority_rank(r["priority"]), r["name"]) for r in rows}
    ordered: list[str] = []
    temporary: set[str] = set()
    permanent: set[str] = set()

    def visit(node: str) -> None:
        if node in permanent:
            return
        if node in temporary:
            raise ValidationError([f"dependency cycle detected at '{node}'"])
        temporary.add(node)
        for dep in sorted(graph.get(node, []), key=lambda d: meta.get(d, (9, 9, d))):
            if dep in graph:
                visit(dep)
        temporary.discard(node)
        permanent.add(node)
        ordered.append(node)

    for name in sorted(graph, key=lambda n: meta[n]):
        visit(name)
    return ordered


# ----------------------------------------------- c3: architecture & stack


def _arch_row(row: sqlite3.Row) -> dict:
    return {
        "id": row["id"],
        "category": row["category"],
        "option_name": row["option_name"],
        "status": row["status"],
        "rationale": row["rationale"],
        "decided_by": row["decided_by"],
        "updated_at": row["updated_at"],
    }


def list_arch(conn: sqlite3.Connection) -> list[dict]:
    rows = conn.execute(
        "SELECT * FROM arch_decisions ORDER BY category, option_name"
    ).fetchall()
    return [_arch_row(r) for r in rows]


def get_arch(conn: sqlite3.Connection, decision_id: int) -> dict:
    row = conn.execute(
        "SELECT * FROM arch_decisions WHERE id=?", (decision_id,)
    ).fetchone()
    if row is None:
        raise NotFoundError(f"architecture decision {decision_id} not found")
    return _arch_row(row)


def propose_arch(conn: sqlite3.Connection, decision: ArchDecision, role: str) -> dict:
    check("architecture", "write", role)
    _raise_if(decision.validate())
    if decision.status == "selected":
        _raise_if(_select_conflicts(conn, decision.category, exclude_id=None))
        decision.decided_by = decision.decided_by or role
    decision.updated_at = utcnow()
    try:
        cur = conn.execute(
            "INSERT INTO arch_decisions (category, option_name, status, rationale,"
            " decided_by, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
            (
                decision.category,
                decision.option_name,
                decision.status,
                decision.rationale,
                decision.decided_by,
                decision.updated_at,
            ),
        )
    except sqlite3.IntegrityError:
        raise ValidationError(
            [f"option '{decision.option_name}' already exists in {decision.category}"]
        )
    conn.commit()
    decision.id = cur.lastrowid
    return decision.to_dict()


def _select_conflicts(
    conn: sqlite3.Connection, category: str, exclude_id: int | None
) -> list[str]:
    row = conn.execute(
        "SELECT id, option_name FROM arch_decisions"
        " WHERE category=? AND status='selected' AND id IS NOT ?",
        (category, exclude_id),
    ).fetchone()
    if row:
        return [
            f"category '{category}' already selected '{row['option_name']}';"
            " reject it first"
        ]
    return []


def select_arch(
    conn: sqlite3.Connection, decision_id: int, rationale: str, role: str
) -> dict:
    check("architecture", "write", role)
    current = get_arch(conn, decision_id)
    if not rationale.strip():
        raise ValidationError(["rationale is required when an option is selected"])
    _raise_if(_select_conflicts(conn, current["category"], exclude_id=decision_id))
    conn.execute(
        "UPDATE arch_decisions SET status='selected', rationale=?, decided_by=?,"
        " updated_at=? WHERE id=?",
        (rationale.strip(), role, utcnow(), decision_id),
    )
    conn.commit()
    return get_arch(conn, decision_id)


def reject_arch(conn: sqlite3.Connection, decision_id: int, role: str) -> dict:
    check("architecture", "write", role)
    get_arch(conn, decision_id)
    conn.execute(
        "UPDATE arch_decisions SET status='rejected', updated_at=? WHERE id=?",
        (utcnow(), decision_id),
    )
    conn.commit()
    return get_arch(conn, decision_id)


def stack_summary(conn: sqlite3.Connection) -> dict:
    """Selected option per category plus overall decided/pending state."""
    selected = {
        r["category"]: _arch_row(r)
        for r in conn.execute(
            "SELECT * FROM arch_decisions WHERE status='selected'"
        )
    }
    decided = [c for c in ARCH_CATEGORIES if c in selected]
    pending = [c for c in ARCH_CATEGORIES if c not in selected]
    return {
        "decided": len(pending) == 0,
        "decided_categories": decided,
        "pending_categories": pending,
        "stack": {c: selected[c] for c in decided},
    }


# --------------------------------- c4: milestones, risks, criteria, approvals


def _milestone_row(row: sqlite3.Row) -> dict:
    return {
        "id": row["id"],
        "name": row["name"],
        "phase": row["phase"],
        "description": row["description"],
        "start_date": row["start_date"],
        "end_date": row["end_date"],
        "status": row["status"],
        "owner_role": row["owner_role"],
        "updated_at": row["updated_at"],
    }


def list_milestones(conn: sqlite3.Connection) -> list[dict]:
    rows = conn.execute("SELECT * FROM milestones").fetchall()
    order = {phase: index for index, phase in enumerate(PHASE_ORDER)}
    mods = [_milestone_row(r) for r in rows]
    mods.sort(key=lambda m: (order.get(m["phase"], 99), m["start_date"], m["name"]))
    return mods


def get_milestone(conn: sqlite3.Connection, milestone_id: int) -> dict:
    row = conn.execute(
        "SELECT * FROM milestones WHERE id=?", (milestone_id,)
    ).fetchone()
    if row is None:
        raise NotFoundError(f"milestone {milestone_id} not found")
    return _milestone_row(row)


def create_milestone(conn: sqlite3.Connection, milestone: Milestone, role: str) -> dict:
    check("milestones", "write", role)
    _raise_if(milestone.validate())
    milestone.updated_at = utcnow()
    try:
        cur = conn.execute(
            "INSERT INTO milestones (name, phase, description, start_date, end_date,"
            " status, owner_role, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                milestone.name,
                milestone.phase,
                milestone.description,
                milestone.start_date,
                milestone.end_date,
                milestone.status,
                milestone.owner_role,
                milestone.updated_at,
            ),
        )
    except sqlite3.IntegrityError:
        raise ValidationError([f"milestone '{milestone.name}' already exists"])
    conn.commit()
    milestone.id = cur.lastrowid
    return milestone.to_dict()


def update_milestone(
    conn: sqlite3.Connection, milestone_id: int, fields: dict, role: str
) -> dict:
    current = get_milestone(conn, milestone_id)
    if "status" in fields and set(fields) == {"status"}:
        check("milestones", "progress", role)
    else:
        check("milestones", "write", role)
    if current["status"] == "approved" and fields.get("status") != "approved":
        _raise_if(["approved milestones are locked; record a new approval to reopen"])
    merged = {**current, **{k: v for k, v in fields.items() if k in current}}
    milestone = Milestone(
        name=merged["name"],
        phase=merged["phase"],
        description=merged.get("description", ""),
        start_date=merged.get("start_date", ""),
        end_date=merged.get("end_date", ""),
        status=merged.get("status", "draft"),
        owner_role=merged.get("owner_role", "product_owner"),
        id=milestone_id,
    )
    _raise_if(milestone.validate())
    if milestone.status == "approved":
        _raise_if(["use the approval workflow to approve a milestone, not a status edit"])
    conn.execute(
        "UPDATE milestones SET phase=?, description=?, start_date=?, end_date=?,"
        " status=?, owner_role=?, updated_at=? WHERE id=?",
        (
            milestone.phase,
            milestone.description,
            milestone.start_date,
            milestone.end_date,
            milestone.status,
            milestone.owner_role,
            utcnow(),
            milestone_id,
        ),
    )
    conn.commit()
    return get_milestone(conn, milestone_id)


def timeline(conn: sqlite3.Connection) -> dict:
    """Phases in order, each with its milestones and counts."""
    phases = []
    for phase in PHASE_ORDER:
        rows = conn.execute(
            "SELECT * FROM milestones WHERE phase=? ORDER BY start_date, name",
            (phase,),
        ).fetchall()
        items = [_milestone_row(r) for r in rows]
        phases.append(
            {
                "phase": phase,
                "milestones": items,
                "count": len(items),
                "approved": sum(1 for m in items if m["status"] == "approved"),
            }
        )
    all_ms = list_milestones(conn)
    return {
        "phases": phases,
        "total": len(all_ms),
        "approved": sum(1 for m in all_ms if m["status"] == "approved"),
    }


# ------------------------------------------------------------------ risks


def _risk_row(row: sqlite3.Row) -> dict:
    data = {
        "id": row["id"],
        "title": row["title"],
        "likelihood": row["likelihood"],
        "impact": row["impact"],
        "mitigation": row["mitigation"],
        "status": row["status"],
        "milestone_id": row["milestone_id"],
        "updated_at": row["updated_at"],
    }
    scale = {"low": 1, "medium": 2, "high": 3}
    data["exposure"] = scale[data["likelihood"]] * scale[data["impact"]]
    return data


def list_risks(conn: sqlite3.Connection, milestone_id: int | None = None) -> list[dict]:
    if milestone_id is None:
        rows = conn.execute("SELECT * FROM risks").fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM risks WHERE milestone_id=?", (milestone_id,)
        ).fetchall()
    risks = [_risk_row(r) for r in rows]
    risks.sort(key=lambda r: (-r["exposure"], r["title"]))
    return risks


def get_risk(conn: sqlite3.Connection, risk_id: int) -> dict:
    row = conn.execute("SELECT * FROM risks WHERE id=?", (risk_id,)).fetchone()
    if row is None:
        raise NotFoundError(f"risk {risk_id} not found")
    return _risk_row(row)


def create_risk(conn: sqlite3.Connection, risk: Risk, role: str) -> dict:
    check("risks", "write", role)
    _raise_if(risk.validate())
    if risk.milestone_id is not None:
        get_milestone(conn, risk.milestone_id)
    risk.updated_at = utcnow()
    cur = conn.execute(
        "INSERT INTO risks (title, likelihood, impact, mitigation, status,"
        " milestone_id, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (
            risk.title,
            risk.likelihood,
            risk.impact,
            risk.mitigation,
            risk.status,
            risk.milestone_id,
            risk.updated_at,
        ),
    )
    conn.commit()
    risk.id = cur.lastrowid
    return risk.to_dict()


def update_risk(conn: sqlite3.Connection, risk_id: int, fields: dict, role: str) -> dict:
    check("risks", "write", role)
    current = get_risk(conn, risk_id)
    merged = {**current, **{k: v for k, v in fields.items() if k in current}}
    risk = Risk(
        title=merged["title"],
        likelihood=merged.get("likelihood", "medium"),
        impact=merged.get("impact", "medium"),
        mitigation=merged.get("mitigation", ""),
        status=merged.get("status", "open"),
        milestone_id=merged.get("milestone_id"),
        id=risk_id,
    )
    _raise_if(risk.validate())
    if risk.milestone_id is not None:
        get_milestone(conn, risk.milestone_id)
    conn.execute(
        "UPDATE risks SET title=?, likelihood=?, impact=?, mitigation=?, status=?,"
        " milestone_id=?, updated_at=? WHERE id=?",
        (
            risk.title,
            risk.likelihood,
            risk.impact,
            risk.mitigation,
            risk.status,
            risk.milestone_id,
            utcnow(),
            risk_id,
        ),
    )
    conn.commit()
    return get_risk(conn, risk_id)


def milestone_health(conn: sqlite3.Connection, milestone_id: int) -> dict:
    """Health combines criteria state and open high-exposure risks."""
    get_milestone(conn, milestone_id)
    criteria = list_criteria(conn, milestone_id)
    risks = list_risks(conn, milestone_id)
    open_hot = [
        r for r in risks if r["status"] == "open" and r["exposure"] >= models.HIGH_EXPOSURE
    ]
    failed = [c for c in criteria if c["status"] == "failed"]
    pending = [c for c in criteria if c["status"] == "pending"]
    if failed or open_hot:
        health = "at_risk"
    elif pending or not criteria:
        health = "in_progress"
    else:
        health = "ready"
    return {
        "milestone_id": milestone_id,
        "health": health,
        "criteria_total": len(criteria),
        "criteria_met": sum(1 for c in criteria if c["status"] == "met"),
        "criteria_failed": len(failed),
        "open_high_risks": len(open_hot),
    }


# ------------------------------------------------- acceptance criteria


def _criterion_row(row: sqlite3.Row) -> dict:
    return {
        "id": row["id"],
        "milestone_id": row["milestone_id"],
        "description": row["description"],
        "verification_method": row["verification_method"],
        "status": row["status"],
        "updated_at": row["updated_at"],
    }


def list_criteria(conn: sqlite3.Connection, milestone_id: int) -> list[dict]:
    rows = conn.execute(
        "SELECT * FROM acceptance_criteria WHERE milestone_id=? ORDER BY id",
        (milestone_id,),
    ).fetchall()
    return [_criterion_row(r) for r in rows]


def get_criterion(conn: sqlite3.Connection, criterion_id: int) -> dict:
    row = conn.execute(
        "SELECT * FROM acceptance_criteria WHERE id=?", (criterion_id,)
    ).fetchone()
    if row is None:
        raise NotFoundError(f"criterion {criterion_id} not found")
    return _criterion_row(row)


def add_criterion(
    conn: sqlite3.Connection, criterion: AcceptanceCriterion, role: str
) -> dict:
    check("criteria", "write", role)
    _raise_if(criterion.validate())
    get_milestone(conn, criterion.milestone_id)
    criterion.updated_at = utcnow()
    cur = conn.execute(
        "INSERT INTO acceptance_criteria (milestone_id, description,"
        " verification_method, status, updated_at) VALUES (?, ?, ?, ?, ?)",
        (
            criterion.milestone_id,
            criterion.description,
            criterion.verification_method,
            criterion.status,
            criterion.updated_at,
        ),
    )
    conn.commit()
    criterion.id = cur.lastrowid
    return criterion.to_dict()


def set_criterion_status(
    conn: sqlite3.Connection, criterion_id: int, status: str, role: str
) -> dict:
    check("criteria", "write", role)
    if status not in models.CRITERION_STATUSES:
        raise ValidationError([f"status must be one of {models.CRITERION_STATUSES}"])
    get_criterion(conn, criterion_id)
    conn.execute(
        "UPDATE acceptance_criteria SET status=?, updated_at=? WHERE id=?",
        (status, utcnow(), criterion_id),
    )
    conn.commit()
    return get_criterion(conn, criterion_id)


# --------------------------------------------------------------- approvals


def _approval_row(row: sqlite3.Row) -> dict:
    return {
        "id": row["id"],
        "milestone_id": row["milestone_id"],
        "approver_role": row["approver_role"],
        "decision": row["decision"],
        "comment": row["comment"],
        "created_at": row["created_at"],
    }


def list_approvals(conn: sqlite3.Connection, milestone_id: int) -> list[dict]:
    rows = conn.execute(
        "SELECT * FROM approvals WHERE milestone_id=? ORDER BY id",
        (milestone_id,),
    ).fetchall()
    return [_approval_row(r) for r in rows]


def _approval_blockers(conn: sqlite3.Connection, milestone_id: int) -> list[str]:
    criteria = list_criteria(conn, milestone_id)
    if not criteria:
        return ["milestone has no acceptance criteria"]
    unmet = [c for c in criteria if c["status"] != "met"]
    if unmet:
        ids = sorted(c["id"] for c in unmet)
        return [f"acceptance criteria not all met: {ids}"]
    risks = list_risks(conn, milestone_id)
    open_hot = [
        r for r in risks if r["status"] == "open" and r["exposure"] >= models.HIGH_EXPOSURE
    ]
    if open_hot:
        titles = sorted(r["title"] for r in open_hot)
        return [f"open high-exposure risks: {titles}"]
    return []


def decide_approval(conn: sqlite3.Connection, approval: Approval, role: str) -> dict:
    check("approvals", "write", role)
    approval.approver_role = role  # the acting role decides, never the payload
    _raise_if(approval.validate())
    milestone = get_milestone(conn, approval.milestone_id)
    if approval.decision == "approved":
        _raise_if(_approval_blockers(conn, approval.milestone_id))
        new_status = "approved"
    elif approval.decision == "rejected":
        new_status = "draft"
    else:  # changes_requested
        new_status = "in_progress" if milestone["status"] != "draft" else "draft"
    approval.approver_role = role
    approval.created_at = utcnow()
    cur = conn.execute(
        "INSERT INTO approvals (milestone_id, approver_role, decision, comment,"
        " created_at) VALUES (?, ?, ?, ?, ?)",
        (
            approval.milestone_id,
            approval.approver_role,
            approval.decision,
            approval.comment,
            approval.created_at,
        ),
    )
    conn.execute(
        "UPDATE milestones SET status=?, updated_at=? WHERE id=?",
        (new_status, utcnow(), approval.milestone_id),
    )
    conn.commit()
    approval.id = cur.lastrowid
    result = approval.to_dict()
    result["milestone_status"] = new_status
    return result
