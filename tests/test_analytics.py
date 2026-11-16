"""Analytics: ingest, summary aggregates, timeseries."""
from .conftest import auth, make_payment


def test_track_and_summary(client):
    for _ in range(3):
        r = client.post("/api/v1/analytics/events",
                        json={"name": "page_view", "user_ref": "u1", "props": {"p": "/"}},
                        headers=auth("developer"))
        assert r.status_code == 201
    client.post("/api/v1/analytics/events", json={"name": "signup"},
                headers=auth("developer"))
    p = make_payment(client)
    client.post(f"/api/v1/payments/intents/{p['public_id']}/confirm", headers=auth("finance"))
    r = client.get("/api/v1/analytics/summary", headers=auth("finance"))
    assert r.status_code == 200
    data = r.json()
    by_name = {e["name"]: e["count"] for e in data["events_by_name"]}
    assert by_name == {"page_view": 3, "signup": 1}
    by_status = {p["status"]: p for p in data["payments_by_status"]}
    assert by_status["succeeded"]["count"] == 1
    assert by_status["succeeded"]["amount_cents"] == 2500


def test_timeseries_buckets(client):
    from app.services import analytics as svc

    svc.track("purchase", "u1", {}, created_at="2026-11-01 10:00:00")
    svc.track("purchase", "u2", {}, created_at="2026-11-01 11:00:00")
    svc.track("purchase", "u3", {}, created_at="2026-11-02 10:00:00")
    r = client.get("/api/v1/analytics/timeseries?event=purchase&bucket=day",
                   headers=auth("auditor"))
    assert r.status_code == 200
    assert r.json()["points"] == [
        {"bucket": "2026-11-01", "count": 2},
        {"bucket": "2026-11-02", "count": 1},
    ]


def test_timeseries_bad_bucket(client):
    r = client.get("/api/v1/analytics/timeseries?event=x&bucket=fortnight",
                   headers=auth("auditor"))
    assert r.status_code == 400


def test_support_cannot_read_summary(client):
    r = client.get("/api/v1/analytics/summary", headers=auth("support"))
    assert r.status_code == 403
