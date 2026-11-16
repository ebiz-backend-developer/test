"""Pydantic request/response models."""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

Channel = Literal["sms", "email"]
Priority = Literal["P0", "P1", "P2"]


class PaymentCreate(BaseModel):
    customer_email: str
    amount_cents: int = Field(gt=0)
    currency: str = "USD"
    provider: str = "stripe_mock"
    payment_method: str = "tok_ok"
    metadata: dict[str, Any] = {}


class RefundCreate(BaseModel):
    amount_cents: int = Field(gt=0)
    reason: str = ""


class WebhookEvent(BaseModel):
    event_type: str
    payment_public_id: str | None = None
    payload: dict[str, Any] = {}


class TemplateCreate(BaseModel):
    name: str
    channel: Channel
    subject: str = ""
    body: str


class MessageSend(BaseModel):
    channel: Channel
    recipient: str
    template_name: str | None = None
    subject: str = ""
    body: str = ""
    variables: dict[str, str] = {}


class AnalyticsEvent(BaseModel):
    name: str
    user_ref: str = ""
    props: dict[str, Any] = {}


class ReportRun(BaseModel):
    report_type: Literal["transactions", "refunds", "notifications", "access_audit", "revenue_daily"]
    format: Literal["csv", "json"] = "csv"
    params: dict[str, Any] = {}


class ModuleUpdate(BaseModel):
    status: Literal["planned", "in_progress", "shipped", "deferred"] | None = None
    priority: Priority | None = None


class MilestoneCreate(BaseModel):
    title: str
    description: str = ""
    due_date: str = ""


class TechDecisionCreate(BaseModel):
    area: str
    choice: str
    rationale: str = ""
