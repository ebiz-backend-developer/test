# Delivery Milestones (Task 8)

Working software for defining delivery milestones: scope + user roles, core
modules with MVP prioritization, architecture/tech-stack decisions, and phased
milestones with timeline, risks, acceptance criteria and an approval workflow.

Standard library only — no third-party dependencies.

## Start the server (API + dashboard UI)

```sh
python3 -m delivery --port 8471
```

(`pip install -e .` also provides a `delivery-server` entry point; both run the
same server declared in [pyproject.toml](pyproject.toml).)

Then open [http://127.0.0.1:8471/](http://127.0.0.1:8471/) in a browser.
The dashboard covers overview, scope, modules/MVP, architecture, milestones,
risks and approvals. Use the role selector to act as a different role
(`admin`, `product_owner`, `tech_lead`, `developer`, `stakeholder`).

Options: `--host`, `--db` (default `data/delivery.db`, created + migrated +
seeded on first start), `--no-seed`. `DELIVERY_DB` env var also sets the database.

## Run the tests

```sh
python -m unittest -v
```

Suites: `tests/test_models.py` (validation), `tests/test_service.py`
(store migrations, roles, scope, MVP, architecture, readiness/approvals),
`tests/test_api.py` (live HTTP server + real SQLite file).

## API sketch

All endpoints live under `/api/v1/` and take the acting role from the
`X-Role` header (default `stakeholder`, read-only).

- `GET /api/v1/roadmap` — phase timeline rollup + MVP + selected stack
- `GET|PUT /api/v1/scope`, `GET /api/v1/roles`
- `GET|POST /api/v1/modules`, `PATCH /api/v1/modules/{id}`, `GET /api/v1/mvp`
- `GET|POST /api/v1/arch` (`?selected_only=1`)
- `GET|POST /api/v1/milestones`, `GET|PATCH /api/v1/milestones/{id}`
- `GET|POST /api/v1/risks`, `GET|POST /api/v1/criteria` (`?milestone_id=`)
- `GET|POST /api/v1/approvals` — approval enforces the readiness gate

See [docs/delivery-plan.md](docs/delivery-plan.md) for the seeded plan summary.
