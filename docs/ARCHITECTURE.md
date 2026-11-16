# Architecture (supporting note — the code is the delivery)

Modular monolith, stdlib-only Python 3.12 + SQLite.

```
browser ── static/ (index.html, app.js, styles.css, no build step)
                │  fetch /api/* with X-Role header
server.py (ThreadingHTTPServer) ── mvp/api.py (routing + RBAC)
                │  one service module per bounded context
mvp/modules/{admissions,attendance,grades,timetable,fees,communication}.py
                │  sqlite3 only
mvp/store.py ── schema.sql (versioned, idempotent migration)
```

Rules: each module owns its tables; no cross-module imports except `mvp.store`;
every mutating route declares one permission enforced by `mvp.roles.check`;
milestone transitions follow `planned → approved → in_progress → done`.

Why this stack: zero-install runs anywhere (reviewer, CI, pilot school server),
SQLite is enough for single-school MVP scale, and the module boundaries map
1:1 onto the M1–M3 milestones so teams can parallelize later. If scale demands
it, each `mvp/modules/*` service can be extracted behind the same JSON routes.
