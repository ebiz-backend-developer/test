"""Role-based access control for the school requirements service (c1).

Roles are the school user roles; actions gate every mutating API call.
Deny by default: unknown roles and unknown actions get no access.
"""
from __future__ import annotations

PERMISSIONS: dict[str, tuple[str, ...]] = {
    # c1: scope / stakeholders / roles administration
    "scope.write": ("sysadmin", "principal", "office_staff"),
    "stakeholders.write": ("sysadmin", "principal"),
    "users.write": ("sysadmin", "principal", "office_staff"),
    # c1: workflow execution (each step further narrows to its own roles)
    "workflows.manage": ("sysadmin", "principal"),
    "workflows.run": (
        "sysadmin", "principal", "registrar", "teacher", "class_teacher",
        "accountant", "office_staff", "student", "parent",
    ),
    # c2: modules & MVP prioritization
    "modules.write": ("sysadmin", "principal"),
    "modules.status": ("sysadmin", "principal", "registrar", "accountant"),
    # c3: architecture & tech stack selection
    "tech.propose": (
        "sysadmin", "principal", "registrar", "teacher", "accountant",
        "office_staff", "it_support",
    ),
    "tech.select": ("sysadmin", "principal"),
    # c4: delivery milestones & approvals
    "milestones.propose": ("sysadmin", "principal", "registrar", "accountant"),
    "milestones.approve": ("sysadmin", "principal"),
    "milestones.track": (
        "sysadmin", "principal", "registrar", "accountant", "office_staff",
    ),
}

ROLE_DESCRIPTIONS: dict[str, str] = {
    "sysadmin": "System administrator: users, roles, school setup, audit, backups.",
    "principal": "Head of school: approvals, dashboards, reports, announcements.",
    "registrar": "Admissions officer: enquiries, applications, admissions, enrolment.",
    "teacher": "Teaching staff: attendance, grades, timetable, parent contact.",
    "class_teacher": "Form tutor: owns class attendance, comments, parent contact.",
    "accountant": "Bursar: fee structures, invoices, receipts, arrears.",
    "office_staff": "Front office: data entry, certificates, corrections.",
    "student": "Pupil: timetable, homework, grades, dues view, announcements.",
    "parent": "Guardian: ward attendance, grades, dues, messaging (scoped to wards).",
    "it_support": "IT support: provisioning help, read-only diagnostics.",
}


def role_permissions(role: str | None) -> list[str]:
    """Return the sorted action list granted to a role."""
    if role is None:
        return []
    return sorted(a for a, roles in PERMISSIONS.items() if role in roles)


def can(role: str | None, action: str) -> bool:
    """Return True when the role may perform the action."""
    if role is None:
        return False
    return role in PERMISSIONS.get(action, ())


def known_role(role: str | None) -> bool:
    return role in ROLE_DESCRIPTIONS
