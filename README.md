# SchoolMS — School Management System

Working MVP: role-based API + single-page UI + tests. Plan (scope, roles,
modules/MVP, architecture, milestones) is encoded in `schoolms/plan.py` and
served live at `GET /api/v1/plan`.

## Quickstart
```
pip install -r requirements.txt
python -m migrations.seed        # migrate + demo data (admin / Admin1234)
uvicorn schoolms.main:app        # UI at http://127.0.0.1:8000
pytest                           # full test suite
```

## Layout
- `schoolms/` — API (`routers/`), models, schemas, auth/RBAC, static UI
- `migrations/` — versioned schema migrations + seed data
- `tests/` — pytest suite exercising real API behavior
- `docs/` — scope/roles, modules/MVP, architecture, delivery plan
