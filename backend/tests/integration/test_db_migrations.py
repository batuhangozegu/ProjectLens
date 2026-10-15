from pathlib import Path

import pytest

pytest.importorskip("sqlalchemy")
pytest.importorskip("alembic")

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect


def test_migration_upgrade_and_downgrade_sqlite_file(test_database, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", test_database["url"])
    backend = Path(__file__).parents[2]
    config = Config(str(backend / "alembic.ini"))
    config.set_main_option("script_location", str(backend / "migrations"))

    command.upgrade(config, "head")
    engine = create_engine(test_database["url"])
    try:
        inspector = inspect(engine)
        assert {"projects", "analysis_snapshots", "analysis_jobs", "alembic_version"} <= set(inspector.get_table_names())
        assert "ix_snapshot_project_created" in {
            index["name"] for index in inspector.get_indexes("analysis_snapshots")
        }
    finally:
        engine.dispose()

    command.downgrade(config, "base")
    engine = create_engine(test_database["url"])
    try:
        assert set(inspect(engine).get_table_names()) <= {"alembic_version"}
    finally:
        engine.dispose()
