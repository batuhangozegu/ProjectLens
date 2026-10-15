"""Explicit SQLAlchemy engine and session factory construction."""

from __future__ import annotations

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from .settings import Settings, get_settings


def create_db_engine(settings: Settings | None = None, *, database_url: str | None = None, **kwargs) -> Engine:
    """Create an engine on demand; no engine is constructed at module import."""
    if settings is not None and database_url is not None:
        raise ValueError("pass settings or database_url, not both")
    url = database_url or (settings or get_settings()).database_url
    engine = create_engine(url, **kwargs)
    if url.startswith("sqlite"):
        @event.listens_for(engine, "connect")
        def _enable_sqlite_foreign_keys(dbapi_connection, _connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()
    return engine


def create_session_factory(engine: Engine) -> sessionmaker[Session]:
    """Build a non-expiring session factory bound to an explicitly created engine."""
    return sessionmaker(bind=engine, class_=Session, expire_on_commit=False)
