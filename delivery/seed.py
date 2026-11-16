"""Seed data: a complete SchoolMS delivery plan (scope, roles, modules,
architecture, milestones, risks, criteria) used by the UI demo and tests."""
from __future__ import annotations

import sqlite3

from .config import ROLE_DESCRIPTIONS, ROLES
from .models import (
    AcceptanceCriterion,
    ArchDecision,
    Milestone,
    Module,
    Risk,
    Scope,
)
from . import service

SCOPE = Scope(
    vision=(
        "Ship a school management system that runs one school's whole term —"
        " admissions, attendance, grades, timetable, fees and communication —"
        " with role-based access for staff, students and parents."
    ),
    in_scope=[
        "Student lifecycle: enquiry, application, admission, enrolment, promotion",
        "Daily operations: attendance, grades, timetable, fees, communication",
        "Role-based access for admin, staff, students and parents",
        "Dashboards and CSV/PDF reports per term",
        "Audit trail on admissions, grades and fee waivers",
    ],
    out_of_scope=[
        "Full payroll/HR, inventory and transport GPS",
        "Online proctored examinations / CBT",
        "Native mobile apps (responsive web first)",
        "Multi-school SaaS billing in MVP",
    ],
    assumptions=[
        "One active academic session with multiple terms",
        "Each school configures its own grading scale and fee structure",
        "Staff have email; parents reachable by email or SMS",
    ],
    constraints=[
        "English-first UI, one timezone per deployment",
        "No offline-first clients in MVP (retry on brief outages)",
        "MVP serves one school; data model stays multi-branch-ready",
    ],
)

# name, description, priority, mvp, effort, status, depends_on
MODULES: list[tuple] = [
    ("Identity & RBAC", "Users, roles, login, least-privilege permissions.", "P0", True, 8, "done", []),
    ("Academic sessions", "Sessions, terms, classes, subjects, grading scales.", "P0", True, 5, "done", ["Identity & RBAC"]),
    ("Admissions", "Enquiries, applications, document checks, enrolment.", "P0", True, 13, "in_progress", ["Academic sessions"]),
    ("Attendance", "Daily registers, unmarked-register nudges.", "P0", True, 8, "planned", ["Academic sessions"]),
    ("Grades", "Grade entry, publishing, report cards.", "P0", True, 13, "planned", ["Academic sessions"]),
    ("Timetable", "Slots, class schedules, teacher assignments.", "P1", True, 8, "backlog", ["Academic sessions"]),
    ("Fees", "Fee structures, invoices, receipts, arrears.", "P0", True, 13, "backlog", ["Admissions"]),
    ("Communication", "Announcements, SMS/email/push to staff and parents.", "P1", True, 5, "backlog", ["Identity & RBAC"]),
    ("Dashboards & reports", "Principal dashboard, CSV/PDF exports.", "P1", False, 8, "backlog", ["Grades", "Attendance", "Fees"]),
    ("Payments integration", "Provider references, reconciliation.", "P2", False, 5, "backlog", ["Fees"]),
    ("Mobile apps", "Native apps reusing the public API.", "P2", False, 21, "backlog", ["Dashboards & reports"]),
]

# category, option, status, rationale
ARCH: list[tuple] = [
    ("language", "Python 3.12", "selected", "Team strength; stdlib-first keeps the MVP dependency-free."),
    ("language", "Node.js 22", "rejected", ""),
    ("framework", "Stdlib http.server + SQLite", "selected", "Zero-dependency MVP; migrates cleanly to a WSGI app later."),
    ("framework", "Django", "proposed", ""),
    ("database", "SQLite (WAL)", "selected", "Single-school MVP needs no database server; file backup is trivial."),
    ("database", "PostgreSQL", "proposed", ""),
    ("auth", "Session + RBAC matrix", "selected", "Matches the five delivery roles and ten school roles; auditable."),
    ("auth", "External OAuth only", "rejected", ""),
    ("hosting", "Single VM + file backup", "selected", "Cheapest reliable shape for one school; scales to containers later."),
    ("hosting", "Kubernetes", "rejected", ""),
    ("messaging", "SMTP + SMS gateway", "selected", "Parents reachable by email or SMS per the scope assumptions."),
    ("messaging", "Push-only", "rejected", ""),
]

# name, phase, description, start, end, status, owner
MILESTONES: list[tuple] = [
    ("M1: Scope & roles signed off", "discovery", "Vision, in/out of scope, roles and RACI agreed.",
     "2026-11-01", "2026-11-15", "approved", "product_owner"),
    ("M2: Architecture selected", "discovery", "One selected option per stack category with rationale.",
     "2026-11-10", "2026-11-25", "planned", "tech_lead"),
    ("M3: MVP core (identity, sessions, admissions)", "mvp", "A registrar can enrol a student end to end.",
     "2026-11-26", "2027-01-15", "in_progress", "tech_lead"),
    ("M4: MVP daily ops (attendance, grades, fees)", "mvp", "A school can run one full week on the system.",
     "2027-01-16", "2027-03-01", "planned", "tech_lead"),
    ("M5: Beta pilots", "beta", "Two pilot schools run a full term.",
     "2027-03-02", "2027-06-30", "draft", "product_owner"),
    ("M6: General availability", "ga", "GA rollout with dashboards and reports.",
     "2027-07-01", "2027-09-30", "draft", "product_owner"),
]

