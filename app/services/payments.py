"""Payments: provider interface + mock PSP adapters + lifecycle helpers.

Swap in real Stripe/bank SDKs by implementing PaymentProvider; the API and
status machine stay unchanged.
"""
from __future__ import annotations

import json
import secrets
from dataclasses import dataclass
from typing import Protocol

from ..db import get_conn


@dataclass
class ProviderResult:
    ok: bool
    status: str  # succeeded | processing | failed
    failure_reason: str = ""
    provider_reference: str = ""


class PaymentProvider(Protocol):
    name: str

    def charge(self, amount_cents: int, currency: str, payment_method: str) -> ProviderResult: ...
    def refund(self, provider_reference: str, amount_cents: int) -> ProviderResult: ...


class StripeMockProvider:
    name = "stripe_mock"

    def charge(self, amount_cents, currency, payment_method):
        if payment_method in ("tok_fail", "card_declined"):
            return ProviderResult(False, "failed", "card_declined", "")
        return ProviderResult(True, "succeeded", "", f"ch_mock_{secrets.token_hex(6)}")

    def refund(self, provider_reference, amount_cents):
        return ProviderResult(True, "succeeded", "", f"re_mock_{secrets.token_hex(6)}")


class BankMockProvider:
    """Bank transfer: asynchronous — confirm moves to processing, a webhook settles it."""

    name = "bank_mock"

    def charge(self, amount_cents, currency, payment_method):
        return ProviderResult(True, "processing", "", f"bt_mock_{secrets.token_hex(6)}")

    def refund(self, provider_reference, amount_cents):
        return ProviderResult(True, "succeeded", "", f"br_mock_{secrets.token_hex(6)}")


PROVIDERS: dict[str, PaymentProvider] = {
    "stripe_mock": StripeMockProvider(),
    "bank_mock": BankMockProvider(),
}


def provider_names() -> list[str]:
    return sorted(PROVIDERS)


def _public_id(prefix: str) -> str:
    return f"{prefix}_{secrets.token_hex(8)}"


def row_to_dict(row) -> dict:
    d = dict(row)
    d["metadata"] = json.loads(d.pop("metadata_json", "{}") or "{}")
    return d


def create_intent(customer_email, amount_cents, currency, provider, payment_method,
                  metadata, created_by) -> dict:
    if provider not in PROVIDERS:
        raise ValueError(f"unknown provider: {provider}")
    conn = get_conn()
    try:
        public_id = _public_id("pi")
        meta = dict(metadata or {})
        meta["payment_method"] = payment_method
        with conn:
            cur = conn.execute(
                """INSERT INTO payment_intents
                   (public_id, customer_email, amount_cents, currency, provider, status, metadata_json, created_by)
                   VALUES (?, ?, ?, ?, ?, 'requires_confirmation', ?, ?)""",
                (public_id, customer_email, amount_cents, currency, provider,
                 json.dumps(meta), created_by),
            )
            row = conn.execute("SELECT * FROM payment_intents WHERE id = ?", (cur.lastrowid,)).fetchone()
        return row_to_dict(row)
    finally:
        conn.close()


def get_payment(public_id: str) -> dict | None:
    conn = get_conn()
    try:
        row = conn.execute("SELECT * FROM payment_intents WHERE public_id = ?", (public_id,)).fetchone()
        return row_to_dict(row) if row else None
    finally:
        conn.close()


def list_payments(customer_email: str | None = None, status: str | None = None,
                  limit: int = 100) -> list[dict]:
    conn = get_conn()
    try:
        q = "SELECT * FROM payment_intents WHERE 1=1"
        args: list = []
        if customer_email:
            q += " AND customer_email = ?"
            args.append(customer_email)
        if status:
            q += " AND status = ?"
            args.append(status)
        q += " ORDER BY id DESC LIMIT ?"
        args.append(limit)
        return [row_to_dict(r) for r in conn.execute(q, args)]
    finally:
        conn.close()


