"""Compliance reports: audited CSV/JSON report runs with artifacts on disk."""
from __future__ import annotations

import csv
import io
import json
import os
import secrets
from pathlib import Path

from ..db import get_conn

REPORT_TYPES = ("transactions", "refunds", "notifications", "access_audit", "revenue_daily")


def reports_dir() -> Path:
    d = Path(os.environ.get("REPORTS_DIR", str(Path(__file__).resolve().parent.parent.parent / "data" / "reports")))
    d.mkdir(parents=True, exist_ok=True)
    return d


def _window(params: dict) -> tuple[str, list]:
    clause, args = "", []
    if params.get("since"):
        clause += " AND created_at >= ?"
        args.append(params["since"])
    if params.get("until"):
        clause += " AND created_at <= ?"
        args.append(params["until"])
    return clause, args


def fetch_rows(report_type: str, params: dict) -> tuple[list[str], list[dict]]:
    clause, args = _window(params)
    conn = get_conn()
    try:
        if report_type == "transactions":
            cols = ["public_id", "customer_email", "amount_cents", "currency", "provider",
                    "status", "created_by", "created_at"]
            rows = [dict(r) for r in conn.execute(
                f"SELECT {','.join(cols)} FROM payment_intents WHERE 1=1{clause} ORDER BY id", args)]
        elif report_type == "refunds":
            cols = ["public_id", "payment_public_id", "amount_cents", "reason", "status",
                    "created_by", "created_at"]
            rows = [dict(r) for r in conn.execute(
                f"""SELECT r.public_id, p.public_id AS payment_public_id, r.amount_cents,
                           r.reason, r.status, r.created_by, r.created_at
                    FROM refunds r JOIN payment_intents p ON p.id = r.payment_id
                    WHERE 1=1{clause.replace('created_at', 'r.created_at')} ORDER BY r.id""", args)]
        elif report_type == "notifications":
            cols = ["public_id", "channel", "recipient", "template_name", "status",
                    "provider", "error", "created_at"]
            rows = [dict(r) for r in conn.execute(
                f"SELECT {','.join(cols)} FROM notification_messages WHERE 1=1{clause} ORDER BY id", args)]
        elif report_type == "access_audit":
            cols = ["actor_email", "actor_role", "action", "resource", "detail", "created_at"]
            rows = [dict(r) for r in conn.execute(
                f"SELECT {','.join(cols)} FROM audit_log WHERE 1=1{clause} ORDER BY id", args)]
        elif report_type == "revenue_daily":
            cols = ["day", "succeeded_count", "gross_cents", "refunded_cents", "net_cents"]
            rows = [dict(r) for r in conn.execute(
                f"""SELECT strftime('%Y-%m-%d', p.created_at) AS day,
                           COUNT(*) AS succeeded_count,
                           COALESCE(SUM(p.amount_cents),0) AS gross_cents,
                           COALESCE((SELECT SUM(r.amount_cents) FROM refunds r
                                     JOIN payment_intents p2 ON p2.id=r.payment_id
                                     WHERE strftime('%Y-%m-%d', r.created_at)=strftime('%Y-%m-%d', p.created_at)
                                     AND r.status='succeeded'),0) AS refunded_cents,
                           COALESCE(SUM(p.amount_cents),0) - COALESCE((SELECT SUM(r.amount_cents) FROM refunds r
                                     JOIN payment_intents p2 ON p2.id=r.payment_id
                                     WHERE strftime('%Y-%m-%d', r.created_at)=strftime('%Y-%m-%d', p.created_at)
                                     AND r.status='succeeded'),0) AS net_cents
                    FROM payment_intents p WHERE p.status IN ('succeeded','partially_refunded','refunded')
                    {clause.replace('created_at', 'p.created_at')}
                    GROUP BY day ORDER BY day""", args)]
        else:
            raise ValueError(f"unknown report type: {report_type}")
        return cols, rows
    finally:
        conn.close()


def to_csv(cols: list[str], rows: list[dict]) -> str:
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=cols, extrasaction="ignore")
    w.writeheader()
    w.writerows(rows)
    return buf.getvalue()


def run_report(report_type: str, fmt: str, params: dict, created_by: int) -> dict:
    if report_type not in REPORT_TYPES:
        raise ValueError(f"unknown report type: {report_type}")
    cols, rows = fetch_rows(report_type, params or {})
    public_id = f"rpt_{secrets.token_hex(8)}"
    ext = "csv" if fmt == "csv" else "json"
    path = reports_dir() / f"{public_id}.{ext}"
    if fmt == "csv":
        path.write_text(to_csv(cols, rows))
    else:
        path.write_text(json.dumps({"columns": cols, "rows": rows}, indent=2))
    conn = get_conn()
    try:
        with conn:
            cur = conn.execute(
                """INSERT INTO report_runs
                   (public_id, report_type, format, params_json, status, row_count, artifact_path, created_by)
                   VALUES (?, ?, ?, ?, 'succeeded', ?, ?, ?)""",
                (public_id, report_type, fmt, json.dumps(params or {}), len(rows),
                 str(path), created_by),
            )
            row = conn.execute("SELECT * FROM report_runs WHERE id=?", (cur.lastrowid,)).fetchone()
        d = dict(row)
        d["params"] = json.loads(d.pop("params_json") or "{}")
        return d
    finally:
        conn.close()


def list_runs(report_type: str | None = None, limit: int = 100) -> list[dict]:
    conn = get_conn()
    try:
        if report_type:
            rows = conn.execute("SELECT * FROM report_runs WHERE report_type=? ORDER BY id DESC LIMIT ?",
                                (report_type, limit))
        else:
            rows = conn.execute("SELECT * FROM report_runs ORDER BY id DESC LIMIT ?", (limit,))
        out = []
        for r in rows:
            d = dict(r)
            d["params"] = json.loads(d.pop("params_json") or "{}")
            out.append(d)
        return out
    finally:
        conn.close()


def get_run(public_id: str) -> dict | None:
    conn = get_conn()
    try:
        row = conn.execute("SELECT * FROM report_runs WHERE public_id=?", (public_id,)).fetchone()
        if not row:
            return None
        d = dict(row)
        d["params"] = json.loads(d.pop("params_json") or "{}")
        return d
    finally:
        conn.close()
