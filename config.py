"""Tech stack selection (criterion c3) as code.

Single source of truth for the stack the MVP is built on. The API exposes
this at GET /api/stack so the "architecture and tech stack selected"
decision is queryable at runtime, not just written in a doc.
"""

STACK = {
    "language": "Python 3.12 (standard library only, no third-party runtime deps)",
    "api": "HTTP JSON API on http.server (REST-ish resources per module)",
    "data_layer": "SQLite via sqlite3, schema-as-code migrations in schema.sql",
    "ui": "Static HTML/CSS/JS in static/ served by the same server, no build step",
    "tests": "unittest (standard library), run with: python3 -m unittest discover -s tests -v",
    "auth": "Role claim via X-Role header / ?role= query (MVP stub for SSO/RBAC)",
    "run": "python3 server.py [--port 8000] [--db school.db]",
}

ARCHITECTURE = {
    "style": "Modular monolith: one deployable, six bounded-context modules "
    "with no cross-module imports except through mvp.store.",
    "layers": ["static/ (UI)", "server.py + mvp/api.py (HTTP/API)",
               "mvp/modules/*.py (domain services)",
               "mvp/store.py + schema.sql (data layer)"],
    "rules": [
        "Each core module owns its tables and service functions.",
        "Every mutating endpoint enforces role-based permission checks.",
        "Migrations are versioned and applied idempotically at startup.",
    ],
}
