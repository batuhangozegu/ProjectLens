from pathlib import Path

import pytest

pytest.importorskip("alembic")
pytest.importorskip("sqlalchemy")

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect


def test_revision_0004_upgrade_and_downgrade(test_database, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", test_database["url"])
    backend = Path(__file__).parents[2]
    config = Config(str(backend / "alembic.ini"))
    config.set_main_option("script_location", str(backend / "migrations"))
    command.upgrade(config, "0003_project_tasks")
    command.upgrade(config, "0004_task_links_and_criteria")
    engine = create_engine(test_database["url"])
    try:
        inspector = inspect(engine)
        assert {"task_file_links", "acceptance_criteria"} <= set(inspector.get_table_names())
        assert "ix_task_file_links_task_id" in {item["name"] for item in inspector.get_indexes("task_file_links")}
        assert "ix_acceptance_criteria_task_id" in {item["name"] for item in inspector.get_indexes("acceptance_criteria")}
    finally:
        engine.dispose()
    command.downgrade(config, "0003_project_tasks")
    engine = create_engine(test_database["url"])
    try:
        assert not ({"task_file_links", "acceptance_criteria"} & set(inspect(engine).get_table_names()))
    finally:
        engine.dispose()
