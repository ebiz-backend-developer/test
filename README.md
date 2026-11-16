# Task 3: Requirements & Roles — working service

School management platform covering **Admissions, Attendance, Grades,
Timetable, Fees, and Communication**, with executable stakeholder workflows
for **students, teachers, admins, and parents** (plus registrar, accountant,
principal). This branch ships the requirements record **as runnable software**:
a SQLite-backed service layer, a role-gated JSON API, and browser screens —
not just notes.

## Run

```sh
python3 run.py            # serves http://127.0.0.1:8133
make test                 # full suite (stdlib unittest, no deps)
```

Open `http://127.0.0.1:8133` in a browser. Pick an acting role in the role bar
to exercise what each school role may do.

## Map to acceptance criteria

- **c1 — Scope and user roles defined:** `app/rbac.py` (permission matrix),
  `app/seed.py` (`ROLES`, `STAKEHOLDERS`, `SCOPE_ITEMS`, `WORKFLOWS`), the
  workflow engine in `app/service.py`, screens `/roles.html`, `/workflows.html`.
- **c2 — Core modules and MVP prioritized:** `MODULES` seed, `mvp_summary()`,
  `PATCH /api/modules/{code}`, screen `/modules.html`.
- **c3 — Architecture and tech stack selected:** `TECH_OPTIONS` seed,
  propose/select/reject with supersede rule, screen `/architecture.html`.
- **c4 — Delivery milestones approved:** `MILESTONES` seed,
  propose → approve/reject → track flow with recorded decisions and audit,
  screen `/milestones.html`.

Supporting note: [docs/requirements-roles.md](docs/requirements-roles.md).

## Design rules enforced in code

- Deny by default: every write needs `(role, action)` from the matrix.
- Workflow steps complete in order; only listed roles may complete each step
  (e.g. teachers enter grades, the principal publishes; the office links wards
  before parents act).
- One selected tech option per category; selecting supersedes the old choice.
- Milestones move proposed → approved → in_progress → done; rejections need a
  note; approvals record actor + timestamp. Grade/fee/enrolment-style mutations
  write audit entries.
