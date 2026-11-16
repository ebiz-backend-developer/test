"""Core modules and MVP prioritization (criterion c2) as code.

Each module has a priority (P0 must-have for MVP, P1 MVP-nice, P2 post-MVP),
an MVP feature slice, and the API resources it serves. The API exposes this
at GET /api/modules so prioritization is runtime data.
"""

MODULES = [
    {
        "id": "admissions",
        "name": "Admissions",
        "priority": "P0",
        "mvp": True,
        "summary": "Application intake, review workflow, admission decisions.",
        "mvp_features": ["submit application", "list/review applications",
                         "admit / waitlist / reject decision"],
        "post_mvp": ["document upload", "online entrance exams"],
        "resources": ["applications"],
    },
    {
        "id": "attendance",
        "name": "Attendance",
        "priority": "P0",
        "mvp": True,
        "summary": "Daily per-student attendance marking and summaries.",
        "mvp_features": ["mark present/absent/late per class-date",
                         "per-student attendance summary"],
        "post_mvp": ["biometric capture", "truancy alerts"],
        "resources": ["attendance"],
    },
    {
        "id": "grades",
        "name": "Grades",
        "priority": "P0",
        "mvp": True,
        "summary": "Assessments, scores, per-student averages.",
        "mvp_features": ["create assessment", "record scores",
                         "per-student average"],
        "post_mvp": ["report-card PDFs", "GPA / transcripts"],
        "resources": ["assessments", "scores"],
    },
    {
        "id": "timetable",
        "name": "Timetable",
        "priority": "P0",
        "mvp": True,
        "summary": "Weekly class schedule with room/teacher conflict detection.",
        "mvp_features": ["weekly slots per class", "teacher/room clash detection"],
        "post_mvp": ["auto-scheduling optimizer", "substitute management"],
        "resources": ["slots"],
    },
    {
        "id": "fees",
        "name": "Fees",
        "priority": "P0",
        "mvp": True,
        "summary": "Invoices, payment recording, outstanding balances.",
        "mvp_features": ["issue invoice", "record payment", "balance per student"],
        "post_mvp": ["payment-gateway integration", "dunning automation"],
        "resources": ["invoices", "payments"],
    },
    {
        "id": "communication",
        "name": "Communication",
        "priority": "P1",
        "mvp": True,
        "summary": "Announcements and direct messages between roles.",
        "mvp_features": ["broadcast announcement", "direct message", "inbox"],
        "post_mvp": ["SMS/push delivery", "parent-teacher meeting scheduler"],
        "resources": ["messages"],
    },
]

PRIORITY_ORDER = {"P0": 0, "P1": 1, "P2": 2}


def ordered_modules():
    return sorted(MODULES, key=lambda m: (PRIORITY_ORDER[m["priority"]], m["id"]))


def mvp_modules():
    return [m for m in ordered_modules() if m["mvp"]]


def get_module(module_id):
    for m in MODULES:
        if m["id"] == module_id:
            return m
    raise KeyError(f"unknown module: {module_id}")
