"""Seed data: roles, users, scope, modules, tech, milestones, flows, wireframes."""
from __future__ import annotations

from .models import (
    NewFlow,
    NewMilestone,
    NewModule,
    NewScopeItem,
    NewTechOption,
    NewWireframe,
)
from .rbac import ROLE_DESCRIPTIONS
from .store import Store

SEED_USERS = [
    ("ada", "Ada Admin", "admin"),
    ("priya", "Priya Planner", "product_manager"),
    ("diego", "Diego Designer", "designer"),
    ("devon", "Devon Dev", "developer"),
    ("sam", "Sam Stakeholder", "stakeholder"),
]

SEED_SCOPE = [
    ("Customer onboarding portal", "in_scope",
     "Signup, KYC-lite verification and first-run dashboard for new customers."),
    ("Mobile companion app (iOS/Android)", "in_scope",
     "Responsive web first, then native shells; offline read of key screens."),
    ("Admin analytics dashboard", "in_scope",
     "Module usage, milestone progress and approval queue for admins."),
    ("Legacy billing migration", "out_of_scope",
     "Stays on the existing provider for MVP; revisit after milestone M3."),
    ("In-house design tool", "out_of_scope",
     "Wireframes live in this hub; no Figma replacement is planned."),
    ("Single sign-on available", "assumption",
     "Corporate IdP exposes OIDC before M2; otherwise fall back to passwords."),
]

SEED_MODULES = [
    ("Identity & Access", "Signup, login, SSO, role management.", "P0", "must",
     True, "in_build", "admin", 0),
    ("Customer Dashboard", "Role-aware dashboard with KPIs and shortcuts.", "P0",
     "must", True, "in_design", "product_manager", 1),
    ("Onboarding Flow", "Guided multi-step onboarding with progress save.", "P0",
     "must", True, "in_design", "designer", 2),
    ("Mobile Views", "Responsive layouts plus offline read for key screens.",
     "P1", "must", True, "planned", "designer", 3),
    ("Notifications", "Email/push templates and preference center.", "P1",
     "should", True, "planned", "developer", 4),
    ("Reporting & Export", "Scheduled CSV/PDF exports of dashboard data.", "P2",
     "should", False, "planned", "developer", 5),
    ("Audit Trail", "Immutable event log for approvals and data changes.", "P2",
     "could", False, "planned", "developer", 6),
    ("White-label Themes", "Per-tenant branding packs and theme switcher.", "P3",
     "wont", False, "planned", "designer", 7),
]

SEED_TECH = [
    ("frontend", "Server-rendered HTML + vanilla JS",
     "No build step; progressive enhancement.", "selected",
     "Fastest path to accessible MVP; easy to hand over."),
    ("frontend", "React SPA",
     "Full client-side rendering with a component library.", "rejected",
     "Heavier than MVP needs; revisit for white-label themes."),
    ("backend", "Python stdlib HTTP API",
     "Dependency-free JSON API over http.server.", "selected",
     "Zero-install runtime; sufficient throughput for MVP portals."),
    ("backend", "FastAPI + uvicorn",
     "ASGI stack with automatic docs.", "proposed", ""),
    ("data", "SQLite + SQL migrations",
     "File database with versioned migration scripts.", "selected",
     "Portable, testable, zero-ops for MVP scale."),
    ("data", "PostgreSQL",
     "Managed relational database.", "proposed", ""),
    ("mobile", "Responsive web + PWA shell",
     "One codebase, installable, offline read cache.", "selected",
     "Covers mobile needs without two native codebases."),
    ("mobile", "Native iOS/Android apps",
     "Two platform codebases.", "rejected",
     "Cost exceeds MVP value; PWA covers the flows."),
    ("infra", "Single-host container",
     "One container with volume-mounted SQLite.", "selected",
     "Simplest operable unit for the MVP."),
    ("infra", "Managed Kubernetes",
     "Cluster with autoscaling.", "rejected",
     "Operational overkill before product-market fit."),
]

SEED_MILESTONES = [
    ("M1 — Scope & roles signed off", "Scope items and five user roles agreed.",
     "2026-12-15", "approved", "sam"),
    ("M2 — MVP flows & wireframes", "Core flows and wireframes reviewed on all devices.",
     "2027-01-20", "proposed", ""),
    ("M3 — MVP build complete", "All P0/P1 MVP modules done and tested.",
     "2027-03-01", "draft", ""),
    ("M4 — Mobile & launch readiness", "PWA shell, offline reads, launch checklist.",
     "2027-04-15", "draft", ""),
]

SEED_FLOWS = [
    ("Customer onboarding", "New customer", "both", [
        {"label": "Land on signup", "desc": "Marketing CTA deep-links to /signup.",
         "next": ["Enter details"]},
        {"label": "Enter details", "desc": "Name, work email, password or SSO.",
         "next": ["Verify email"]},
        {"label": "Verify email", "desc": "Magic link; 10-minute expiry.",
         "next": ["Pick workspace"]},
        {"label": "Pick workspace", "desc": "Join invite or create a new one.",
         "next": ["See dashboard"]},
        {"label": "See dashboard", "desc": "Role-aware first-run dashboard.",
         "next": []},
    ]),
    ("Milestone approval", "Stakeholder", "desktop", [
        {"label": "Open approvals", "desc": "Pending queue on the dashboard.",
         "next": ["Review evidence"]},
        {"label": "Review evidence", "desc": "Linked flows, wireframes, tests.",
         "next": ["Approve", "Reject"]},
        {"label": "Approve", "desc": "Records approver and timestamp.", "next": []},
        {"label": "Reject", "desc": "Sends back to draft with a reason.", "next": []},
    ]),
    ("Mobile offline read", "Field agent", "mobile", [
        {"label": "Sync while online", "desc": "PWA caches dashboard + flows.",
         "next": ["Go offline"]},
        {"label": "Go offline", "desc": "Connectivity lost in the field.",
         "next": ["Read cached screens"]},
        {"label": "Read cached screens", "desc": "Read-only banner shown.",
         "next": ["Queue changes"]},
        {"label": "Queue changes", "desc": "Edits queued for later sync.",
         "next": []},
    ]),
    ("Designer handoff", "Designer", "desktop", [
        {"label": "Draft wireframe", "desc": "Block spec created in the hub.",
         "next": ["Request review"]},
        {"label": "Request review", "desc": "Status moves to review.",
         "next": ["PM walkthrough"]},
        {"label": "PM walkthrough", "desc": "Flow + wireframe reviewed together.",
         "next": ["Approve for build"]},
        {"label": "Approve for build", "desc": "Module moves to in_build.",
         "next": []},
    ]),
]

