"""Scope and user roles (criterion c1) as code.

SCOPE states what the MVP covers and explicitly excludes.
ROLES defines every user role, what it may do (permissions), and which
modules it touches. mvp.api enforces these permissions at runtime.
"""

SCOPE = {
    "product": "School management MVP for a single K-12 school",
    "in_scope": [
        "Student admissions pipeline (apply -> review -> admit/enroll)",
        "Daily class attendance marking and summaries",
        "Gradebook: assessments, scores, per-student averages",
        "Weekly class timetable with conflict detection",
        "Fee invoicing, recording payments, outstanding balances",
        "Announcements/messaging between staff, students, parents",
    ],
    "out_of_scope": [
        "Multi-school / district tenancy",
        "Payroll and HR",
        "Transport / fleet tracking",
        "Online examinations / proctoring",
        "Real payment-gateway settlement (payments recorded manually)",
    ],
}

# permission -> description
PERMISSIONS = {
    "admissions.apply": "Submit an admission application",
    "admissions.review": "Review / decide on applications",
    "admissions.read": "List and view applications",
    "attendance.mark": "Mark attendance for a class session",
    "attendance.read": "View attendance records and summaries",
    "grades.edit": "Create assessments and record scores",
    "grades.read": "View grades and averages",
    "timetable.edit": "Create/update timetable slots",
    "timetable.read": "View the timetable",
    "fees.invoice": "Issue fee invoices",
    "fees.collect": "Record fee payments",
    "fees.read": "View invoices, payments, balances",
    "comms.send": "Send announcements/messages",
    "comms.read": "Read announcements/messages",
    "admin.milestones": "Approve delivery milestones",
}

ROLES = {
    "admin": {
        "description": "System administrator: full access incl. milestone approval",
        "permissions": sorted(PERMISSIONS),
    },
    "admissions_officer": {
        "description": "Runs the admissions pipeline",
        "permissions": ["admissions.apply", "admissions.review", "admissions.read",
                        "comms.send", "comms.read"],
    },
    "teacher": {
        "description": "Teaches classes: attendance, grades, timetable viewing",
        "permissions": ["attendance.mark", "attendance.read", "grades.edit",
                        "grades.read", "timetable.read", "comms.send", "comms.read"],
    },
    "accountant": {
        "description": "Manages fees end to end",
        "permissions": ["fees.invoice", "fees.collect", "fees.read",
                        "comms.send", "comms.read"],
    },
    "student": {
        "description": "Enrolled student: read-only on own data surfaces",
        "permissions": ["attendance.read", "grades.read", "timetable.read",
                        "fees.read", "comms.read"],
    },
    "parent": {
        "description": "Parent/guardian: applies for admission, follows child progress",
        "permissions": ["admissions.apply", "admissions.read", "attendance.read",
                        "grades.read", "timetable.read", "fees.read",
                        "comms.send", "comms.read"],
    },
}


class PermissionDenied(Exception):
    pass


def check(role, permission):
    """Raise PermissionDenied unless *role* grants *permission*."""
    perms = ROLES.get(role, {}).get("permissions", [])
    if permission not in perms:
        raise PermissionDenied(f"role '{role}' lacks permission '{permission}'")
    return True


def roles_for(permission):
    """Return sorted roles that hold *permission*."""
    return sorted(r for r, d in ROLES.items() if permission in d["permissions"])
