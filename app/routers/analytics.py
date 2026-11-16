"""Analytics API: event ingest + aggregates."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from ..auth import Actor, require_roles
from ..models import AnalyticsEvent
from ..services import analytics

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.post("/events", status_code=201)
def track(body: AnalyticsEvent,
          actor: Annotated[Actor, Depends(require_roles("developer", "support", "finance"))]):
    return analytics.track(body.name, body.user_ref, body.props)


@router.get("/summary")
def summary(since: str | None = None, until: str | None = None,
            actor: Annotated[Actor, Depends(require_roles("finance", "auditor", "developer"))] = None):
    return analytics.summary(since, until)


@router.get("/timeseries")
def timeseries(event: str, bucket: str = "day", since: str | None = None,
               actor: Annotated[Actor, Depends(require_roles("finance", "auditor", "developer"))] = None):
    try:
        return {"event": event, "bucket": bucket, "points": analytics.timeseries(event, bucket, since)}
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
