# Design Hub — UI/UX flows, dashboards & portals

Working software for Task 6 (Design UI/UX flows). Stdlib-only Python backend
(SQLite + `http.server`, no install step) serving a JSON API and a responsive
multi-portal UI.

## Run

```sh
python3 run.py              # http://127.0.0.1:8130
python3 run.py --port 8080 --db data/hub.db
python3 -m unittest discover -s tests   # or: make test
```

Open [the portal](http://127.0.0.1:8130) in a browser after starting the server.
Use the “Acting as” switcher (seed users: `ada`, `priya`, `diego`, `devon`,
`sam`) — write actions enforce per-role permissions.

## Criterion coverage

- **c1 Scope & user roles** — `app/rbac.py` matrix, `roles`/`users`/`scope_items`
  tables, `/api/roles`, `/api/scope`, [scope page](web/scope.html).
- **c2 Core modules & MVP** — `modules` table with P0–P3 + MVP flag,
  `/api/modules` (+ `?mvp=1`, `/prioritize`), [modules board](web/modules.html).
- **c3 Architecture & tech stack** — `tech_options` per layer with
  select-supersedes logic, `/api/tech`, [tech page](web/tech.html).
- **c4 Delivery milestones** — draft → proposed → approved workflow with audit
  trail (`migrations/002_*`), `/api/milestones`, [milestones page](web/milestones.html).

Plus SVG UX-flow diagrams ([flows](web/flows.html)), rendered wireframe block
specs ([wireframes](web/wireframes.html)), role dashboards
([dashboard](web/dashboard.html)), and mobile support via responsive CSS plus a
bottom tab bar and device-filtered flows/wireframes.
