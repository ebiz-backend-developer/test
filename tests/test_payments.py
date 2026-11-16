"""Payments lifecycle: intents, confirm, refunds, webhooks, customer scoping."""
from .conftest import auth, make_payment


def test_create_and_confirm_success(client):
    p = make_payment(client)
    assert p["status"] == "requires_confirmation"
    r = client.post(f"/api/v1/payments/intents/{p['public_id']}/confirm", headers=auth("finance"))
    assert r.status_code == 200
    assert r.json()["status"] == "succeeded"


def test_declined_card_fails_on_confirm(client):
    p = make_payment(client, payment_method="tok_fail")
    r = client.post(f"/api/v1/payments/intents/{p['public_id']}/confirm", headers=auth("finance"))
    assert r.json()["status"] == "failed"


def test_unknown_provider_rejected(client):
    r = client.post("/api/v1/payments/intents",
                    json={"customer_email": "a@b.c", "amount_cents": 100,
                          "provider": "nope", "payment_method": "tok_ok"},
                    headers=auth("finance"))
    assert r.status_code == 400


def test_double_confirm_conflicts(client):
    p = make_payment(client)
    url = f"/api/v1/payments/intents/{p['public_id']}/confirm"
    assert client.post(url, headers=auth("finance")).status_code == 200
    assert client.post(url, headers=auth("finance")).status_code == 409


def test_bank_payment_settles_via_webhook(client):
    p = make_payment(client, provider="bank_mock")
    r = client.post(f"/api/v1/payments/intents/{p['public_id']}/confirm", headers=auth("finance"))
    assert r.json()["status"] == "processing"
    r = client.post("/api/v1/payments/webhooks/bank_mock",
                    json={"event_type": "payment.settled",
                          "payment_public_id": p["public_id"], "payload": {}},
                    headers={"X-Webhook-Secret": "dev-webhook-secret"})
    assert r.json() == {"applied": True, "new_status": "succeeded"}
    r = client.get(f"/api/v1/payments/{p['public_id']}", headers=auth("finance"))
    assert r.json()["status"] == "succeeded"


def test_webhook_bad_secret_rejected(client):
    r = client.post("/api/v1/payments/webhooks/bank_mock",
                    json={"event_type": "payment.settled", "payload": {}},
                    headers={"X-Webhook-Secret": "wrong"})
    assert r.status_code == 401


def test_webhook_unknown_provider_404(client):
    r = client.post("/api/v1/payments/webhooks/nope",
                    json={"event_type": "x", "payload": {}},
                    headers={"X-Webhook-Secret": "dev-webhook-secret"})
    assert r.status_code == 404


def test_full_refund_marks_refunded(client):
    p = make_payment(client)
    client.post(f"/api/v1/payments/intents/{p['public_id']}/confirm", headers=auth("finance"))
    r = client.post(f"/api/v1/payments/{p['public_id']}/refund",
                    json={"amount_cents": 2500, "reason": "duplicate"}, headers=auth("finance"))
    assert r.status_code == 201
    r = client.get(f"/api/v1/payments/{p['public_id']}", headers=auth("finance"))
    assert r.json()["status"] == "refunded"


def test_partial_refund_then_over_refund_rejected(client):
    p = make_payment(client)
    client.post(f"/api/v1/payments/intents/{p['public_id']}/confirm", headers=auth("finance"))
    url = f"/api/v1/payments/{p['public_id']}/refund"
    assert client.post(url, json={"amount_cents": 500}, headers=auth("finance")).status_code == 201
    r = client.get(f"/api/v1/payments/{p['public_id']}", headers=auth("finance"))
    assert r.json()["status"] == "partially_refunded"
    r = client.post(url, json={"amount_cents": 9999}, headers=auth("finance"))
    assert r.status_code == 409


def test_refund_unconfirmed_payment_rejected(client):
    p = make_payment(client)
    r = client.post(f"/api/v1/payments/{p['public_id']}/refund",
                    json={"amount_cents": 100}, headers=auth("finance"))
    assert r.status_code == 409


def test_customer_scoping(client):
    mine = make_payment(client, role="user", customer_email="user@example.com")
    assert mine["customer_email"] == "user@example.com"
    r = client.post("/api/v1/payments/intents",
                    json={"customer_email": "someone-else@example.com", "amount_cents": 100,
                          "provider": "stripe_mock", "payment_method": "tok_ok"},
                    headers=auth("user"))
    assert r.status_code == 403
    make_payment(client, customer_email="cust@example.com")  # another customer's
    r = client.get("/api/v1/payments", headers=auth("user"))
    emails = {p["customer_email"] for p in r.json()["payments"]}
    assert emails == {"user@example.com"}
