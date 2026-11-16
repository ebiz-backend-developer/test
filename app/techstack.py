"""Architecture and tech stack selection (criterion c3)."""
from __future__ import annotations

STACK = {
    "language": "Python 3.11+ (standard library only)",
    "api": "HTTP JSON API on http.server (no framework dependency)",
    "datastore": "SQLite with versioned SQL migrations",
    "ui": "Static HTML/CSS/JS served by the same process",
    "tests": "unittest (standard library)",
}

COMPONENTS = [
    {"id": "web-ui", "name": "Web UI", "tech": "Static HTML/CSS/JS",
     "responsibility": "Role, workflow, module, milestone screens."},
    {"id": "http-api", "name": "HTTP API", "tech": "Python http.server",
     "responsibility": "JSON endpoints for all domain operations."},
    {"id": "service", "name": "Service layer", "tech": "Python package app/",
     "responsibility": "RBAC, workflow engine, MVP ordering, milestone approvals."},
    {"id": "store", "name": "Store", "tech": "sqlite3 + migrations/*.sql",
     "responsibility": "Durable roles, workflow instances, modules, milestones."},
]

DECISIONS = [
    {"id": "ADR-1", "title": "Standard library only",
     "rationale": "Zero install friction; runs anywhere Python 3.11+ exists.",
     "status": "accepted"},
    {"id": "ADR-2", "title": "SQLite as system of record",
     "rationale": "Single-file durable store with SQL migrations; Postgres later.",
     "status": "accepted"},
    {"id": "ADR-3", "title": "Static UI + JSON API",
     "rationale": "Keeps UI decoupled from the service so a framework UI can replace it.",
     "status": "accepted"},
    {"id": "ADR-4", "title": "Milestone approval by admin + parent",
     "rationale": "Both operating and customer stakeholders sign off delivery gates.",
     "status": "accepted"},
]

DATA_FLOW = ["web-ui", "http-api", "service", "store"]


def summary() -> dict:
    return {"stack": STACK, "components": COMPONENTS,
            "decisions": DECISIONS, "data_flow": DATA_FLOW}
