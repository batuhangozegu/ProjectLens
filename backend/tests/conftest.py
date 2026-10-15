"""Shared database fixtures for SQLite and opt-in PostgreSQL test runs."""

from __future__ import annotations

import os

import pytest


_DATABASE_BACKENDS = ("sqlite", "postgres") if os.environ.get("TEST_DATABASE_URL") else ("sqlite",)


@pytest.fixture(params=_DATABASE_BACKENDS, ids=_DATABASE_BACKENDS)
def test_database(request, tmp_path):
    """Provide an isolated database and clear all tables around each DB test.

    PostgreSQL is deliberately opt-in and may only target a database whose
    name ends with ``_test``.  Never infer this URL from DATABASE_URL.
    """
    from sqlalchemy import create_engine
    from sqlalchemy.engine import make_url

    backend = request.param
    configured_url = os.environ.get("TEST_DATABASE_URL")
    if backend == "postgres":
        assert configured_url is not None
        try:
            parsed_url = make_url(configured_url)
        except Exception as exc:
            raise pytest.UsageError(f"Invalid TEST_DATABASE_URL: {exc}") from exc
        if parsed_url.get_backend_name() != "postgresql":
            raise pytest.UsageError("TEST_DATABASE_URL must use a PostgreSQL URL.")
        database_name = parsed_url.database
        if not database_name or not database_name.endswith("_test"):
            raise pytest.UsageError(
                "Refusing PostgreSQL tests: TEST_DATABASE_URL database name must end with '_test' "
                "because the test fixture drops and recreates schema objects."
            )
        url = configured_url
    else:
        url = f"sqlite:///{(tmp_path / 'test.sqlite').as_posix()}"

    engine = create_engine(url)

    def clear_schema():
        sqlalchemy = __import__("sqlalchemy")
        metadata = sqlalchemy.MetaData()
        metadata.reflect(bind=engine, only=lambda _name, _metadata: _name in {
            "projects", "analysis_snapshots", "analysis_jobs", "alembic_version"
        })
        metadata.drop_all(bind=engine)

    clear_schema()
    try:
        yield {"url": url, "backend": backend}
    finally:
        clear_schema()
        engine.dispose()
