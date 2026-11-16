"""Service layer: real behavior for scope, roles, workflows, MVP, stack, milestones."""
from __future__ import annotations

import json

from . import rbac
from .models import Workflow, WorkflowStep
from .store import Store, utcnow


class ServiceError(Exception):
    """Domain failure with an HTTP-style status code."""

    def __init__(self, message: str, status: int = 400):
        super().__init__(message)
        self.status = status


def _require(role: str | None, action: str) -> None:
    if not rbac.can(role, action):
        raise ServiceError(f"role '{role}' may not perform '{action}'", 403)


def _audit(store: Store, actor: str, role: str, action: str,
           entity: str, entity_id: str = "",
           before: dict | None = None, after: dict | None = None) -> None:
    store.execute(
        "INSERT INTO audit (actor, role, action, entity, entity_id,"
        " before_json, after_json, created_at)"
        " VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (actor, role or "", action, entity, entity_id,
         json.dumps(before or {}), json.dumps(after or {}), utcnow()),
    )


# ---------------------------------------------------------------- c1: scope
SCOPE_KINDS = ("in_scope", "out_of_scope", "assumption", "constraint")


def list_scope(store: Store, kind: str | None = None) -> list[dict]:
    if kind:
        if kind not in SCOPE_KINDS:
            raise ServiceError(f"unknown scope kind '{kind}'")
        return store.query(
            "SELECT * FROM scope_items WHERE kind = ? ORDER BY id", (kind,))
    return store.query("SELECT * FROM scope_items ORDER BY id")


def add_scope_item(store: Store, actor: str, role: str | None,
                   kind: str, title: str, detail: str = "") -> dict:
    _require(role, "scope.write")
    if kind not in SCOPE_KINDS:
        raise ServiceError(f"unknown scope kind '{kind}'")
    if not title.strip():
        raise ServiceError("scope title is required")
    item_id = store.execute(
        "INSERT INTO scope_items (kind, title, detail) VALUES (?, ?, ?)",
        (kind, title.strip(), detail.strip()),
    )
    item = store.query_one("SELECT * FROM scope_items WHERE id = ?", (item_id,))
    _audit(store, actor, role or "", "scope.add", "scope_item",
           str(item_id), None, item)
    return item or {}


def list_stakeholders(store: Store) -> list[dict]:
    return store.query("SELECT * FROM stakeholders ORDER BY code")


def update_stakeholder(store: Store, actor: str, role: str | None,
                       code: str, **fields: str) -> dict:
    _require(role, "stakeholders.write")
    current = store.query_one(
        "SELECT * FROM stakeholders WHERE code = ?", (code,))
    if current is None:
        raise ServiceError(f"unknown stakeholder '{code}'", 404)
    allowed = {"label", "interest", "primary_role", "journey_ref"}
    updates = {k: v for k, v in fields.items() if k in allowed}
    if "primary_role" in updates and not rbac.known_role(updates["primary_role"]):
        raise ServiceError(f"unknown role '{updates['primary_role']}'")
    if updates:
        assignments = ", ".join(f"{k} = ?" for k in updates)
        with store.conn:
            store.conn.execute(
                f"UPDATE stakeholders SET {assignments} WHERE code = ?",
                (*updates.values(), code),
            )
    updated = store.query_one(
        "SELECT * FROM stakeholders WHERE code = ?", (code,))
    _audit(store, actor, role or "", "stakeholders.update", "stakeholder",
           code, current, updated)
    return updated or {}


def list_roles(store: Store) -> list[dict]:
    roles = store.query("SELECT * FROM roles ORDER BY code")
    for row in roles:
        row["permissions"] = rbac.role_permissions(row["code"])
    return roles


def role_detail(store: Store, code: str) -> dict:
    row = store.query_one("SELECT * FROM roles WHERE code = ?", (code,))
    if row is None:
        raise ServiceError(f"unknown role '{code}'", 404)
    row["permissions"] = rbac.role_permissions(code)
    row["workflows"] = [
        w["code"] for w in
        store.query("SELECT code FROM workflows WHERE role = ? ORDER BY code",
                    (code,))
    ]
    return row


# ------------------------------------------------------- c1: workflow engine
def list_workflows(store: Store) -> list[dict]:
    flows = store.query("SELECT * FROM workflows ORDER BY code")
    for flow in flows:
        flow["step_count"] = store.query_one(
            "SELECT COUNT(*) AS n FROM workflow_steps WHERE workflow_code = ?",
            (flow["code"],))["n"]
    return flows


