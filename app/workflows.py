"""Per-role workflow definitions with guard rails (criteria c1/c2).

Each workflow is a small state machine: ordered steps plus role-gated
actions that move an instance forward. The service layer persists
instances; this module holds the pure transition rules.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Action:
    name: str
    actor_roles: tuple[str, ...]
    from_step: str
    to_step: str
    label: str


@dataclass(frozen=True)
class Workflow:
    id: str
    title: str
    owner_role: str
    steps: tuple[str, ...]
    actions: tuple[Action, ...]
    description: str = ""

    def allowed(self, step: str, role: str) -> list[Action]:
        return [a for a in self.actions if a.from_step == step and role in a.actor_roles]

    def transition(self, step: str, action_name: str, role: str) -> str:
        for action in self.actions:
            if action.name == action_name and action.from_step == step:
                if role not in action.actor_roles:
                    raise PermissionError(
                        f"role '{role}' may not perform '{action_name}' at '{step}'"
                    )
                return action.to_step
        raise ValueError(f"unknown action '{action_name}' at step '{step}'")


WORKFLOWS: dict[str, Workflow] = {}


def _register(workflow: Workflow) -> Workflow:
    WORKFLOWS[workflow.id] = workflow
    return workflow


_register(Workflow(
    id="student-enrollment",
    title="Student enrollment",
    owner_role="student",
    description="Apply, get admitted, enroll in classes, access school services.",
    steps=("applied", "admitted", "enrolled", "active"),
    actions=(
        Action("approve-application", ("admin",), "applied", "admitted", "Approve application"),
        Action("reject-application", ("admin",), "applied", "applied", "Reject (stays applied)"),
        Action("confirm-enrollment", ("admin", "student"), "admitted", "enrolled", "Confirm enrollment"),
        Action("activate", ("admin",), "enrolled", "active", "Activate student"),
    ),
))

_register(Workflow(
    id="teacher-gradebook",
    title="Teacher gradebook cycle",
    owner_role="teacher",
    description="Teacher takes attendance then enters and publishes grades.",
    steps=("scheduled", "attendance-taken", "grades-entered", "published"),
    actions=(
        Action("take-attendance", ("teacher", "admin"), "scheduled", "attendance-taken", "Take attendance"),
        Action("enter-grades", ("teacher",), "attendance-taken", "grades-entered", "Enter grades"),
        Action("publish-grades", ("teacher", "admin"), "grades-entered", "published", "Publish grades"),
        Action("reopen", ("admin",), "published", "grades-entered", "Reopen gradebook"),
    ),
))

_register(Workflow(
    id="admin-admissions",
    title="Admin admissions pipeline",
    owner_role="admin",
    description="Admin reviews applicants, assigns classes, invoices fees.",
    steps=("applied", "under-review", "accepted", "class-assigned", "invoiced"),
    actions=(
        Action("start-review", ("admin",), "applied", "under-review", "Start review"),
        Action("accept", ("admin",), "under-review", "accepted", "Accept applicant"),
        Action("assign-class", ("admin",), "accepted", "class-assigned", "Assign class"),
        Action("invoice-fees", ("admin",), "class-assigned", "invoiced", "Invoice fees"),
    ),
))

_register(Workflow(
    id="parent-monitoring",
    title="Parent monitoring & fees",
    owner_role="parent",
    description="Parent links a child, monitors progress, pays fees.",
    steps=("unlinked", "linked", "monitoring", "fees-current"),
    actions=(
        Action("link-child", ("parent", "admin"), "unlinked", "linked", "Link child"),
        Action("start-monitoring", ("parent",), "linked", "monitoring", "Start monitoring"),
        Action("pay-fees", ("parent",), "monitoring", "fees-current", "Pay fees"),
        Action("new-invoice", ("admin",), "fees-current", "monitoring", "New invoice issued"),
    ),
))


def get(workflow_id: str) -> Workflow:
    try:
        return WORKFLOWS[workflow_id]
    except KeyError:
        raise ValueError(f"unknown workflow '{workflow_id}'") from None


def describe(workflow: Workflow) -> dict:
    return {
        "id": workflow.id,
        "title": workflow.title,
        "owner_role": workflow.owner_role,
        "description": workflow.description,
        "steps": list(workflow.steps),
        "actions": [
            {"name": a.name, "actor_roles": list(a.actor_roles),
             "from_step": a.from_step, "to_step": a.to_step, "label": a.label}
            for a in workflow.actions
        ],
    }
