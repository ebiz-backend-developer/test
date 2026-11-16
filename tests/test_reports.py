"""Compliance reports: run all types, verify content + download + audit trail."""
import json

from .conftest import auth, make_payment


def _seed(client):
    p1 = make_payment(client, customer_email="a@example.com", amount_cents=1000)
    p2 = make_payment(client, customer_email="b@example.com", amount_cents=2000)
    client.post(f"/api/v1/payments/intents/{p1['public_id']}/confirm", headers=auth("finance"))
    client.post(f"/api/v1/payments/intents/{p2['public_id']}/confirm", headers=auth("finance"))
    client.post(f"/api/v1/payments/{p1['public_id']}/refund",
                json={"amount_cents": 400, "reason": "partial"}, headers=auth("finance"))
    client.post("/api/v1/notify/send", headers=auth("support"),
                json={"channel": "email", "recipient": "a@example.com", "body": "hi"})
    return p1, p2


def test_report_types_listed(client):
    r = client.get("/api/v1/reports/types", headers=auth("auditor"))
    assert set(r.json()["report_types"]) == {
        "transactions", "refunds", "notifications", "access_audit", "revenue_daily"}


def test_transactions_csv_content(client):
    _seed(client)
    r = client.post("/api/v1/reports/run",
                    json={"report_type": "transactions", "format": "csv", "params": {}},
                    headers=auth("auditor"))
    assert r.status_code == 201
    run = r.json()
    assert run["row_count"] == 2
    dl = client.get(f"/api/v1/reports/{run['public_id']}/download", headers=auth("auditor"))
    assert dl.status_code == 200
    assert "public_id,customer_email,amount_cents" in dl.text
    assert "a@example.com" in dl.text and "b@example.com" in dl.text


def test_refunds_and_revenue_reports(client):
    _seed(client)
    r = client.post("/api/v1/reports/run",
                    json={"report_type": "refunds", "format": "json", "params": {}},
                    headers=auth("finance"))
    run = r.json()
    assert run["row_count"] == 1
    dl = client.get(f"/api/v1/reports/{run['public_id']}/download", headers=auth("finance"))
    payload = json.loads(dl.text)
    assert payload["rows"][0]["amount_cents"] == 400

    r = client.post("/api/v1/reports/run",
                    json={"report_type": "revenue_daily", "format": "json", "params": {}},
                    headers=auth("finance"))
    run = r.json()
    assert run["row_count"] == 1
    dl = client.get(f"/api/v1/reports/{run['public_id']}/download", headers=auth("finance"))
    row = json.loads(dl.text)["rows"][0]
    assert row["gross_cents"] == 3000 and row["refunded_cents"] == 400
    assert row["net_cents"] == 2600


def test_notifications_and_audit_reports(client):
    _seed(client)
    for rtype in ("notifications", "access_audit"):
        r = client.post("/api/v1/reports/run",
                        json={"report_type": rtype, "format": "csv", "params": {}},
                        headers=auth("auditor"))
        assert r.status_code == 201, r.text
        assert r.json()["row_count"] >= 1


def test_report_history_and_audit_trail(client):
    _seed(client)
    r = client.post("/api/v1/reports/run",
                    json={"report_type": "transactions", "format": "csv", "params": {}},
                    headers=auth("auditor"))
    pid = r.json()["public_id"]
    r = client.get("/api/v1/reports", headers=auth("auditor"))
    assert any(x["public_id"] == pid for x in r.json()["runs"])
    r = client.get("/api/v1/admin/audit?limit=50", headers=auth("auditor"))
    actions = {(e["action"], e["resource"]) for e in r.json()["entries"]}
    assert ("report.run", pid) in actions
