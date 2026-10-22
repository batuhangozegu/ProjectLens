import pytest

pytest.importorskip("sqlalchemy")
pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient
from sqlalchemy import func, select

from projectlens.app.api import create_app
from projectlens.app.db.models import (
    AcceptanceCriterion, AnalysisJob, AnalysisSnapshot, Base, Project, Task,
    TaskFileLink,
)
from projectlens.app.db.repository import (
    add_snapshot, create_acceptance_criterion, create_analysis_job, create_project,
    create_task, create_task_file_link,
)
from projectlens.app.db.session import create_db_engine, create_session_factory


@pytest.fixture
def project_env(test_database):
    engine = create_db_engine(database_url=test_database["url"])
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    factory = create_session_factory(engine)
    with factory.begin() as session:
        project = create_project(session, "Delete me")
        keep = create_project(session, "Keep me")
        project_id, keep_id = project.id, keep.id
    with TestClient(create_app(session_factory=factory)) as client:
        yield client, factory, project_id, keep_id
    Base.metadata.drop_all(engine)
    engine.dispose()


def test_delete_project_cascades_all_related_rows_and_disappears(project_env):
    client, factory, project_id, keep_id = project_env
    with factory.begin() as session:
        add_snapshot(
            session, project_id, {"schema_version": "1", "metrics": {}},
            branch="main", commit="a" * 40,
        )
        job = create_analysis_job(session, project_id, branch="main", commit=None)
        job.status = "succeeded"
        task = create_task(session, project_id, title="Task")
        create_task_file_link(session, project_id, task.id, "src/app.py")
        create_acceptance_criterion(
            session, project_id, task.id, kind="file_exists", params={"path": "src/app.py"}
        )

    deleted = client.delete(f"/api/v1/projects/{project_id}")
    assert deleted.status_code == 204 and deleted.content == b""
    assert client.delete(f"/api/v1/projects/{project_id}").status_code == 404
    assert client.get(f"/api/v1/projects/{project_id}").json()["error"]["code"] == "project_not_found"
    listed_ids = {item["id"] for item in client.get("/api/v1/projects").json()["items"]}
    assert project_id not in listed_ids and keep_id in listed_ids

    with factory() as session:
        for model in (Project, AnalysisSnapshot, AnalysisJob, Task, TaskFileLink, AcceptanceCriterion):
            assert session.scalar(select(func.count()).select_from(model)) == (1 if model is Project else 0)


def test_delete_missing_project_returns_project_not_found(project_env):
    client, _factory, _project_id, _keep_id = project_env
    response = client.delete("/api/v1/projects/999999")
    assert response.status_code == 404
    assert response.json() == {"error": {"code": "project_not_found", "message": "Project was not found."}}


@pytest.mark.parametrize("status", ["queued", "running"])
def test_delete_project_conflicts_with_active_analysis(project_env, status):
    client, factory, project_id, _keep_id = project_env
    with factory.begin() as session:
        job = create_analysis_job(session, project_id, branch="main", commit=None)
        job.status = status

    response = client.delete(f"/api/v1/projects/{project_id}")
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "project_analysis_active"
    assert "queued or running" in response.json()["error"]["message"]
    assert client.get(f"/api/v1/projects/{project_id}").status_code == 200
