"""Optional FastAPI application factory."""
from __future__ import annotations

from contextlib import asynccontextmanager
from dataclasses import dataclass
import os
from typing import Any

from fastapi import FastAPI

from projectlens.app.api.errors import install_error_handlers
from projectlens.app.api.routers import router
from projectlens.app.db.repository import mark_orphaned_jobs_interrupted
from projectlens.app.db.session import create_db_engine, create_session_factory
from projectlens.app.db.settings import Settings as DatabaseSettings, get_settings
from projectlens.app.services.analysis_jobs import AnalysisJobManager


@dataclass(frozen=True)
class APISettings:
    database_url: str | None = None
    max_workers: int = 2
    max_queue: int = 8
    checkout_timeout: float = 120.0
    checkout_max_bytes: int = 512 * 1024 * 1024


def _settings(value: Any, *, require_database: bool = True) -> APISettings:
    if value is None:
        if require_database:
            return APISettings(
                database_url=get_settings().database_url,
                max_workers=int(os.environ.get("PROJECTLENS_MAX_WORKERS", "2")),
                max_queue=int(os.environ.get("PROJECTLENS_MAX_QUEUE", "8")),
                checkout_timeout=float(os.environ.get("PROJECTLENS_CHECKOUT_TIMEOUT", "120")),
                checkout_max_bytes=int(os.environ.get("PROJECTLENS_CHECKOUT_MAX_BYTES", str(512 * 1024 * 1024))),
            )
        return APISettings()
    if isinstance(value, APISettings):
        configured = value
    elif isinstance(value, DatabaseSettings):
        configured = APISettings(database_url=value.database_url)
    elif isinstance(value, dict):
        configured = APISettings(**value)
    else:
        configured = APISettings(
            database_url=getattr(value, "database_url", None),
            max_workers=getattr(value, "max_workers", 2),
            max_queue=getattr(value, "max_queue", 8),
            checkout_timeout=getattr(value, "checkout_timeout", 120.0),
            checkout_max_bytes=getattr(value, "checkout_max_bytes", 512 * 1024 * 1024),
        )
    if require_database and not configured.database_url:
        configured = APISettings(
            database_url=get_settings().database_url,
            max_workers=configured.max_workers,
            max_queue=configured.max_queue,
            checkout_timeout=configured.checkout_timeout,
            checkout_max_bytes=configured.checkout_max_bytes,
        )
    return configured


def create_app(settings=None, *, engine=None, session_factory=None, checkout_function=None, executor=None) -> FastAPI:
    """Construct the HTTP app and its resources on demand (never at import time).

    ``engine``, ``session_factory``, ``checkout_function`` and ``executor`` are
    injection points for SQLite tests and deterministic job execution.
    """
    configured = _settings(settings, require_database=session_factory is None and engine is None)
    owns_engine = engine is None and session_factory is None
    if session_factory is None:
        engine = engine or create_db_engine(database_url=configured.database_url, pool_pre_ping=True)
        session_factory = create_session_factory(engine)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        with session_factory() as session, session.begin():
            mark_orphaned_jobs_interrupted(session)
        try:
            yield
        finally:
            app.state.job_manager.shutdown()
            if app.state.owns_engine and app.state.engine is not None:
                app.state.engine.dispose()

    app = FastAPI(title="ProjectLens API", version="1.0.0", lifespan=lifespan)
    app.state.engine = engine
    app.state.owns_engine = owns_engine
    app.state.session_factory = session_factory
    app.state.job_manager = AnalysisJobManager(
        session_factory,
        max_workers=configured.max_workers,
        max_queue=configured.max_queue,
        checkout_timeout=configured.checkout_timeout,
        checkout_max_bytes=configured.checkout_max_bytes,
        checkout_function=checkout_function,
        executor=executor,
    )
    app.include_router(router, prefix="/api/v1")
    install_error_handlers(app)

    return app


__all__ = ["APISettings", "create_app"]
