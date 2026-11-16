"""Fresh isolated DB + reports dir per test; thin API helpers."""
import os

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("REPORTS_DIR", str(tmp_path / "reports"))
    from app.main import app

    with TestClient(app) as c:
        yield c


KEYS = {
    "admin": "dev-admin-key",
    "finance": "dev-finance-key",
    "support": "dev-support-key",
    "auditor": "dev-auditor-key",
    "developer": "dev-developer-key",
    "user": "dev-user-key",
}


def auth(role: str) -> dict:
    return {"X-API-Key": KEYS[role]}


def make_payment(c: TestClient, role="finance", **kw):
    body = {
        "customer_email": "cust@example.com",
        "amount_cents": 2500,
        "currency": "USD",
        "provider": "stripe_mock",
        "payment_method": "tok_ok",
    }
    body.update(kw)
    r = c.post("/api/v1/payments/intents", json=body, headers=auth(role))
    assert r.status_code == 201, r.text
    return r.json()