def get_workflow(store: Store, code: str) -> Workflow:
    row = store.query_one("SELECT * FROM workflows WHERE code = ?", (code,))
    if row is None:
        raise ServiceError(f"unknown workflow '{code}'", 404)
    steps = [
        WorkflowStep.from_row(r) for r in store.query(
            "SELECT * FROM workflow_steps WHERE workflow_code = ?"
            " ORDER BY position", (code,))
    ]
    return Workflow(code=row["code"], role=row["role"], title=row["title"],
                    description=row.get("description", ""), steps=steps)


def workflow_payload(store: Store, code: str) -> dict:
    flow = get_workflow(store, code)
    return {
        "code": flow.code, "role": flow.role, "title": flow.title,
        "description": flow.description,
        "steps": [
            {"position": s.position, "module": s.module, "title": s.title,
             "detail": s.detail, "allowed_roles": s.allowed_roles,
             "required_action": s.required_action, "gate": s.gate}
            for s in flow.steps
        ],
    }


def start_instance(store: Store, actor: str, role: str | None,
                   workflow_code: str) -> dict:
    _require(role, "workflows.run")
    flow = get_workflow(store, workflow_code)
    if not flow.steps:
        raise ServiceError(f"workflow '{workflow_code}' has no steps")
    first = flow.steps[0]
    if first.allowed_roles and role not in first.allowed_roles:
        raise ServiceError(
            f"role '{role}' may not start workflow '{workflow_code}'", 403)
    now = utcnow()
    instance_id = store.execute(
        "INSERT INTO workflow_instances (workflow_code, actor, status,"
        " current_position, created_at, updated_at)"
        " VALUES (?, ?, 'open', 1, ?, ?)",
        (workflow_code, actor, now, now),
    )
    store.execute(
        "INSERT INTO workflow_events (instance_id, actor, role, from_position,"
        " to_position, note, created_at) VALUES (?, ?, ?, 0, 1, ?, ?)",
        (instance_id, actor, role or "", "started", now),
    )
    return get_instance(store, instance_id)


def get_instance(store: Store, instance_id: int) -> dict:
    inst = store.query_one(
        "SELECT * FROM workflow_instances WHERE id = ?", (instance_id,))
    if inst is None:
        raise ServiceError(f"unknown workflow instance {instance_id}", 404)
    inst["events"] = store.query(
        "SELECT * FROM workflow_events WHERE instance_id = ? ORDER BY id",
        (instance_id,))
    total = store.query_one(
        "SELECT COUNT(*) AS n FROM workflow_steps WHERE workflow_code = ?",
        (inst["workflow_code"],))["n"]
    inst["total_steps"] = total
    return inst


def advance_instance(store: Store, actor: str, role: str | None,
                     instance_id: int, note: str = "") -> dict:
    _require(role, "workflows.run")
    inst = store.query_one(
        "SELECT * FROM workflow_instances WHERE id = ?", (instance_id,))
    if inst is None:
        raise ServiceError(f"unknown workflow instance {instance_id}", 404)
    if inst["status"] != "open":
        raise ServiceError(
            f"instance {instance_id} is {inst['status']}; only open"
            " instances advance")
    flow = get_workflow(store, inst["workflow_code"])
    current = next(
        (s for s in flow.steps if s.position == inst["current_position"]), None)
    if current is None:
        raise ServiceError("instance points past the final step")
    if current.allowed_roles and role not in current.allowed_roles:
        raise ServiceError(
            f"role '{role}' may not complete step {current.position}"
            f" '{current.title}'", 403)
    if current.required_action and not rbac.can(role, current.required_action):
        raise ServiceError(
            f"step {current.position} requires action"
            f" '{current.required_action}'", 403)
    is_last = inst["current_position"] >= len(flow.steps)
    new_position = inst["current_position"] + 1
    new_status = "completed" if is_last else "open"
    now = utcnow()
    with store.conn:
        store.conn.execute(
            "UPDATE workflow_instances SET current_position = ?, status = ?,"
            " updated_at = ? WHERE id = ?",
            (new_position if not is_last else inst["current_position"],
             new_status, now, instance_id),
        )
        store.conn.execute(
            "INSERT INTO workflow_events (instance_id, actor, role,"
            " from_position, to_position, note, created_at)"
            " VALUES (?, ?, ?, ?, ?, ?, ?)",
            (instance_id, actor, role or "", inst["current_position"],
             new_position, note or f"completed: {current.title}", now),
        )
    _audit(store, actor, role or "", "workflows.advance",
           "workflow_instance", str(instance_id),
           {"position": inst["current_position"], "status": inst["status"]},
           {"position": new_position, "status": new_status})
    return get_instance(store, instance_id)


