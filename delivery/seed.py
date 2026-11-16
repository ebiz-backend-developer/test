"""Seed data: the initial delivery plan (phases, timeline, risks, criteria).

Seeding is additive and idempotent: it only fills tables that are empty, so it
never overwrites user edits or reseeds a live database.
"""
from __future__ import annotations

import sqlite3

from . import models, service
from .models import (
    AcceptanceCriterion,
    Approval,
    ArchDecision,
    Milestone,
    Module,
    Risk,
    Scope,
)

ADMIN = "admin"
PO = "product_owner"
TL = "tech_lead"

SCOPE = Scope(
    vision=(
        "Ship a shippable delivery-milestones product: scoped MVP, selected tech stack, "
        "phased timeline with risks tracked and milestones formally approved."
    ),
    in_scope=[
        "Scope statement and user roles with enforced permissions",
        "Core module registry with MVP prioritization",
        "Architecture / tech-stack decision log",
        "Phased milestones with timeline, risks and acceptance criteria",
        "Milestone approval workflow with readiness gates",
        "Dashboard UI and REST API over one SQLite store",
    ],
    out_of_scope=[
        "Multi-tenant organizations and SSO",
        "Automated deployment pipelines",
        "Mobile clients",
        "Billing and metering",
    ],
    assumptions=[
        "Single project workspace; one active scope document",
        "Five roles (admin, product_owner, tech_lead, developer, stakeholder)",
        "SQLite is sufficient for planning-scale data",
    ],
    constraints=[
        "Standard library only: no third-party runtime dependencies",
        "Approval requires all acceptance criteria met and no high-exposure open risks",
        "Only admin / product_owner can approve milestones",
    ],
)

MODULES = [
    Module(name="scope-roles", description="Scope document and role registry", priority="P0",
           mvp=True, effort_points=3, status="done"),
    Module(name="module-registry", description="Core module registry with MVP prioritization",
           priority="P0", mvp=True, effort_points=5, status="done"),
    Module(name="arch-log", description="Architecture / tech-stack decision log",
           priority="P0", mvp=True, effort_points=3, status="done"),
    Module(name="milestone-api", description="Milestone, risk and criteria REST API",
           priority="P0", mvp=True, effort_points=8, status="in_progress",
           depends_on=["module-registry"]),
    Module(name="approval-workflow", description="Readiness gates and approval records",
           priority="P0", mvp=True, effort_points=5, status="in_progress",
           depends_on=["milestone-api"]),
    Module(name="dashboard-ui", description="Milestone dashboard UI", priority="P0",
           mvp=True, effort_points=5, status="planned", depends_on=["milestone-api"]),
    Module(name="risk-register", description="Risk register with exposure scoring",
           priority="P1", mvp=True, effort_points=3, status="planned",
           depends_on=["milestone-api"]),
    Module(name="reporting-export", description="CSV/JSON export of roadmap and risks",
           priority="P1", mvp=False, effort_points=3, status="backlog"),
    Module(name="notifications", description="Email/slack notifications on approvals",
           priority="P2", mvp=False, effort_points=5, status="backlog"),
]

ARCH = [
    ArchDecision(category="language", option_name="Python 3.12 (standard library only)",
                 status="selected",
                 rationale="Zero-dependency runtime: sqlite3, http.server and unittest cover store, API and tests.",
                 decided_by=TL),
    ArchDecision(category="language", option_name="Node.js + TypeScript", status="rejected",
                 rationale="Node is unavailable in this environment; adds toolchain without benefit.",
                 decided_by=TL),
    ArchDecision(category="datastore", option_name="SQLite + versioned migrations",
                 status="selected",
                 rationale="Single-file store fits planning-scale data; migrations keep schema evolution explicit.",
                 decided_by=TL),
    ArchDecision(category="datastore", option_name="PostgreSQL", status="proposed",
                 rationale="Candidate if multi-writer scale is ever needed; not required for MVP.",
                 decided_by=TL),
    ArchDecision(category="api", option_name="REST + JSON over stdlib http.server",
                 status="selected",
                 rationale="No framework dependency; small surface area suits the milestone domain.",
                 decided_by=TL),
    ArchDecision(category="ui", option_name="Server-served static page + vanilla JS",
                 status="selected",
                 rationale="One deployable unit, no build step, works offline from the same server.",
                 decided_by=TL),
    ArchDecision(category="tests", option_name="unittest (standard library)",
                 status="selected",
                 rationale="Available everywhere with no install step; covers models, service and live API.",
                 decided_by=TL),
]

MILESTONES = [
    Milestone(name="M1 Discovery & scope sign-off", phase="discovery",
              description="Scope, roles, module priorities and tech stack agreed.",
              start_date="2026-11-16", end_date="2026-11-23", status="done",
              owner_role=PO),
    Milestone(name="M2 MVP backend", phase="mvp",
              description="Store, service rules, REST API and approval workflow.",
              start_date="2026-11-24", end_date="2026-12-05", status="in_progress",
              owner_role=TL),
    Milestone(name="M3 MVP UI & approvals live", phase="mvp",
              description="Dashboard UI, risk register and first approved milestones.",
              start_date="2026-12-06", end_date="2026-12-19", status="planned",
              owner_role=TL),
    Milestone(name="M4 Beta hardening", phase="beta",
              description="Export/reporting, load checks, docs and beta users.",
              start_date="2027-01-04", end_date="2027-01-23", status="draft",
              owner_role=TL),
    Milestone(name="M5 General availability", phase="ga",
              description="GA release with signed-off acceptance evidence.",
              start_date="2027-01-24", end_date="2027-02-06", status="draft",
              owner_role=PO),
]