# milestone name -> [(description, verification, status)]
CRITERIA: dict[str, list[tuple]] = {
    "M1: Scope & roles signed off": [
        ("Vision and in/out-of-scope lists published", "Scope page shows vision plus both lists", "met"),
        ("Five delivery roles defined with permissions", "Roles API returns 5 roles", "met"),
    ],
    "M2: Architecture selected": [
        ("Every stack category has a selected option", "Stack summary reports decided=true", "pending"),
        ("Rejected options recorded", "Each category has a non-proposed option", "pending"),
    ],
    "M3: MVP core (identity, sessions, admissions)": [
        ("Registrar enrols a student end to end", "Seeded demo walkthrough passes", "pending"),
        ("RBAC denies cross-role actions", "RBAC test suite green", "met"),
    ],
    "M4: MVP daily ops (attendance, grades, fees)": [
        ("Attendance + grades + fees usable for one week", "Pilot checklist signed", "pending"),
    ],
}

# title, likelihood, impact, mitigation, status, milestone name | None
RISKS: list[tuple] = [
    ("Fee-structure variety across schools", "high", "high",
     "Model fee structures as school configuration, never hard-coded.", "mitigating",
     "M4: MVP daily ops (attendance, grades, fees)"),
    ("Scope creep from stakeholder requests", "high", "medium",
     "Out-of-scope list enforced at intake; changes need product-owner sign-off.", "mitigating",
     "M1: Scope & roles signed off"),
    ("SMS gateway downtime at fee deadlines", "medium", "high",
     "Queue + retry with email fallback for deadline reminders.", "open",
     "M4: MVP daily ops (attendance, grades, fees)"),
    ("Pilot data migration errors", "medium", "medium",
     "Import dry-run plus registrar sign-off before go-live.", "open",
     "M5: Beta pilots"),
    ("Single-VM hosting limits growth", "low", "medium", "", "open", None),
]


def seed(conn: sqlite3.Connection) -> dict[str, int]:
    """Seed a fresh database; returns counts per collection."""
    counts: dict[str, int] = {}
    cur = conn.execute("SELECT COUNT(*) AS n FROM roles")
    if cur.fetchone()["n"]:
        return counts  # already seeded

    for name in ROLES:
        conn.execute(
            "INSERT INTO roles (name, description) VALUES (?, ?)",
            (name, ROLE_DESCRIPTIONS[name]),
        )
    counts["roles"] = len(ROLES)

    service.save_scope(conn, SCOPE, role="admin")
    counts["scopes"] = 1

    for name, desc, prio, mvp, effort, status, deps in MODULES:
        service.create_module(
            conn,
            Module(name=name, description=desc, priority=prio, mvp=mvp,
                   effort_points=effort, status="backlog", depends_on=deps),
            role="admin",
        )
        # walk the status machine instead of jumping straight to the target
        order = ["backlog", "planned", "in_progress", "done"]
        for step in order[1:order.index(status) + 1]:
            service.update_module_status(conn, _module_id(conn, name), step, role="admin")
    counts["modules"] = len(MODULES)

    for category, option, status, rationale in ARCH:
        service.propose_arch(
            conn,
            ArchDecision(category=category, option_name=option,
                         status="proposed" if status != "selected" else "proposed"),
            role="admin",
        )
        decision_id = _arch_id(conn, category, option)
        if status == "selected":
            service.select_arch(conn, decision_id, rationale, role="admin")
        elif status == "rejected":
            service.reject_arch(conn, decision_id, role="admin")
    counts["arch"] = len(ARCH)

    for name, phase, desc, start, end, status, owner in MILESTONES:
        service.create_milestone(
            conn,
            Milestone(name=name, phase=phase, description=desc,
                      start_date=start, end_date=end, status="draft", owner_role=owner),
            role="admin",
        )
        mid = _milestone_id(conn, name)
        if status in ("planned", "in_progress", "approved"):
            service.update_milestone(conn, mid, {"status": "planned"}, role="admin")
        if status in ("in_progress", "approved"):
            service.update_milestone(conn, mid, {"status": "in_progress"}, role="admin")
    counts["milestones"] = len(MILESTONES)

    for ms_name, items in CRITERIA.items():
        mid = _milestone_id(conn, ms_name)
        for desc, verification, status in items:
            criterion = service.add_criterion(
                conn,
                AcceptanceCriterion(milestone_id=mid, description=desc,
                                    verification_method=verification),
                role="admin",
            )
            if status != "pending":
                service.set_criterion_status(conn, criterion["id"], status, role="admin")
    counts["criteria"] = sum(len(v) for v in CRITERIA.values())

    for title, likelihood, impact, mitigation, status, ms_name in RISKS:
        mid = _milestone_id(conn, ms_name) if ms_name else None
        risk = service.create_risk(
            conn,
            Risk(title=title, likelihood=likelihood, impact=impact,
                 mitigation=mitigation, status="open", milestone_id=mid),
            role="admin",
        )
        if status != "open":
            service.update_risk(conn, risk["id"], {"status": status}, role="admin")
    counts["risks"] = len(RISKS)

    # M1 is pre-approved: its criteria are met and it has no open hot risks.
    m1 = _milestone_id(conn, "M1: Scope & roles signed off")
    from .models import Approval

    service.decide_approval(
        conn,
        Approval(milestone_id=m1, approver_role="product_owner",
                 decision="approved", comment="Seeded approval"),
        role="product_owner",
    )
    counts["approvals"] = 1
    return counts


def _module_id(conn: sqlite3.Connection, name: str) -> int:
    return conn.execute("SELECT id FROM modules WHERE name=?", (name,)).fetchone()["id"]


def _arch_id(conn: sqlite3.Connection, category: str, option: str) -> int:
    return conn.execute(
        "SELECT id FROM arch_decisions WHERE category=? AND option_name=?",
        (category, option),
    ).fetchone()["id"]


def _milestone_id(conn: sqlite3.Connection, name: str) -> int:
    return conn.execute("SELECT id FROM milestones WHERE name=?", (name,)).fetchone()["id"]
