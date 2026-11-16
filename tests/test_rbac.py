"""RBAC: unauthenticated, unknown key, and cross-role denials."""
from .conftest import auth


def test_missing_key_rejected(client):
    r = client.get("/api/v1/me")
    assert r.status_code == 401


def test_invalid_key_rejected(client):
    r = client.get("/api/v1/me", headers={"X-API-Key": "nope"})
    assert r.status_code == 401


def test_bearer_token_accepted(client):
    r = client.get("/api/v1/me", headers={"Authorization": "Bearer dev-admin-key"})
    assert r.status_code == 200
    assert r.json()["role"] == "admin"


def test_me_returns_actor(client):
    r = client.get("/api/v1/me", headers=auth("finance"))
    assert r.json()["email"] == "finance@example.com"


def test_auditor_cannot_refund(client):
    from .conftest import make_payment

    p = make_payment(client)
    client.post(f"/api/v1/payments/intents/{p['public_id']}/confirm", headers=auth("finance"))
    r = client.post(f"/api/v1/payments/{p['public_id']}/refund",
                    json={"amount_cents": 100}, headers=auth("auditor"))
    assert r.status_code == 403


def test_user_cannot_run_reports(client):
    r = client.post("/api/v1/reports/run",
                    json={"report_type": "transactions", "format": "csv", "params": {}},
                    headers=auth("user"))
    assert r.status_code == 403


def test_support_cannot_approve_milestone(client):
    r = client.post("/api/v1/planning/milestones/1/approve", headers=auth("support"))
    assert r.status_code == 403


def test_auditor_can_read_audit_but_not_users(client):
    assert client.get("/api/v1/admin/audit", headers=auth("auditor")).status_code == 200
    assert client.get("/api/v1/admin/users", headers=auth("auditor")).status_code == 403


def test_status_is_public(client):
    r = client.get("/api/v1/status")
    assert r.status_code == 200
    assert "stripe_mock" in r.json()["payment_providers"]


def test_dashboard_served(client):
    r = client.get("/")
    assert r.status_code == 200
    assert "Integrations &amp; Reports" in r.text or "Integrations & Reports" in r.text
