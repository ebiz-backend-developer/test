"""Service layer: RBAC checks, workflow runtime, modules, milestones."""
from __future__ import annotations

import json

from . import milestones as ms
from . import modules as mods
from . import rbac
from . import techstack
from . import workflows as wf
from .store import Store


class Service:
    def __init__(self, store: Store) -> None:
        self.store = store
        self.db = store.conn

    # ---- c1: scope & roles ----

    def scope(self) -> dict:
        return rbac.SCOPE

    def roles(self) -> list[dict]:
        out = []
        for name, meta in rbac.ROLES.items():
            out.append({"name": name, "title": meta["title"],
                        "description": meta["description"],
                        "permissions": rbac.permissions_for(name)})
        return out

    def check_access(self, role: str, permission: str) -> dict:
        if role not in rbac.ROLES:
            raise ValueError(f"unknown role '{role}'")
        if permission not in rbac.PERMISSIONS:
            raise ValueError(f"unknown permission '{permission}'")
        return {"role": role, "permission": permission,
                "allowed": rbac.can(role, permission)}

    def stakeholders(self) -> list[dict]:
        return [dict(r) for r in self.db.execute(
            "SELECT id, name, role, interest FROM stakeholders ORDER BY id")]

    # ---- workflows (student / teacher / admin / parent) ----

    def workflow_list(self) -> list[dict]:
        return [wf.describe(w) for w in wf.WORKFLOWS.values()]

    def workflow_get(self, workflow_id: str) -> dict:
        return wf.describe(wf.get(workflow_id))

    def instance_start(self, workflow_id: str, subject: str) -> dict:
        flow = wf.get(workflow_id)
        if not subject.strip():
            raise ValueError("subject is required")
        cur = self.db.execute(
            "INSERT INTO workflow_instances (workflow_id, subject, current_step)"
            " VALUES (?, ?, ?)", (flow.id, subject.strip(), flow.steps[0]))
        self.db.commit()
        return self.instance_get(cur.lastrowid)

    def instance_get(self, instance_id: int) -> dict:
        row = self.db.execute(
            "SELECT * FROM workflow_instances WHERE id = ?", (instance_id,)).fetchone()
        if row is None:
            raise LookupError(f"unknown workflow instance {instance_id}")
        inst = dict(row)
        flow = wf.get(inst["workflow_id"])
        inst["is_final"] = inst["current_step"] == flow.steps[-1]
        inst["events"] = [dict(r) for r in self.db.execute(
            "SELECT * FROM workflow_events WHERE instance_id = ? ORDER BY id",
            (instance_id,))]
        return inst

    def instance_advance(self, instance_id: int, action: str, actor_role: str) -> dict:
        if actor_role not in rbac.ROLES:
            raise ValueError(f"unknown role '{actor_role}'")
        inst = self.instance_get(instance_id)
        flow = wf.get(inst["workflow_id"])
        to_step = flow.transition(inst["current_step"], action, actor_role)
        self.db.execute(
            "INSERT INTO workflow_events (instance_id, actor_role, action, from_step, to_step)"
            " VALUES (?, ?, ?, ?, ?)",
            (instance_id, actor_role, action, inst["current_step"], to_step))
        status = "complete" if to_step == flow.steps[-1] else "open"
        self.db.execute(
            "UPDATE workflow_instances SET current_step = ?, status = ?,"
            " updated_at = datetime('now') WHERE id = ?",
            (to_step, status, instance_id))
        self.db.commit()
        return self.instance_get(instance_id)

    # ---- c2: modules & MVP ----

    def modules(self) -> list[dict]:
        rows = self.db.execute("SELECT * FROM modules ORDER BY priority, id").fetchall()
        out = []
        for r in rows:
            m = dict(r)
            m["depends_on"] = json.loads(m["depends_on"])
            out.append(m)
        return out

    def mvp(self) -> list[dict]:
        return mods.mvp_modules(self.modules())

    def set_module_priority(self, module_id: str, priority: int) -> dict:
        current = self.modules()
        updated = mods.set_priority(current, module_id, priority)
        self.db.execute("UPDATE modules SET priority = ? WHERE id = ?",
                        (priority, module_id))
        self.db.commit()
        return updated

    # ---- c3: architecture & stack ----

    def architecture(self) -> dict:
        return techstack.summary()

    # ---- c4: milestones ----

    def milestones(self) -> list[dict]:
        out = []
        for r in self.db.execute("SELECT * FROM milestones ORDER BY due_week, id"):
            m = dict(r)
            m["approvals"] = [dict(a) for a in self.db.execute(
                "SELECT role, approver, approved_at FROM milestone_approvals"
                " WHERE milestone_id = ? ORDER BY role", (m["id"],))]
            out.append(m)
        return out

    def approve_milestone(self, milestone_id: str, role: str, approver: str) -> dict:
        if role not in ms.REQUIRED_APPROVER_ROLES:
            raise PermissionError(
                f"role '{role}' cannot approve milestones;"
                f" required: {list(ms.REQUIRED_APPROVER_ROLES)}")
        if not rbac.can(role, "milestones.approve"):
            raise PermissionError(f"role '{role}' lacks milestones.approve")
        if not approver.strip():
            raise ValueError("approver is required")
        row = self.db.execute("SELECT * FROM milestones WHERE id = ?",
                              (milestone_id,)).fetchone()
        if row is None:
            raise LookupError(f"unknown milestone '{milestone_id}'")
        self.db.execute(
            "INSERT OR REPLACE INTO milestone_approvals (milestone_id, role, approver)"
            " VALUES (?, ?, ?)", (milestone_id, role, approver.strip()))
        roles = {r[0] for r in self.db.execute(
            "SELECT role FROM milestone_approvals WHERE milestone_id = ?",
            (milestone_id,))}
        status = ms.next_status(dict(row)["status"], roles)
        self.db.execute("UPDATE milestones SET status = ? WHERE id = ?",
                        (status, milestone_id))
        self.db.commit()
        return next(m for m in self.milestones() if m["id"] == milestone_id)