def confirm_intent(public_id: str) -> dict:
    payment = get_payment(public_id)
    if payment is None:
        raise LookupError("payment not found")
    if payment["status"] != "requires_confirmation":
        raise ValueError(f"cannot confirm payment in status {payment['status']}")
    adapter = PROVIDERS[payment["provider"]]
    result = adapter.charge(payment["amount_cents"], payment["currency"],
                            payment["metadata"].get("payment_method", "tok_ok"))
    conn = get_conn()
    try:
        meta = dict(payment["metadata"])
        if result.provider_reference:
            meta["provider_reference"] = result.provider_reference
        with conn:
            conn.execute(
                "UPDATE payment_intents SET status=?, failure_reason=?, metadata_json=?,"
                " updated_at=datetime('now') WHERE public_id=?",
                (result.status, result.failure_reason, json.dumps(meta), public_id),
            )
            conn.execute(
                "INSERT INTO payment_events (payment_id, provider, event_type, payload_json)"
                " VALUES ((SELECT id FROM payment_intents WHERE public_id=?), ?, ?, ?)",
                (public_id, payment["provider"], f"confirm:{result.status}",
                 json.dumps({"provider_reference": result.provider_reference})),
            )
        return get_payment(public_id)
    finally:
        conn.close()


def refunded_total_cents(payment_id: int) -> int:
    conn = get_conn()
    try:
        row = conn.execute(
            "SELECT COALESCE(SUM(amount_cents),0) FROM refunds WHERE payment_id=? AND status='succeeded'",
            (payment_id,),
        ).fetchone()
        return int(row[0])
    finally:
        conn.close()


def create_refund(public_id: str, amount_cents: int, reason: str, created_by: int) -> dict:
    payment = get_payment(public_id)
    if payment is None:
        raise LookupError("payment not found")
    if payment["status"] not in ("succeeded", "partially_refunded"):
        raise ValueError(f"cannot refund payment in status {payment['status']}")
    remaining = payment["amount_cents"] - refunded_total_cents(payment["id"])
    if amount_cents > remaining:
        raise ValueError(f"refund {amount_cents} exceeds refundable {remaining}")
    adapter = PROVIDERS[payment["provider"]]
    result = adapter.refund(payment["metadata"].get("provider_reference", ""), amount_cents)
    if not result.ok:
        raise ValueError(f"provider refund failed: {result.failure_reason}")
    conn = get_conn()
    try:
        with conn:
            cur = conn.execute(
                "INSERT INTO refunds (public_id, payment_id, amount_cents, reason, status, created_by)"
                " VALUES (?, ?, ?, ?, 'succeeded', ?)",
                (_public_id("re"), payment["id"], amount_cents, reason, created_by),
            )
            refund_row = conn.execute("SELECT * FROM refunds WHERE id = ?", (cur.lastrowid,)).fetchone()
            total = conn.execute(
                "SELECT COALESCE(SUM(amount_cents),0) FROM refunds WHERE payment_id=? AND status='succeeded'",
                (payment["id"],),
            ).fetchone()[0]
            new_status = "refunded" if total >= payment["amount_cents"] else "partially_refunded"
            conn.execute(
                "UPDATE payment_intents SET status=?, updated_at=datetime('now') WHERE id=?",
                (new_status, payment["id"]),
            )
            conn.execute(
                "INSERT INTO payment_events (payment_id, provider, event_type, payload_json)"
                " VALUES (?, ?, 'refund:succeeded', ?)",
                (payment["id"], payment["provider"], json.dumps({"amount_cents": amount_cents})),
            )
        return dict(refund_row)
    finally:
        conn.close()


def record_webhook(provider: str, event_type: str, payment_public_id: str | None,
                   payload: dict) -> dict:
    """Apply an asynchronous provider event (e.g. bank settlement)."""
    conn = get_conn()
    try:
        payment = get_payment(payment_public_id) if payment_public_id else None
        with conn:
            conn.execute(
                "INSERT INTO payment_events (payment_id, provider, event_type, payload_json)"
                " VALUES (?, ?, ?, ?)",
                (payment["id"] if payment else None, provider, event_type, json.dumps(payload or {})),
            )
            new_status = None
            if payment and event_type in ("payment.settled", "payment.succeeded"):
                if payment["status"] in ("processing", "requires_confirmation"):
                    new_status = "succeeded"
            elif payment and event_type in ("payment.failed",):
                if payment["status"] in ("processing", "requires_confirmation"):
                    new_status = "failed"
            if new_status:
                conn.execute(
                    "UPDATE payment_intents SET status=?, updated_at=datetime('now') WHERE id=?",
                    (new_status, payment["id"]),
                )
        return {"applied": new_status is not None, "new_status": new_status}
    finally:
        conn.close()