def cancel_instance(store: Store, actor: str, role: str | None,
                    instance_id: int, note: str = "") -> dict:
    _require(role, "workflows.run")
    inst = store.query_one(
        "SELECT * FROM workflow_instances WHERE id = ?", (instance_id,))
    if inst is None:
        raise ServiceError(f"unknown workflow instance {instance_id}", 404)
    if inst["status"] != "open":
        raise ServiceError(f"instance {instance_id} is already {inst['status']}")
    now = utcnow()
    with store.conn:
        store.conn.execute(
            "UPDATE workflow_instances SET status = 'cancelled',"
            " updated_at = ? WHERE id = ?",
            (now, instance_id),
        )
        store.conn.execute(
            "INSERT INTO workflow_events (instance_id, actor, role,"
            " from_position, to_position, note, created_at)"
            " VALUES (?, ?, ?, ?, ?, ?, ?)",
            (instance_id, actor, role or "", inst["current_position"],
             inst["current_position"], note or "cancelled", now),
        )
    return get_instance(store, instance_id)


def list_instances(store: Store, workflow_code: str | None = None,
                   status: str | None = None) -> list[dict]:
    sql = "SELECT * FROM workflow_instances"
    clauses: list = []
    params: list = []
    if workflow_code:
        clauses.append("workflow_code = ?")
        params.append(workflow_code)
    if status:
        if status not in ("open", "completed", "cancelled"):
            raise ServiceError(f"unknown status '{status}'")
        clauses.append("status = ?")
        params.append(status)
    if clauses:
        sql += " WHERE " + " AND ".join(clauses)
    return store.query(sql + " ORDER BY id", tuple(params))


# --------------------------------------------------- c2: modules & MVP slice
PRIORITIES = ("P0", "P1", "P2")
MODULE_STATUSES = ("planned", "in_progress", "done")


def list_modules(store: Store) -> list[dict]:
    return store.query("SELECT * FROM modules ORDER BY position, code")


def mvp_modules(store: Store) -> list[dict]:
    return store.query(
        "SELECT * FROM modules WHERE priority = 'P0' ORDER BY position, code")


def mvp_summary(store: Store) -> dict:
    modules = mvp_modules(store)
    done = sum(1 for m in modules if m["status"] == "done")
    return {
        "modules": modules,
        "total": len(modules),
        "done": done,
        "complete": bool(modules) and done == len(modules),
        "exit_rule": (
            "A school can admit students, run a term (attendance + grades +"
            " report cards), bill and collect fees, and message parents —"
            " with audit coverage — using only this slice."
        ),
    }


def update_module(store: Store, actor: str, role: str | None,
                  code: str, priority: str | None = None,
                  status: str | None = None) -> dict:
    current = store.query_one("SELECT * FROM modules WHERE code = ?", (code,))
    if current is None:
        raise ServiceError(f"unknown module '{code}'", 404)
    if priority is not None:
        _require(role, "modules.write")
        if priority not in PRIORITIES:
            raise ServiceError(f"unknown priority '{priority}'")
    if status is not None:
        _require(role, "modules.status")
        if status not in MODULE_STATUSES:
            raise ServiceError(f"unknown status '{status}'")
    if priority is None and status is None:
        raise ServiceError("nothing to update: give priority and/or status")
    with store.conn:
        if priority is not None:
            phase = {"P0": "MVP", "P1": "Phase 2", "P2": "Phase 3"}[priority]
            store.conn.execute(
                "UPDATE modules SET priority = ?, phase = ? WHERE code = ?",
                (priority, phase, code),
            )
        if status is not None:
            store.conn.execute(
                "UPDATE modules SET status = ? WHERE code = ?", (status, code))
    updated = store.query_one("SELECT * FROM modules WHERE code = ?", (code,))
    _audit(store, actor, role or "", "modules.update", "module",
           code, current, updated)
    return updated or {}


# ------------------------------------------------- c3: architecture & stack
TECH_STATUSES = ("proposed", "selected", "rejected")


