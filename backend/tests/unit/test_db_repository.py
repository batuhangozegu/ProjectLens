import shutil
from pathlib import Path

import pytest

pytest.importorskip("sqlalchemy")

from sqlalchemy import create_engine, inspect, select
from sqlalchemy.orm import Session

from projectlens.analysis.models import AnalysisOptions
from projectlens.analysis.pipeline import analyze
from projectlens.app.db.models import AnalysisSnapshot, Base, Project
from projectlens.app.db.repository import (
    DuplicateSnapshotError,
    ProjectNotFoundError,
    add_snapshot,
    create_project,
    get_latest_snapshot,
    get_project,
    get_snapshot,
    list_projects,
    list_snapshots,
)
from projectlens.app.db.session import create_db_engine, create_session_factory


FIXTURE = Path(__file__).parents[1] / "fixtures" / "sample_repo"


@pytest.fixture
def factory(test_database):
    engine = create_db_engine(database_url=test_database["url"])
    Base.metadata.create_all(engine)
    yield create_session_factory(engine)
    engine.dispose()


def test_round_trip_pipeline_result_and_summary_columns(factory, tmp_path):
    copied = tmp_path / "sample_repo"
    shutil.copytree(FIXTURE, copied)
    result = analyze(AnalysisOptions(str(copied)))
    original = __import__("json").loads(result.to_json())

    with factory() as session, session.begin():
        project = create_project(session, "Sample Project", canonical_repository_url="https://github.com/example/sample")
        snapshot = add_snapshot(
            session, project, result, branch="main", commit="a" * 40
        )
        snapshot_id, project_id = snapshot.id, project.id
        assert snapshot.status == "partial"

    with factory() as session:
        stored = get_snapshot(session, snapshot_id)
        snapshot = session.get(AnalysisSnapshot, snapshot_id)
        assert stored == original
        metrics = original["metrics"]
        assert snapshot.file_count == metrics["total_file_count"]
        assert snapshot.python_file_count == metrics["python_file_count"]
        assert snapshot.python_loc == metrics["python_loc"]["total"]
        assert snapshot.edge_count == metrics["dependencies"]["edge_count"]
        assert snapshot.cycle_group_count == metrics["dependencies"]["cycle_group_count"]
        assert snapshot.diagnostic_count == len(original["diagnostics"])
        assert snapshot.created_at.tzinfo is not None
        assert get_latest_snapshot(session, project_id).id == snapshot_id
        assert [item.id for item in list_snapshots(session, project_id)] == [snapshot_id]


def test_duplicate_snapshot_is_rejected(factory):
    with factory() as session, session.begin():
        project = create_project(session, "Project")
        snapshot = {"schema_version": "4", "partial": False, "metrics": {}}
        add_snapshot(session, project, snapshot, branch="main", commit="b" * 40)
        with pytest.raises(DuplicateSnapshotError):
            add_snapshot(session, project, snapshot, branch="main", commit="b" * 40)


def test_unknown_project_raises_domain_error(factory):
    with factory() as session:
        with pytest.raises(ProjectNotFoundError, match="does not exist"):
            add_snapshot(
                session,
                999,
                {"schema_version": "4", "metrics": {}},
                branch="main",
                commit="c" * 40,
            )


def test_project_delete_cascades_to_snapshots(factory):
    with factory() as session, session.begin():
        project = create_project(session, "Project")
        add_snapshot(session, project, {"schema_version": "4", "metrics": {}}, branch="main", commit="d" * 40)
        project_id = project.id
    with factory() as session, session.begin():
        session.delete(session.get(Project, project_id))
    with factory() as session:
        assert session.scalar(select(AnalysisSnapshot.id)) is None


def test_caller_transaction_rollback(factory):
    with pytest.raises(RuntimeError, match="rollback"):
        with factory() as session, session.begin():
            create_project(session, "Uncommitted")
            raise RuntimeError("rollback")
    with factory() as session:
        assert get_project(session, slug="uncommitted") is None
        assert list_projects(session) == []


def test_missing_database_url_is_reported():
    from projectlens.app.db.settings import get_settings

    with pytest.raises(RuntimeError, match="DATABASE_URL is required"):
        get_settings({})
