"""Planning: scope/roles (c1), modules/MVP (c2), tech stack (c3), milestones (c4)."""
from .conftest import auth


def test_scope_and_roles_defined(client):
    scope = client.get("/api/v1/planning/scope", headers=auth("user")).json()["scope"]
    assert len(scope) >= 7
    assert any(not s["in_scope"] for s in scope)  # explicit out-of-scope items
    roles = client.get("/api/v1/planning/roles", headers=auth("user")).json()["roles"]
    assert {r["name"] for r in roles} == {"admin", "finance", "support", "auditor", "developer", "user"}


def test_modules_mvp_prioritized(client):
    mods = client.get("/api/v1/planning/modules", headers=auth("developer")).json()["modules"]
    by_name = {m["name"]: m for m in mods}
    assert by_name["payments"]["priority"] == "P0" and by_name["payments"]["mvp"] == 1
    assert by_name["real-psp-adapters"]["mvp"] == 0
    mvp = client.get("/api/v1/planning/modules?mvp_only=true", headers=auth("developer")).json()["modules"]
    assert all(m["mvp"] == 1 for m in mvp) and len(mvp) < len(mods)


def test_module_status_update(client):
    r = client.patch("/api/v1/planning/modules/payments", json={"status": "in_progress"},
                     headers=auth("developer"))
    assert r.status_code == 200 and r.json()["status"] == "in_progress"
    r = client.patch("/api/v1/planning/modules/payments", json={"status": "in_progress"},
                     headers=auth("support"))
    assert r.status_code == 403


def test_tech_stack_selected_and_proposable(client):
    decisions = client.get("/api/v1/planning/tech", headers=auth("user")).json()["decisions"]
    assert any(d["status"] == "selected" for d in decisions)
    r = client.post("/api/v1/planning/tech",
                    json={"area": "queue", "choice": "Redis Streams", "rationale": "webhooks"},
                    headers=auth("developer"))
    assert r.status_code == 201 and r.json()["status"] == "proposed"


def test_milestone_approval_flow(client):
    r = client.post("/api/v1/planning/milestones",
                    json={"title": "M9 test", "description": "d", "due_date": "2027-05-01"},
                    headers=auth("admin"))
    assert r.status_code == 201
    mid = r.json()["id"]
    assert r.json()["status"] == "proposed"
    # non-admin cannot approve
    assert client.post(f"/api/v1/planning/milestones/{mid}/approve",
                       headers=auth("finance")).status_code == 403
    # approve then complete
    r = client.post(f"/api/v1/planning/milestones/{mid}/approve", headers=auth("admin"))
    assert r.json()["status"] == "approved"
    # double approval conflicts
    assert client.post(f"/api/v1/planning/milestones/{mid}/approve",
                       headers=auth("admin")).status_code == 409
    r = client.post(f"/api/v1/planning/milestones/{mid}/complete", headers=auth("admin"))
    assert r.json()["status"] == "done"


def test_complete_requires_approval(client):
    r = client.post("/api/v1/planning/milestones/1/complete", headers=auth("admin"))
    assert r.status_code == 409  # still proposed


def test_seed_milestones_present(client):
    ms = client.get("/api/v1/planning/milestones", headers=auth("admin")).json()["milestones"]
    assert len(ms) >= 4
