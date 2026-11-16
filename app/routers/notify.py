"""Notifications API: templates, sending, delivery log."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from ..auth import Actor, audit, require_roles
from ..models import MessageSend, TemplateCreate
from ..services import notify

router = APIRouter(prefix="/notify", tags=["notifications"])


@router.get("/templates")
def templates(channel: str | None = None,
              actor: Annotated[Actor, Depends(require_roles("support", "developer", "auditor"))] = None):
    return {"templates": notify.list_templates(channel)}


@router.post("/templates", status_code=201)
def create_template(body: TemplateCreate,
                    actor: Annotated[Actor, Depends(require_roles("support", "developer"))]):
    try:
        tpl = notify.create_template(body.name, body.channel, body.subject, body.body, actor.id)
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc
    audit(actor, "notify.template.create", body.name, body.channel)
    return tpl


@router.post("/send", status_code=201)
def send(body: MessageSend, actor: Annotated[Actor, Depends(require_roles("support"))]):
    try:
        msg = notify.send_message(body.channel, body.recipient, body.template_name,
                                  body.subject, body.body, body.variables, actor.id)
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    audit(actor, "notify.send", msg["public_id"], f"{body.channel} to {body.recipient}: {msg['status']}")
    return msg


@router.get("/messages")
def messages(channel: str | None = None, status: str | None = None,
             actor: Annotated[Actor, Depends(require_roles("support", "auditor"))] = None):
    return {"messages": notify.list_messages(channel, status)}


@router.get("/messages/{public_id}")
def message_detail(public_id: str,
                   actor: Annotated[Actor, Depends(require_roles("support", "auditor"))]):
    msg = notify.get_message(public_id)
    if msg is None:
        raise HTTPException(404, "message not found")
    return msg
