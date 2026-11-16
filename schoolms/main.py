"""FastAPI application factory: mounts API routers and serves the UI."""

from __future__ import annotations

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from . import __version__
from .config import get_settings
from .database import Base, engine
from .routers import attendance, auth, classes, dashboard, grades, plan, students, teachers, users

STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=f"{settings.app_name} API", version=__version__, lifespan=lifespan)

    @app.get("/health")
    def health():
        return {"status": "ok", "app": settings.app_name, "version": __version__}

    prefix = settings.api_prefix
    app.include_router(auth.router, prefix=prefix)
    app.include_router(users.router, prefix=prefix)
    app.include_router(students.router, prefix=prefix)
    app.include_router(teachers.router, prefix=prefix)
    app.include_router(classes.router, prefix=prefix)
    app.include_router(classes.enroll_router, prefix=prefix)
    app.include_router(attendance.router, prefix=prefix)
    app.include_router(grades.router, prefix=prefix)
    app.include_router(dashboard.router, prefix=prefix)
    app.include_router(plan.router, prefix=prefix)

    if os.path.isdir(STATIC_DIR):
        app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

        @app.get("/", include_in_schema=False)
        def index():
            return FileResponse(os.path.join(STATIC_DIR, "index.html"))

    return app


app = create_app()