SEED_WIREFRAMES = [
    ("WF-01 Signup", "signup", "both", 3, [
        {"type": "header", "label": "Top bar with logo"},
        {"type": "form", "label": "Name / email / password fields"},
        {"type": "button", "label": "Create account + SSO button"},
        {"type": "text", "label": "Terms note and sign-in link"},
    ]),
    ("WF-02 Customer dashboard", "dashboard", "both", 2, [
        {"type": "nav", "label": "Side nav with role switcher"},
        {"type": "kpi", "label": "KPI strip: modules, milestones, approvals"},
        {"type": "list", "label": "My tasks and pending approvals"},
        {"type": "chart", "label": "Milestone progress chart"},
    ]),
    ("WF-03 Mobile dashboard", "dashboard", "mobile", 4, [
        {"type": "header", "label": "Compact header + offline badge"},
        {"type": "kpi", "label": "Stacked KPI cards"},
        {"type": "list", "label": "Task list, thumb-sized rows"},
        {"type": "navbar", "label": "Bottom tab bar"},
    ]),
    ("WF-04 Approval queue", "milestones", "desktop", 2, [
        {"type": "header", "label": "Milestone title + due date"},
        {"type": "list", "label": "Evidence links: flows, tests"},
        {"type": "button", "label": "Approve / Reject buttons"},
        {"type": "text", "label": "Audit trail of decisions"},
    ]),
    ("WF-05 Module board", "modules", "both", 2, [
        {"type": "nav", "label": "Filter: all / MVP / by priority"},
        {"type": "list", "label": "Module cards with priority badges"},
        {"type": "button", "label": "Prioritize control (PM only)"},
    ]),
    ("WF-06 Flow viewer", "flows", "both", 3, [
        {"type": "header", "label": "Flow name + persona + device"},
        {"type": "diagram", "label": "Step diagram with branches"},
        {"type": "text", "label": "Selected step detail panel"},
    ]),
]


def seed(store: Store) -> dict[str, int]:
    """Insert seed data if tables are empty. Returns counts inserted."""
    counts = {"roles": 0, "users": 0, "scope": 0, "modules": 0, "tech": 0,
              "milestones": 0, "flows": 0, "wireframes": 0}
    conn = store.conn

    if not store.list_roles():
        with conn:
            for name, desc in ROLE_DESCRIPTIONS.items():
                conn.execute(
                    "INSERT INTO roles (name, description) VALUES (?, ?)",
                    (name, desc),
                )
                counts["roles"] += 1

    if not store.list_users():
        roles = {r["name"]: r["id"] for r in store.list_roles()}
        with conn:
            for username, display, role in SEED_USERS:
                conn.execute(
                    "INSERT INTO users (username, display_name, role_id)"
                    " VALUES (?, ?, ?)",
                    (username, display, roles[role]),
                )
                counts["users"] += 1

    if not store.list_scope():
        for title, kind, detail in SEED_SCOPE:
            store.add_scope(NewScopeItem(title=title, kind=kind, detail=detail))
            counts["scope"] += 1

    if not store.list_modules():
        with conn:
            for (name, desc, prio, moscow, mvp, status, owner, order) in SEED_MODULES:
                conn.execute(
                    "INSERT INTO modules (name, description, priority, moscow, mvp,"
                    " status, owner_role, sort_order)"
                    " VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (name, desc, prio, moscow, int(mvp), status, owner, order),
                )
                counts["modules"] += 1

    if not store.list_tech():
        with conn:
            for layer, name, desc, status, rationale in SEED_TECH:
                conn.execute(
                    "INSERT INTO tech_options (layer, name, description, status,"
                    " rationale) VALUES (?, ?, ?, ?, ?)",
                    (layer, name, desc, status, rationale),
                )
                counts["tech"] += 1

    if not store.list_milestones():
        for title, desc, due, status, approved_by in SEED_MILESTONES:
            ms = store.add_milestone(
                NewMilestone(title=title, description=desc, due_date=due)
            )
            if status in ("proposed", "approved"):
                store.submit_milestone(ms["id"])
            if status == "approved":
                store.decide_milestone(ms["id"], "approved", approved_by or "sam")
            counts["milestones"] += 1

    if not store.list_flows():
        for name, persona, device, steps in SEED_FLOWS:
            store.add_flow(NewFlow(name=name, persona=persona, device=device,
                                   steps=steps))
            counts["flows"] += 1

    if not store.list_wireframes():
        # Seed module ids are 1-based in insertion order.
        for title, screen, device, module_id, blocks in SEED_WIREFRAMES:
            store.add_wireframe(NewWireframe(
                title=title, screen=screen, device=device,
                module_id=module_id, blocks=blocks))
            counts["wireframes"] += 1

    return counts
