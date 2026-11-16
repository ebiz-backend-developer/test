"""Scope statement, roles, and RBAC permission matrix (criterion c1)."""
from __future__ import annotations

SCOPE = {
    "product": "SchoolMS",
    "in_scope": [
        "Student enrollment and profiles",
        "Teacher class and subject assignment",
        "Attendance capture and parent visibility",
        "Gradebook entry and report cards",
        "Fee invoicing and payment tracking",
        "Role-based access for admin, teacher, student, parent",
    ],
    "out_of_scope": [
        "Payroll processing",
        "Transport fleet GPS tracking",
        "Cafeteria point-of-sale",
    ],
    "assumptions": [
        "One deployment serves one school (multi-school later).",
        "Parents access only data of linked children.",
    ],
}

ROLES = {
    "admin": {
        "title": "Administrator",
        "description": "Manages users, admissions, classes, fees, and approvals.",
    },
    "teacher": {
        "title": "Teacher",
        "description": "Takes attendance, enters grades, manages own classes.",
    },
    "student": {
        "title": "Student",
        "description": "Views timetable, attendance, grades, and fees.",
    },
    "parent": {
        "title": "Parent",
        "description": "Monitors linked children and pays fees.",
    },
}

PERMISSIONS = {
    "users.manage": "Create/update/deactivate user accounts.",
    "admissions.review": "Review and admit applicants.",
    "classes.assign": "Assign teachers and students to classes.",
    "attendance.take": "Record attendance for a class session.",
    "attendance.view": "View attendance records.",
    "grades.enter": "Enter and edit grades.",
    "grades.view": "View grades and report cards.",
    "fees.invoice": "Issue fee invoices.",
    "fees.pay": "Pay fee invoices.",
    "milestones.approve": "Approve delivery milestones.",
}

ROLE_PERMISSIONS = {
    "admin": [
        "users.manage", "admissions.review", "classes.assign",
        "attendance.take", "attendance.view",
        "grades.enter", "grades.view",
        "fees.invoice", "fees.pay", "milestones.approve",
    ],
    "teacher": ["attendance.take", "attendance.view", "grades.enter", "grades.view"],
    "student": ["attendance.view", "grades.view", "fees.pay"],
    "parent": ["attendance.view", "grades.view", "fees.pay", "milestones.approve"],
}

STAKEHOLDERS = [
    {"id": "st-admin", "name": "School office", "role": "admin",
     "interest": "Runs admissions, staffing, fees; approves milestones."},
    {"id": "st-teacher", "name": "Teaching staff", "role": "teacher",
     "interest": "Needs fast attendance and gradebook entry."},
    {"id": "st-student", "name": "Students", "role": "student",
     "interest": "Needs timetable, grades, and fee visibility."},
    {"id": "st-parent", "name": "Parents / guardians", "role": "parent",
     "interest": "Needs child progress visibility and fee payment."},
]


def can(role: str, permission: str) -> bool:
    """Return True when *role* is granted *permission*."""
    return permission in ROLE_PERMISSIONS.get(role, [])


def permissions_for(role: str) -> list[str]:
    """Return the sorted permission list for *role* (unknown role -> [])."""
    return sorted(ROLE_PERMISSIONS.get(role, []))
