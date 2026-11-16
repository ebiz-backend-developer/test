# School Management MVP — Core Modules

Task 4 delivery: scope + roles, six prioritized core modules, selected stack,
and delivery milestones — all implemented as **runnable software**, not just docs.

## Run

```sh
python3 server.py --seed          # http://127.0.0.1:8000, demo data included
python3 -m unittest discover -s tests -v   # 48 tests, stdlib only
```

No third-party packages required (`requirements.txt` is intentionally empty).

## What was built

| Area | Code |
|---|---|
| Scope + user roles (c1) | [mvp/roles.py](mvp/roles.py), `GET /api/scope` |
| Core modules + MVP priority (c2) | [mvp/catalog.py](mvp/catalog.py), `GET /api/modules` |
| Architecture + stack (c3) | [config.py](config.py), `GET /api/stack` |
| Delivery milestones + approval flow (c4) | [mvp/milestones.py](mvp/milestones.py), `GET/POST /api/milestones` |
| Data layer / migrations | [schema.sql](schema.sql), [mvp/store.py](mvp/store.py) |
| Module services | [mvp/modules/](mvp/modules/) (admissions, attendance, grades, timetable, fees, communication) |
| Roleified JSON API | [mvp/api.py](mvp/api.py) |
| UI (8 screens) | [static/](static/) — overview + one screen per module + milestones |
| Tests | [tests/](tests/) — 48 unittest cases incl. live-HTTP roundtrip |

## Roles & permissions

Six roles (`admin`, `admissions_officer`, `teacher`, `accountant`, `student`,
`parent`), 16 permissions. Pass the role per request via the `X-Role` header
(or `?role=`); the UI has a role switcher. Mutating endpoints return 403 when
the role lacks the permission.

## Core modules (all MVP, P0 except Communication P1)

- **Admissions** — apply → review → admit/waitlist/reject
- **Attendance** — students, daily marking, per-student rate
- **Grades** — assessments, scores, per-student average %
- **Timetable** — weekly slots with class/teacher/room clash detection
- **Fees** — invoices, payments, per-student balances
- **Communication** — broadcasts + audience-filtered inbox

## Milestones

M1 Foundation+Admissions+Comms → M2 Attendance+Timetable → M3 Grades+Fees →
M4 Hardening+pilot. Status flow `planned → approved → in_progress → done`,
approval restricted to `admin`, persisted in `milestone_status`.
