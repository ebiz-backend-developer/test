"""Analytics: event ingest + revenue/usage aggregates."""
from __future__ import annotations

import json

from ..db import get_conn


def track(name: str, user_ref: str = "", props: dict | None = None,
          created_at: str | None = None) -> dict:
    conn = get_conn()
    try:
        with conn:
            if created_at:
                cur = conn.execute(
                    "INSERT INTO analytics_events (name, user_ref, props_json, created_at)"
                    " VALUES (?, ?, ?, ?)",
                    (name, user_ref or "", json.dumps(props or {}), created_at),
                )
            else:
                cur = conn.execute(
                    "INSERT INTO analytics_events (name, user_ref, props_json) VALUES (?, ?, ?)",
                    (name, user_ref or "", json.dumps(props or {})),
                )
            row = conn.execute("SELECT * FROM analytics_events WHERE id=?",
                               (cur.lastrowid,)).fetchone()
        d = dict(row)
        d["props"] = json.loads(d.pop("props_json") or "{}")
        return d
    finally:
        conn.close()


def summary(since: str | None = None, until: str | None = None) -> dict:
    conn = get_conn()
    try:
        args: list = []
        window = ""
        if since:
            window += " AND created_at >= ?"
            args.append(since)
        if until:
            window += " AND created_at <= ?"
            args.append(until)
        events = conn.execute(
            f"SELECT name, COUNT(*) c FROM analytics_events WHERE 1=1{window} GROUP BY name ORDER BY c DESC",
            args,
        ).fetchall()
        pay = conn.execute(
            f"""SELECT status, COUNT(*) c, COALESCE(SUM(amount_cents),0) s
                FROM payment_intents WHERE 1=1{window} GROUP BY status""",
            args,
        ).fetchall()
        refunds = conn.execute(
            "SELECT COUNT(*) c, COALESCE(SUM(amount_cents),0) s FROM refunds"
            + (" WHERE 1=1" + window if window else ""),
            args,
        ).fetchone()
        msgs = conn.execute(
            f"SELECT channel, status, COUNT(*) c FROM notification_messages WHERE 1=1{window} GROUP BY channel, status",
            args,
        ).fetchall()
        return {
            "events_by_name": [{"name": r["name"], "count": r["c"]} for r in events],
            "payments_by_status": [
                {"status": r["status"], "count": r["c"], "amount_cents": r["s"]} for r in pay
            ],
            "refunds": {"count": refunds["c"], "amount_cents": refunds["s"]},
            "messages": [
                {"channel": r["channel"], "status": r["status"], "count": r["c"]} for r in msgs
            ],
        }
    finally:
        conn.close()


def timeseries(event: str, bucket: str = "day", since: str | None = None) -> list[dict]:
    fmt = {"day": "%Y-%m-%d", "hour": "%Y-%m-%d %H:00", "month": "%Y-%m"}.get(bucket)
    if fmt is None:
        raise ValueError("bucket must be day, hour or month")
    conn = get_conn()
    try:
        q = f"SELECT strftime('{fmt}', created_at) b, COUNT(*) c FROM analytics_events WHERE name=?"
        args: list = [event]
        if since:
            q += " AND created_at >= ?"
            args.append(since)
        q += " GROUP BY b ORDER BY b"
        return [{"bucket": r["b"], "count": r["c"]} for r in conn.execute(q, args)]
    finally:
        conn.close()
