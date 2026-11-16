# Architecture and Tech Stack (c3)

Source of truth: `schoolms/plan.py` (`ARCHITECTURE`); live at `GET /api/v1/plan/architecture`.

- Style: modular monolith — one FastAPI app, one router per module.
- Language: Python 3.12; API: FastAPI + Starlette.
- Data: SQLAlchemy 2.0 ORM; SQLite file DB for MVP (`SCHOOLMS_DATABASE_URL`
  switches to Postgres); versioned migrations in `migrations/run.py`.
- Auth: JWT (PyJWT HS256) + PBKDF2 password hashing (stdlib only).
- UI: static single-page app (`schoolms/static/index.html`) served by the API.
- Tests: pytest + FastAPI TestClient (`tests/`).

Layers: `routers/` (HTTP) → `schemas.py` (validation) → `models.py` (ORM) →
`security.py`/`deps.py` (auth + RBAC) → `database.py` (sessions).
Run: `pip install -r requirements.txt && python -m migrations.seed &&
uvicorn schoolms.main:app`; open http://127.0.0.1:8000.
