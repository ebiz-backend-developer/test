# SchoolMS Delivery Milestones (Task 8)

Working software for delivery governance: scope + user roles (c1), core
modules + MVP prioritization (c2), architecture/tech-stack selection (c3),
and delivery milestones with phases, timeline, risks, acceptance criteria
and approvals (c4).

Stdlib-only Python: SQLite store with file migrations, RBAC service layer,
JSON API + dashboard UI, unittest suite.

## Run

```bash
python3 run.py            # dashboard at http://127.0.0.1:8138
python3 run.py --port 8140
DELIVERY_DB=delivery.db python3 run.py   # persistent file instead of memory
make test                 # python3 -m unittest discover -s tests
```

Act as a role via the dashboard role picker or the `X-Role` header
(`admin`, `product_owner`, `tech_lead`, `developer`, `stakeholder`).

## Layout

- `delivery/` — `models.py` (validation), `service.py` (RBAC + rules),
  `store.py` (sqlite + migrations), `seed.py` (SchoolMS plan),
  `server.py` (JSON API + static UI), `static/` (dashboard)
- `delivery/migrations/` — SQL schema migrations
- `tests/` — `test_scope_roles`, `test_modules_mvp`, `test_architecture`,
  `test_milestones`, `test_api` (live-server end-to-end)
- `run.py`, `Makefile`, `pyproject.toml`

## Key rules enforced

- Scope: vision required; nothing both in- and out-of-scope.
- Modules: dependency cycle/unknown-dep checks; status machine
  backlog→planned→in_progress→done; `done` needs deps done.
- Architecture: one selected option per category; rationale required.
- Approvals: need all acceptance criteria met and no open high-exposure
  risk; only `admin`/`product_owner` decide; approved locks the milestone.
