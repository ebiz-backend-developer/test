"""Notifications: SMS/email templates, rendering, mock gateways + delivery log.

Real Twilio/SES adapters implement MessageGateway; the API and delivery log
stay unchanged.
"""
from __future__ import annotations

import re
import secrets
from typing import Protocol

from ..db import get_conn

VAR_RE = re.compile(r"\{\{\s*(\w+)\s*\}\}")


class MessageGateway(Protocol):
    name: str
    channel: str

    def send(self, recipient: str, subject: str, body: str) -> tuple[bool, str, str]:
        """Returns (ok, provider_message_id, error)."""


class SmsMockGateway:
    name = "sms_mock"
    channel = "sms"

    def send(self, recipient, subject, body):
        if "invalid" in recipient or not re.fullmatch(r"\+?[0-9 .()+-]+", recipient):
            return False, "", f"undeliverable recipient: {recipient}"
        return True, f"sms_{secrets.token_hex(6)}", ""


class EmailMockGateway:
    name = "email_mock"
    channel = "email"

    def send(self, recipient, subject, body):
        if "invalid" in recipient or "@" not in recipient:
            return False, "", f"undeliverable recipient: {recipient}"
        return True, f"email_{secrets.token_hex(6)}", ""


GATEWAYS: dict[str, MessageGateway] = {
    "sms_mock": SmsMockGateway(),
    "email_mock": EmailMockGateway(),
}
CHANNEL_GATEWAY = {"sms": "sms_mock", "email": "email_mock"}


def render(template: str, variables: dict[str, str]) -> str:
    def sub(m: re.Match) -> str:
        return str(variables.get(m.group(1), m.group(0)))

    return VAR_RE.sub(sub, template)


def get_template(name: str) -> dict | None:
    conn = get_conn()
    try:
        row = conn.execute("SELECT * FROM notification_templates WHERE name = ?", (name,)).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def list_templates(channel: str | None = None) -> list[dict]:
    conn = get_conn()
    try:
        if channel:
            rows = conn.execute("SELECT * FROM notification_templates WHERE channel=? ORDER BY name",
                                (channel,))
        else:
            rows = conn.execute("SELECT * FROM notification_templates ORDER BY name")
        return [dict(r) for r in rows]
    finally:
        conn.close()


def create_template(name, channel, subject, body, created_by) -> dict:
    conn = get_conn()
    try:
        with conn:
            try:
                cur = conn.execute(
                    "INSERT INTO notification_templates (name, channel, subject, body, created_by)"
                    " VALUES (?, ?, ?, ?, ?)",
                    (name, channel, subject, body, created_by),
                )
            except Exception as exc:  # unique name violation
                raise ValueError(f"template '{name}' already exists") from exc
            row = conn.execute("SELECT * FROM notification_templates WHERE id=?",
                               (cur.lastrowid,)).fetchone()
        return dict(row)
    finally:
        conn.close()


def send_message(channel, recipient, template_name, subject, body, variables, created_by) -> dict:
    if template_name:
        tpl = get_template(template_name)
        if tpl is None:
            raise LookupError(f"template '{template_name}' not found")
        if tpl["channel"] != channel:
            raise ValueError(f"template '{template_name}' is for channel {tpl['channel']}")
        subject = render(tpl["subject"], variables)
        body = render(tpl["body"], variables)
    if not body.strip():
        raise ValueError("message body is empty")
    gateway_name = CHANNEL_GATEWAY[channel]
    ok, provider_id, error = GATEWAYS[gateway_name].send(recipient, subject, body)
    conn = get_conn()
    try:
        with conn:
            cur = conn.execute(
                """INSERT INTO notification_messages
                   (public_id, channel, recipient, template_name, subject, body, status,
                    provider, provider_message_id, error, created_by)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (f"msg_{secrets.token_hex(8)}", channel, recipient, template_name or "",
                 subject, body, "sent" if ok else "failed", gateway_name, provider_id,
                 error, created_by),
            )
            row = conn.execute("SELECT * FROM notification_messages WHERE id=?",
                               (cur.lastrowid,)).fetchone()
        return dict(row)
    finally:
        conn.close()


def list_messages(channel: str | None = None, status: str | None = None,
                  limit: int = 100) -> list[dict]:
    conn = get_conn()
    try:
        q = "SELECT * FROM notification_messages WHERE 1=1"
        args: list = []
        if channel:
            q += " AND channel = ?"
            args.append(channel)
        if status:
            q += " AND status = ?"
            args.append(status)
        q += " ORDER BY id DESC LIMIT ?"
        args.append(limit)
        return [dict(r) for r in conn.execute(q, args)]
    finally:
        conn.close()


def get_message(public_id: str) -> dict | None:
    conn = get_conn()
    try:
        row = conn.execute("SELECT * FROM notification_messages WHERE public_id=?",
                           (public_id,)).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()
