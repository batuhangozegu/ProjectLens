from pathlib import Path

import pytest

pytest.importorskip("alembic")
pytest.importorskip("sqlalchemy")

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect


def test_revision_0003_upgrade_and_downgrade(test_database, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", test_database["url"])
    backend = Path(__file__).parents[2]
    config = Config(str(backend / "alembic.ini"))
    config.set_main_option("script_location", str(backend / "migrations"))
    command.upgrade(config, "0002_analysis_jobs")
    command.upgrade(config, "0003_project_tasks")
    engine = create_engine(test_database["url"])
    try:
        inspector = inspect(engine)
        assert "tasks" in inspector.get_table_names()
        assert {"ix_tasks_project_status", "ix_tasks_project_priority"} <= {
            item["name"] for item in inspector.get_indexes("tasks")
        }
    finally:
        engine.dispose()
    command.downgrade(config, "0002_analysis_jobs")
    engine = create_engine(test_database["url"])
    try:
        assert "tasks" not in inspect(engine).get_table_names()
    finally:
        engine.dispose()