def list_tech(store: Store, category: str | None = None,
              status: str | None = None) -> list[dict]:
    sql = "SELECT * FROM tech_options"
    clauses, params = [], []
    if category:
        clauses.append("category = ?")
        params.append(category)
    if status:
        if status not in TECH_STATUSES:
            raise ServiceError(f"unknown tech status '{status}'")
        clauses.append("status = ?")
        params.append(status)
    if clauses:
        sql += " WHERE " + " AND ".join(clauses)
    return store.query(sql + " ORDER BY category, name", tuple(params))


def selected_stack(store: Store) -> list[dict]:
    return list_tech(store, status="selected")


def propose_tech(store: Store, actor: str, role: str | None, category: str,
                 name: str, detail: str = "",
                 rationale: str = "") -> dict:
    _require(role, "tech.propose")
    if not category.strip() or not name.strip():
        raise ServiceError("tech category and name are required")
    if store.query_one(
            "SELECT id FROM tech_options WHERE category = ? AND name = ?",
            (category.strip(), name.strip())):
        raise ServiceError(
            f"'{name.strip()}' already proposed for '{category.strip()}'")
    option_id = store.execute(
        "INSERT INTO tech_options (category, name, detail, status, rationale,"
        " proposed_by) VALUES (?, ?, ?, 'proposed', ?, ?)",
        (category.strip(), name.strip(), detail.strip(), rationale.strip(),
         actor),
    )
    option = store.query_one(
        "SELECT * FROM tech_options WHERE id = ?", (option_id,))
    _audit(store, actor, role or "", "tech.propose", "tech_option",
           str(option_id), None, option)
    return option or {}


def select_tech(store: Store, actor: str, role: str | None, option_id: int,
                rationale: str = "") -> dict:
    _require(role, "tech.select")
    current = store.query_one(
        "SELECT * FROM tech_options WHERE id = ?", (option_id,))
    if current is None:
        raise ServiceError(f"unknown tech option {option_id}", 404)
    if current["status"] == "rejected":
        raise ServiceError("a rejected option cannot be selected"
                           " — propose it again under a new entry")
    with store.conn:
        store.conn.execute(
            "UPDATE tech_options SET status = 'rejected',"
            " rationale = 'superseded by ' || ?"
            " WHERE category = ? AND status = 'selected' AND id != ?",
            (current["name"], current["category"], option_id),
        )
        store.conn.execute(
            "UPDATE tech_options SET status = 'selected', rationale = ?"
            " WHERE id = ?",
            (rationale.strip() or current["rationale"], option_id),
        )
    updated = store.query_one(
        "SELECT * FROM tech_options WHERE id = ?", (option_id,))
    _audit(store, actor, role or "", "tech.select", "tech_option",
           str(option_id), current, updated)
    return updated or {}


def reject_tech(store: Store, actor: str, role: str | None, option_id: int,
                rationale: str = "") -> dict:
    _require(role, "tech.select")
    current = store.query_one(
        "SELECT * FROM tech_options WHERE id = ?", (option_id,))
    if current is None:
        raise ServiceError(f"unknown tech option {option_id}", 404)
    if current["status"] == "selected":
        raise ServiceError("a selected option cannot be rejected outright —"
                           " select its replacement instead")
    with store.conn:
        store.conn.execute(
            "UPDATE tech_options SET status = 'rejected', rationale = ?"
            " WHERE id = ?",
            (rationale.strip() or current["rationale"], option_id),
        )
    updated = store.query_one(
        "SELECT * FROM tech_options WHERE id = ?", (option_id,))
    _audit(store, actor, role or "", "tech.reject", "tech_option",
           str(option_id), current, updated)
    return updated or {}


# -------------------------------------------------- c4: milestones & approval
MILESTONE_FLOW = ("proposed", "approved", "in_progress", "done")


def list_milestones(store: Store) -> list[dict]:
    milestones = store.query("SELECT * FROM milestones ORDER BY position, code")
    for milestone in milestones:
        milestone["approvals"] = store.query(
            "SELECT * FROM approvals WHERE milestone_code = ? ORDER BY id",
            (milestone["code"],))
    return milestones


