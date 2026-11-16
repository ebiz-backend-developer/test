"""Integrations & Reports service: payments, SMS/email, analytics, compliance reports."""
from __future__ import annotations

from pathlib import Path

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from .db import migrate
from .routers import admin, analytics, notify, payments, planning, reports


@asynccontextmanager
async def lifespan(app: FastAPI):
    migrate()
    yield


app = FastAPI(title="Integrations & Reports API", version="0.1.0", lifespan=lifespan)

app.include_router(admin.router, prefix="/api/v1")
app.include_router(payments.router, prefix="/api/v1")
app.include_router(notify.router, prefix="/api/v1")
app.include_router(analytics.router, prefix="/api/v1")
app.include_router(reports.router, prefix="/api/v1")
app.include_router(planning.router, prefix="/api/v1")

STATIC_DIR = Path(__file__).resolve().parent / "static"
STATIC_DIR.mkdir(exist_ok=True)
app.mount("/", StaticFiles(directory=str(STATIC_DIR), html=True), name="dashboard")
