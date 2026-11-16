"""Plan-as-code: scope, user roles, core modules/MVP, and delivery milestones.

Task 1 acceptance criteria (c1..c4) are encoded here as structured data so the
running API (``/api/v1/plan/*``), the UI "Plan" screen, and the test suite all
verify the same single source of truth. The markdown files under ``docs/``
are rendered views of this data for human review.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# c1: Scope and user roles
# ---------------------------------------------------------------------------
SCOPE = {
    "product": "School Management System (SchoolMS)",
    "in_scope": [
        "User accounts with role-based access control",
        "Student records and enrollment lifecycle",
        "Teacher records and class assignments",
        "Class / section scheduling and rosters",
        "Daily attendance capture and summaries",
        "Assignments, grades and report cards",
        "Fee invoices and payment tracking",
        "Dashboards and operational reports",
    ],
    "out_of_scope_mvp": [
        "Payroll and HR management",
        "Transport / bus fleet tracking",
        "Hostel / dormitory management",
        "Library catalogue and circulation",
        "Online examinations / proctoring",
        "Native mobile applications",
    ],
    "assumptions": [
        "One school (single tenant) per deployment for MVP.",
        "Academic year model with terms; MVP ships one active term.",
        "English-only UI for MVP.",
    ],
}

ROLES = {
    "admin": {
        "description": "Full system access: users, settings, all modules.",
        "permissions": ["*"],
    },
    "staff": {
        "description": "Front-office staff: admissions, fees, attendance oversight.",
        "permissions": [
            "students:read", "students:write",
            "teachers:read",
            "classes:read",
            "enrollments:read", "enrollments:write",
            "attendance:read", "attendance:write",
            "grades:read",
            "fees:read", "fees:write",
            "dashboard:read",
        ],
    },
    "teacher": {
        "description": "Takes attendance and manages grades for assigned classes.",
        "permissions": [
            "students:read",
            "teachers:read",
            "classes:read",
            "enrollments:read",
            "attendance:read", "attendance:write",
            "grades:read", "grades:write",
            "dashboard:read",
        ],
    },
    "student": {
        "description": "Views own classes, attendance, grades and fees.",
        "permissions": [
            "classes:read",
            "attendance:read:self",
            "grades:read:self",
            "fees:read:self",
            "dashboard:read",
        ],
    },
    "parent": {
        "description": "Views linked children's attendance, grades and fees.",
        "permissions": [
            "attendance:read:self",
            "grades:read:self",
            "fees:read:self",
            "dashboard:read",
        ],
    },
}

# ---------------------------------------------------------------------------
# c2: Core modules and MVP prioritisation
# ---------------------------------------------------------------------------
MODULES = [
    {"id": "users", "name": "Users & Access Control", "phase": "MVP",
     "description": "Accounts, roles, authentication (JWT), RBAC enforcement."},
    {"id": "students", "name": "Student Records", "phase": "MVP",
     "description": "Student profiles, admission, status lifecycle."},
    {"id": "teachers", "name": "Teacher Records", "phase": "MVP",
     "description": "Teacher profiles, subjects, employment status."},
    {"id": "classes", "name": "Classes & Sections", "phase": "MVP",
     "description": "Classes, sections, teacher assignment, capacity."},
    {"id": "enrollments", "name": "Enrollments", "phase": "MVP",
     "description": "Student-class enrollment with capacity validation."},
    {"id": "attendance", "name": "Attendance", "phase": "MVP",
     "description": "Daily attendance capture and per-class summaries."},
    {"id": "grades", "name": "Grades & Report Cards", "phase": "MVP",
     "description": "Assignments, scores, GPA-style averages, report cards."},
    {"id": "fees", "name": "Fees & Payments", "phase": "Phase 2",
     "description": "Fee invoices, payment recording, outstanding balances."},
    {"id": "timetable", "name": "Timetable & Scheduling", "phase": "Phase 2",
     "description": "Periods, rooms, weekly timetable generation."},
    {"id": "messaging", "name": "Messaging & Notifications", "phase": "Phase 3",
     "description": "Announcements, SMS/email notifications to parents."},
    {"id": "library", "name": "Library", "phase": "Phase 3",
     "description": "Catalogue, issue/return circulation."},
    {"id": "transport", "name": "Transport", "phase": "Phase 3",
     "description": "Routes, vehicles, ridership tracking."},
]

MVP_PRIORITY = [
    "users", "students", "teachers", "classes", "enrollments",
    "attendance", "grades",
]

# ---------------------------------------------------------------------------
# c3: Architecture and tech stack (mirrors docs/ARCHITECTURE.md)
# ---------------------------------------------------------------------------
ARCHITECTURE = {
    "style": "Modular monolith: FastAPI app with per-module routers, "
             "SQLAlchemy data layer, static single-page UI.",
    "stack": {
        "language": "Python 3.12",
        "api": "FastAPI + Starlette",
        "orm": "SQLAlchemy 2.0",
        "database": "SQLite (MVP, file-based); Postgres-compatible via SQLAlchemy URL",
        "auth": "JWT (PyJWT, HS256) + PBKDF2 password hashing (stdlib)",
        "ui": "Static HTML/CSS/vanilla JS single-page app served by the API",
        "tests": "pytest + FastAPI TestClient",
    },
    "layers": ["routers (HTTP)", "schemas (validation)", "models (ORM)",
               "security/deps (auth + RBAC)", "database (sessions)"],
}

# ---------------------------------------------------------------------------
# c4: Delivery milestones
# ---------------------------------------------------------------------------
DELIVERY_MILESTONES = [
    {"id": "M1", "name": "Foundation: plan, auth, users, roles",
     "modules": ["users"], "acceptance": "Login works; RBAC enforced; plan API live."},
    {"id": "M2", "name": "People & classes: students, teachers, classes, enrollments",
     "modules": ["students", "teachers", "classes", "enrollments"],
     "acceptance": "Rosters build end-to-end with capacity checks."},
    {"id": "M3", "name": "Daily operations: attendance, grades, dashboards",
     "modules": ["attendance", "grades"],
     "acceptance": "Attendance + grades captured; dashboards render."},
    {"id": "M4", "name": "Phase 2: fees, timetable",
     "modules": ["fees", "timetable"],
     "acceptance": "Invoices issued and paid; timetable published."},
    {"id": "M5", "name": "Phase 3: messaging, library, transport",
     "modules": ["messaging", "library", "transport"],
     "acceptance": "Notifications sent; circulation and routes tracked."},
]
