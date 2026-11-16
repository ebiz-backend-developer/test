"""Notifications: templates, rendering, delivery success/failure."""
from .conftest import auth


def test_seed_templates_present(client):
    r = client.get("/api/v1/notify/templates", headers=auth("support"))
    names = {t["name"] for t in r.json()["templates"]}
    assert {"payment_receipt", "payment_failed", "otp_code", "refund_issued"} <= names


def test_create_template_and_duplicate_conflicts(client):
    body = {"name": "hello", "channel": "email", "subject": "Hi {{name}}", "body": "Hi {{name}}"}
    r = client.post("/api/v1/notify/templates", json=body, headers=auth("support"))
    assert r.status_code == 201
    r = client.post("/api/v1/notify/templates", json=body, headers=auth("support"))
    assert r.status_code == 409


def test_send_with_template_renders_variables(client):
    r = client.post("/api/v1/notify/send", headers=auth("support"), json={
        "channel": "email", "recipient": "cust@example.com",
        "template_name": "payment_receipt",
        "variables": {"name": "Cust", "amount": "25.00", "currency": "USD", "payment_id": "pi_1"}})
    assert r.status_code == 201
    msg = r.json()
    assert msg["status"] == "sent"
    assert "Cust" in msg["body"] and "25.00" in msg["body"] and "{{" not in msg["body"]
    assert msg["provider_message_id"].startswith("email_")


def test_send_sms_raw_body(client):
    r = client.post("/api/v1/notify/send", headers=auth("support"), json={
        "channel": "sms", "recipient": "+15551234567", "body": "hello"})
    assert r.json()["status"] == "sent"


def test_undeliverable_recipient_marks_failed(client):
    r = client.post("/api/v1/notify/send", headers=auth("support"), json={
        "channel": "email", "recipient": "invalid-user", "body": "hi"})
    msg = r.json()
    assert r.status_code == 201
    assert msg["status"] == "failed"
    assert msg["error"]


def test_template_channel_mismatch_rejected(client):
    r = client.post("/api/v1/notify/send", headers=auth("support"), json={
        "channel": "sms", "recipient": "+1555", "template_name": "payment_receipt",
        "variables": {}})
    assert r.status_code == 400


def test_unknown_template_404(client):
    r = client.post("/api/v1/notify/send", headers=auth("support"), json={
        "channel": "email", "recipient": "a@b.c", "template_name": "missing", "variables": {}})
    assert r.status_code == 404


def test_empty_body_rejected(client):
    r = client.post("/api/v1/notify/send", headers=auth("support"), json={
        "channel": "email", "recipient": "a@b.c", "body": "  "})
    assert r.status_code == 400


def test_message_log_filtering(client):
    client.post("/api/v1/notify/send", headers=auth("support"),
                json={"channel": "sms", "recipient": "+15551234567", "body": "a"})
    client.post("/api/v1/notify/send", headers=auth("support"),
                json={"channel": "email", "recipient": "invalid-user", "body": "b"})
    r = client.get("/api/v1/notify/messages?status=failed", headers=auth("auditor"))
    assert r.status_code == 200
    assert all(m["status"] == "failed" for m in r.json()["messages"])
    assert len(r.json()["messages"]) >= 1