def propose_milestone(store: Store, actor: str, role: str | None, code: str,
                      title: str, goal: str = "",
                      exit_criteria: str = "") -> dict:
    _require(role, "milestones.propose")
    code = code.strip().upper()
    if not code or not title.strip():
        raise ServiceError("milestone code and title are required")
    if store.query_one("SELECT code FROM milestones WHERE code = ?", (code,)):
        raise ServiceError(f"milestone '{code}' already exists")
    position = store.query_one(
        "SELECT COALESCE(MAX(position), -1) + 1 AS n FROM milestones")["n"]
    store.execute(
        "INSERT INTO milestones (code, title, goal, exit_criteria, status,"
        " proposed_by, position) VALUES (?, ?, ?, ?, 'proposed', ?, ?)",
        (code, title.strip(), goal.strip(), exit_criteria.strip(), actor,
         position),
    )
    milestone = store.query_one(
        "SELECT * FROM milestones WHERE code = ?", (code,))
    _audit(store, actor, role or "", "milestones.propose", "milestone",
           code, None, milestone)
    return milestone or {}


def decide_milestone(store: Store, actor: str, role: str | None, code: str,
                     decision: str, note: str = "") -> dict:
    _require(role, "milestones.approve")
    if decision not in ("approved", "rejected"):
        raise ServiceError("decision must be 'approved' or 'rejected'")
    current = store.query_one(
        "SELECT * FROM milestones WHERE code = ?", (code,))
    if current is None:
        raise ServiceError(f"unknown milestone '{code}'", 404)
    if current["status"] != "proposed":
        raise ServiceError(
            f"milestone '{code}' is {current['status']}; only proposed"
            " milestones can be decided")
    if decision == "rejected" and not note.strip():
        raise ServiceError("a rejection needs a note explaining why")
    now = utcnow()
    with store.conn:
        store.conn.execute(
            "UPDATE milestones SET status = ?, approved_by = ?, approved_at = ?"
            " WHERE code = ?",
            (decision, actor, now, code),
        )
        store.conn.execute(
            "INSERT INTO approvals (milestone_code, actor, role, decision,"
            " note, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (code, actor, role or "", decision, note.strip(), now),
        )
    updated = store.query_one(
        "SELECT * FROM milestones WHERE code = ?", (code,))
    _audit(store, actor, role or "", f"milestones.{decision}", "milestone",
           code, current, updated)
    return updated or {}


def track_milestone(store: Store, actor: str, role: str | None, code: str,
                    status: str) -> dict:
    _require(role, "milestones.track")
    if status not in ("in_progress", "done"):
        raise ServiceError("tracking status must be 'in_progress' or 'done'")
    current = store.query_one(
        "SELECT * FROM milestones WHERE code = ?", (code,))
    if current is None:
        raise ServiceError(f"unknown milestone '{code}'", 404)
    order = {name: index for index, name in enumerate(MILESTONE_FLOW)}
    if current["status"] not in order:
        raise ServiceError(
            f"milestone '{code}' is {current['status']}; only approved"
            " milestones can be tracked")
    if order[status] != order[current["status"]] + 1:
        raise ServiceError(
            f"milestone '{code}' cannot move from {current['status']}"
            f" to {status}")
    with store.conn:
        store.conn.execute(
            "UPDATE milestones SET status = ? WHERE code = ?", (status, code))
    updated = store.query_one(
        "SELECT * FROM milestones WHERE code = ?", (code,))
    _audit(store, actor, role or "", "milestones.track", "milestone",
           code, current, updated)
    return updated or {}


# ------------------------------------------------------------------ subjects
def list_users(store: Store) -> list[dict]:
    return store.query("SELECT * FROM users ORDER BY id")


def add_user(store: Store, actor: str, role: str | None, name: str,
             email: str, user_role: str) -> dict:
    _require(role, "users.write")
    if not name.strip() or not email.strip():
        raise ServiceError("user name and email are required")
    if not rbac.known_role(user_role):
        raise ServiceError(f"unknown role '{user_role}'")
    try:
        user_id = store.execute(
            "INSERT INTO users (name, email, role) VALUES (?, ?, ?)",
            (name.strip(), email.strip().lower(), user_role),
        )
    except Exception as exc:
        raise ServiceError(f"cannot add user: {exc}") from exc
    user = store.query_one("SELECT * FROM users WHERE id = ?", (user_id,))
    _audit(store, actor, role or "", "users.add", "user",
           str(user_id), None, user)
    return user or {}


def list_audit(store: Store, limit: int = 100) -> list[dict]:
    return store.query(
        "SELECT * FROM audit ORDER BY id DESC LIMIT ?", (max(1, min(limit, 500)),))