# milestone name -> [(description, verification_method, status)]
CRITERIA = {
    "M1 Discovery & scope sign-off": [
        ("Scope statement stored with in/out of scope lists", "GET /api/v1/scope returns vision + lists", "met"),
        ("Five user roles defined with enforced permissions", "403 on stakeholder write; roles endpoint", "met"),
        ("Core modules prioritized and MVP slice flagged", "GET /api/v1/mvp lists P0 slice", "met"),
        ("Tech stack selections recorded with rationale", "GET /api/v1/arch?selected_only=1", "met"),
    ],
    "M2 MVP backend": [
        ("Milestone CRUD API covered by automated tests", "python -m unittest passes", "pending"),
        ("Approval blocked until criteria met and risks low", "rejected approval test case", "pending"),
        ("Migrations apply cleanly on an empty database", "fresh-db migration test", "pending"),
    ],
    "M3 MVP UI & approvals live": [
        ("Dashboard shows roadmap, risks and approvals", "manual UI walkthrough", "pending"),
        ("At least one milestone approved end to end", "approval record in API", "pending"),
    ],
    "M4 Beta hardening": [
        ("Export of roadmap and risks available", "export endpoint test", "pending"),
        ("Beta checklist signed off", "approval record", "pending"),
    ],
    "M5 General availability": [
        ("All MVP criteria met with evidence", "readiness report", "pending"),
        ("GA approval recorded", "approval record", "pending"),
    ],
}

# (milestone name | None, title, likelihood, impact, mitigation, status)
RISKS = [
    ("M1 Discovery & scope sign-off", "Scope creep from late stakeholder requests",
     "low", "medium", "Out-of-scope list reviewed at each milestone approval.", "closed"),
    ("M2 MVP backend", "Approval gate too strict blocks progress",
     "medium", "medium", "Readiness endpoint shows exactly what is missing before approval.", "mitigating"),
    ("M2 MVP backend", "SQLite concurrency limits under parallel writers",
     "low", "medium", "Per-request connections; Postgres candidate logged for later.", "open"),
    ("M3 MVP UI & approvals live", "UI/UX rework after first user walkthrough",
     "medium", "high", "Thin vertical slice first; keep UI server-served with no build step.", "open"),
    (None, "Key-person dependency on single implementer",
     "medium", "high", "Docs plus seeded plan keep context recoverable; tests guard behavior.", "mitigating"),
]


def _table_empty(conn: sqlite3.Connection, table: str) -> bool:
    return conn.execute(f"SELECT COUNT(*) AS c FROM {table}").fetchone()["c"] == 0


def seed(conn: sqlite3.Connection) -> dict:
    """Fill empty tables with the initial delivery plan. Returns what was added."""
    added: dict[str, int] = {"roles": 0, "scope": 0, "modules": 0, "arch": 0,
                             "milestones": 0, "criteria": 0, "risks": 0, "approvals": 0}
    if _table_empty(conn, "roles"):
        for name in models.ROLES:
            conn.execute("INSERT INTO roles (name, description) VALUES (?, ?)",
                         (name, models.ROLE_DESCRIPTIONS[name]))
        conn.commit()
        added["roles"] = len(models.ROLES)
    if _table_empty(conn, "scopes"):
        service.save_scope(conn, SCOPE, ADMIN)
        added["scope"] = 1
    if _table_empty(conn, "modules"):
        for module in MODULES:
            service.create_module(conn, Module(**{**module.to_dict(), "id": None}), ADMIN)
        added["modules"] = len(MODULES)
    if _table_empty(conn, "arch_decisions"):
        for decision in ARCH:
            service.save_arch(conn, ArchDecision(**{**decision.to_dict(), "id": None}), ADMIN)
        added["arch"] = len(ARCH)
    if _table_empty(conn, "milestones"):
        ids: dict[str, int] = {}
        for milestone in MILESTONES:
            created = service.create_milestone(
                conn, Milestone(**{**milestone.to_dict(), "id": None}), ADMIN)
            ids[created["name"]] = created["id"]
            added["milestones"] += 1
        for name, items in CRITERIA.items():
            for description, method, status in items:
                service.save_criterion(conn, AcceptanceCriterion(
                    milestone_id=ids[name], description=description,
                    verification_method=method, status=status), ADMIN)
                added["criteria"] += 1
        for name, title, likelihood, impact, mitigation, status in RISKS:
            service.save_risk(conn, Risk(
                milestone_id=ids[name] if name else None, title=title,
                likelihood=likelihood, impact=impact, mitigation=mitigation,
                status=status), ADMIN)
            added["risks"] += 1
        # M1 is fully met with no high-exposure open risks: record its approval
        # through the real workflow to exercise the readiness gate.
        m1 = ids["M1 Discovery & scope sign-off"]
        service.record_approval(conn, Approval(
            milestone_id=m1, approver_role=PO, decision="approved",
            comment="Discovery exit: scope, roles, MVP slice and stack agreed."), PO)
        added["approvals"] = 1
    return added
