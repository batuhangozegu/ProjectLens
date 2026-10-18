import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")
pytest.importorskip("sqlalchemy")

from fastapi.testclient import TestClient
from sqlalchemy import select

from projectlens.app.api import create_app
from projectlens.app.db.models import AcceptanceCriterion, Base, Task, TaskFileLink
from projectlens.app.db.repository import add_snapshot, create_project, create_task
from projectlens.app.db.session import create_db_engine, create_session_factory


def _result(*, partial=False, files=None):
    return {
        "schema_version": "1", "partial": partial,
        "files": files or [{"path": "src/a.py", "analysis_status": "analyzed"}],
        "dependency_edges": [], "cycles": [], "diagnostics": [],
        "metrics": {"total_file_count": 1, "python_file_count": 1,
                    "python_loc": {"total": 1}, "dependencies": {"edge_count": 0}},
    }


@pytest.fixture
def assessment_env(test_database):
    engine = create_db_engine(database_url=test_database["url"])
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    factory = create_session_factory(engine)
    with factory.begin() as session:
        project = create_project(session, "Assessment")
        other = create_project(session, "Other assessment")
        task = create_task(session, project.id, title="Evidence", status="DONE")
        empty = create_project(session, "Empty")
        ids = project.id, task.id, other.id, empty.id
    with TestClient(create_app(session_factory=factory)) as client:
        yield client, factory, ids
    Base.metadata.drop_all(engine)
    engine.dispose()


def _snapshot(factory, project_id, *, partial=False, commit="a"):
    with factory.begin() as session:
        return add_snapshot(session, project_id, _result(partial=partial), branch="main",
                            commit=commit * 40)


def test_task_assessment_snapshot_selection_errors_and_no_snapshot(assessment_env):
    client, factory, (project_id, task_id, other_id, _empty_id) = assessment_env
    base = f"/api/v1/projects/{project_id}/tasks/{task_id}/assessment"
    assert client.get(base).json()["state"] == "no_snapshot"
    selected = _snapshot(factory, project_id)
    other_snapshot = _snapshot(factory, other_id, commit="b")
    assert client.get(base).json()["snapshot"]["id"] == selected.id
    assert client.get(base, params={"snapshot": str(selected.id)}).json()["snapshot"]["commit"] == "a" * 40
    wrong_project = client.get(base, params={"snapshot": str(other_snapshot.id)})
    assert wrong_project.status_code == 404 and wrong_project.json()["error"]["code"] == "snapshot_not_found"
    invalid = client.get(base, params={"snapshot": "newest"})
    assert invalid.status_code == 422 and invalid.json()["error"]["code"] == "validation_error"
    assert client.get("/api/v1/projects/999999/tasks/1/assessment").json()["error"]["code"] == "project_not_found"
    assert client.get(f"/api/v1/projects/{project_id}/tasks/999999/assessment").json()["error"]["code"] == "task_not_found"


def test_task_assessment_evidence_unknown_divergence_and_manual_status_unchanged(assessment_env):
    client, factory, (project_id, task_id, _other_id, _empty_id) = assessment_env
    with factory.begin() as session:
        session.add(TaskFileLink(task_id=task_id, path="src/a.py"))
        session.add(AcceptanceCriterion(task_id=task_id, kind="file_exists", params={"path": "src/a.py"},
                                        description="present", position=0))
        session.add(AcceptanceCriterion(task_id=task_id, kind="file_exists", params={"path": "missing.py"},
                                        description="missing", position=1))
        session.add(AcceptanceCriterion(task_id=task_id, kind="manual_attestation", params={},
                                        description="reported", attested=True, position=2))
    _snapshot(factory, project_id)
    response = client.get(f"/api/v1/projects/{project_id}/tasks/{task_id}/assessment")
    body = response.json()
    assert [item["outcome"] for item in body["criteria_results"]] == ["met", "unmet", "unknown"]
    assert body["divergence"] == "done_but_unmet"
    with factory() as session:
        assert session.scalar(select(Task.status).where(Task.id == task_id)) == "DONE"
    assert body["manual_status"] == "DONE"


def test_roadmap_assessment_mixed_empty_and_no_snapshot(assessment_env):
    client, factory, (project_id, task_id, _other_id, empty_id) = assessment_env
    with factory.begin() as session:
        create_task(session, project_id, title="No criteria")
    mixed = client.get(f"/api/v1/projects/{project_id}/roadmap/assessment").json()
    assert mixed["total_tasks"] == 2 and mixed["snapshot"] is None
    assert mixed["counts_by_state"]["no_snapshot"] == 2
    assert mixed["tasks_without_criteria"] == 2
    assert mixed["average_estimated_percent"] is None
    _snapshot(factory, project_id)
    with factory.begin() as session:
        session.add(AcceptanceCriterion(task_id=task_id, kind="file_exists", params={"path": "src/a.py"},
                                        description="present", position=0))
    result = client.get(f"/api/v1/projects/{project_id}/roadmap/assessment").json()
    assert result["total_tasks"] == 2 and result["tasks_with_estimate"] == 1
    assert result["tasks_without_criteria"] == 1
    assert "average_estimated_percent" in result and result["snapshot"] is not None
    empty = client.get(f"/api/v1/projects/{empty_id}/roadmap/assessment").json()
    assert empty["total_tasks"] == 0 and empty["average_estimated_percent"] is None
    assert empty["snapshot"] is None
