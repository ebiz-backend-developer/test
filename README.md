# SchoolMS — School Management System

Working MVP covering the scoped modules: users/roles, students, teachers,
classes & enrollments, attendance, grades/GPA, fee billing, and a dashboard UI.

## Quick start (stdlib only, no dependencies)

```sh
python run.py --seed --port 8000
```

Then open [http://127.0.0.1:8000/](http://127.0.0.1:8000/) in a browser.
Demo logins: `admin/admin123`, `teacher/teacher123`, `student/student123`,
`parent/parent123`, `staff/staff123`.

## Tests

```sh
python -m unittest discover -s tests -v
```

## Layout

- `school/` — `models` (validation), `store` (JSON persistence),
  `auth` (users, roles, RBAC), `service` (business logic per module),
  `milestones` (delivery plan as code), `app` (REST API + UI hosting),
  `seed` (demo data)
- `static/index.html` — dashboard UI (login + 8 tabs)
- `config/` — `roles.json` (c1), `modules.json` (c2), `milestones.json` (c4)
- `tests/` — maintained suite: models, service, RBAC, HTTP API, milestones
- `ARCHITECTURE.md` — scope, modules, stack, milestones
