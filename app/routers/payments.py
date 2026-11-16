"""Payments API: intents, confirm, refunds, webhooks."""
from __future__ import annotations

import os
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException

from ..auth import Actor, audit, current_actor, require_roles
from ..models import PaymentCreate, RefundCreate, WebhookEvent
from ..services import payments

router = APIRouter(prefix="/payments", tags=["payments"])

WEBHOOK_SECRET = os.environ.get("WEBHOOK_SECRET", "dev-webhook-secret")


@router.get("/providers")
def list_providers(actor: Annotated[Actor, Depends(current_actor)]):
    return {"providers": payments.provider_names()}


@router.post("/intents", status_code=201)
def create_intent(body: PaymentCreate, actor: Annotated[Actor, Depends(require_roles("finance", "support", "user"))]):
    if actor.role == "user" and body.customer_email != actor.email:
        raise HTTPException(403, "customers can only create payments for their own email")
    try:
        payment = payments.create_intent(
            body.customer_email, body.amount_cents, body.currency, body.provider,
            body.payment_method, body.metadata, actor.id,
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    audit(actor, "payment.create", payment["public_id"], f"{body.amount_cents} {body.currency}")
    return payment


@router.get("")
def search(customer_email: str | None = None, status: str | None = None,
           actor: Annotated[Actor, Depends(require_roles("finance", "support", "auditor", "user"))] = None):
    if actor.role == "user":
        customer_email = actor.email
    return {"payments": payments.list_payments(customer_email, status)}


@router.get("/{public_id}")
def detail(public_id: str, actor: Annotated[Actor, Depends(require_roles("finance", "support", "auditor", "user"))]):
    payment = payments.get_payment(public_id)
    if payment is None:
        raise HTTPException(404, "payment not found")
    if actor.role == "user" and payment["customer_email"] != actor.email:
        raise HTTPException(403, "not your payment")
    return payment


@router.post("/intents/{public_id}/confirm")
def confirm(public_id: str, actor: Annotated[Actor, Depends(require_roles("finance", "support", "user"))]):
    payment = payments.get_payment(public_id)
    if payment is None:
        raise HTTPException(404, "payment not found")
    if actor.role == "user" and payment["customer_email"] != actor.email:
        raise HTTPException(403, "not your payment")
    try:
        result = payments.confirm_intent(public_id)
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc
    audit(actor, "payment.confirm", public_id, result["status"])
    return result


@router.post("/{public_id}/refund", status_code=201)
def refund(public_id: str, body: RefundCreate,
           actor: Annotated[Actor, Depends(require_roles("finance"))]):
    try:
        result = payments.create_refund(public_id, body.amount_cents, body.reason, actor.id)
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc
    audit(actor, "payment.refund", public_id, f"{body.amount_cents}: {body.reason}")
    return result


@router.post("/webhooks/{provider}")
def webhook(provider: str, body: WebhookEvent,
            x_webhook_secret: Annotated[str | None, Header()] = None):
    if provider not in payments.PROVIDERS:
        raise HTTPException(404, f"unknown provider: {provider}")
    if x_webhook_secret != WEBHOOK_SECRET:
        raise HTTPException(401, "invalid webhook secret")
    result = payments.record_webhook(provider, body.event_type, body.payment_public_id, body.payload)
    audit(None, "payment.webhook", body.payment_public_id or "", f"{provider}:{body.event_type}")
    return result
