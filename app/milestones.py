"""Delivery milestones with stakeholder approval gates (criterion c4)."""
from __future__ import annotations

REQUIRED_APPROVER_ROLES = ("admin", "parent")

MILESTONES = [
    {"id": "M1", "title": "Foundation & access", "due_week": 2,
     "goal": "Users, roles, RBAC, admissions skeleton live."},
    {"id": "M2", "title": "Daily school loop", "due_week": 4,
     "goal": "Attendance and timetable usable by teachers daily."},
    {"id": "M3", "title": "Grades & reports", "due_week": 6,
     "goal": "Gradebook entry, publishing, parent-visible reports."},
    {"id": "M4", "title": "Fees & communication", "due_week": 8,
     "goal": "Invoicing, parent payments, announcements."},
    {"id": "M5", "title": "Dashboards & hardening", "due_week": 10,
     "goal": "Role dashboards, backups, pilot readiness."},
]

STATUSES = ("draft", "proposed", "approved")


def next_status(current: str, approvals: set[str]) -> str:
    """Derive milestone status from current status and approving roles."""
    if current not in STATUSES:
        raise ValueError(f"unknown status '{current}'")
    if set(REQUIRED_APPROVER_ROLES) <= set(approvals):
        return "approved"
    if approvals:
        return "proposed"
    return "draft"
