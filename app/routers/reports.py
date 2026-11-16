"""Compliance reports API: run, list, download."""
from __future__ import annotations

from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse

from ..auth import Actor, audit, require_roles
from ..models import ReportRun
from ..services import reports

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/types")
def types(actor: Annotated[Actor, Depends(require_roles("finance", "auditor"))]):
    return {"report_types": list(reports.REPORT_TYPES)}


@router.post("/run", status_code=201)
def run(body: ReportRun, actor: Annotated[Actor, Depends(require_roles("finance", "auditor"))]):
    try:
        result = reports.run_report(body.report_type, body.format, body.params, actor.id)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    audit(actor, "report.run", result["public_id"], f"{body.report_type} ({body.format}): {result['row_count']} rows")
    return result


@router.get("")
def history(report_type: str | None = None,
            actor: Annotated[Actor, Depends(require_roles("finance", "auditor"))] = None):
    return {"runs": reports.list_runs(report_type)}


@router.get("/{public_id}")
def detail(public_id: str, actor: Annotated[Actor, Depends(require_roles("finance", "auditor"))]):
    run = reports.get_run(public_id)
    if run is None:
        raise HTTPException(404, "report run not found")
    return run


@router.get("/{public_id}/download")
def download(public_id: str, actor: Annotated[Actor, Depends(require_roles("finance", "auditor"))]):
    run = reports.get_run(public_id)
    if run is None:
        raise HTTPException(404, "report run not found")
    path = Path(run["artifact_path"])
    if not path.exists():
        raise HTTPException(404, "report artifact missing")
    media = "text/csv" if run["format"] == "csv" else "application/json"
    audit(actor, "report.download", public_id, run["report_type"])
    return FileResponse(path, media_type=media, filename=f"{public_id}.{run['format']}")
