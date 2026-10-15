import pytest

pytest.importorskip("sqlalchemy")
pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from projectlens.app.api import create_app
from projectlens.app.db.models import Base, Project, Task
from projectlens.app.db.repository import (
    ProjectNotFoundError, TaskNotFoundError, create_project, create_task, delete_task,
    get_task, list_tasks, update_task,
)
from projectlens.app.db.session import create_db_engine, create_session_factory


@pytest.fixture
def task_env(test_database):
    engine = create_db_engine(database_url=test_database["url"])
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    factory = create_session_factory(engine)
    with factory.begin() as session:
        project = create_project(session, "Tasks")
        other = create_project(session, "Other")
        ids = project.id, other.id
    app = create_app(session_factory=factory)
    with TestClient(app) as client:
        yield client, factory, engine, ids
    Base.metadata.drop_all(engine)
    engine.dispose()


def test_repository_position_filters_pagination_and_completion(task_env):
    _client, factory, _engine, (project_id, _) = task_env
    with factory.begin() as session:
        a = create_task(session, project_id, title=" Alpha ", category="  ui  ")
        sequential = create_task(session, project_id, title="Second default")
        b = create_task(session, project_id, title="Beta", status="IN_PROGRESS", priority="HIGH", position=10)
        c = create_task(session, project_id, title="Gamma", status="DONE")
        assert (a.position, sequential.position, b.position, c.position) == (0, 1, 10, 11)
        assert a.category == "ui"
        assert c.completed_at is not None
        done, total = list_tasks(session, project_id, status=["IN_PROGRESS", "DONE"], limit=1)
        assert total == 2 and done[0].id == b.id
        found, count = list_tasks(session, project_id, priority="MEDIUM", category="ui", search="alpha")
        assert count == 1 and found[0].id == a.id
        assert list_tasks(session, project_id, limit=1, offset=2)[0][0].id == b.id
        update_task(session, project_id, a.id, {"status": "DONE"})
        assert a.completed_at is not None
        update_task(session, project_id, a.id, {"status": "IN_PROGRESS"})
        assert a.completed_at is None
        with pytest.raises(ValueError):
            list_tasks(session, project_id, limit=101)


def test_repo_scoping_source_key_checks_and_cascade(task_env):
    _client, factory, _engine, (project_id, other_id) = task_env
    with factory.begin() as session:
        first = create_task(session, project_id, title="One", source="import", source_key="a")
        create_task(session, other_id, title="One", source="import", source_key="a")
        with pytest.raises(IntegrityError):
            create_task(session, project_id, title="Duplicate", source="import", source_key="a")
        session.rollback()
    with factory.begin() as session:
        first = create_task(session, project_id, title="One", source="import", source_key="a")
        task_id = first.id
    with factory() as session:
        with pytest.raises(TaskNotFoundError):
            get_task(session, other_id, task_id)
        with pytest.raises(ProjectNotFoundError):
            get_task(session, 99999, task_id)
    with factory.begin() as session:
        session.delete(session.get(Project, project_id))
    with factory() as session:
        assert session.scalar(select(Task.id).where(Task.project_id == project_id)) is None


def test_database_constraints_reject_invalid_values(task_env):
    _client, factory, _engine, (project_id, _) = task_env
    with factory() as session:
        session.add(Task(project_id=project_id, title="", position=0, status="TODO", priority="MEDIUM", source="manual"))
        with pytest.raises(IntegrityError):
            session.flush()
        session.rollback()
        session.add(Task(project_id=project_id, title="Bad status", position=0, status="INVALID", priority="MEDIUM", source="manual"))
        with pytest.raises(IntegrityError):
            session.flush()


def test_task_api_happy_path_errors_and_validation(task_env):
    client, _factory, _engine, (project_id, other_id) = task_env
    base = f"/api/v1/projects/{project_id}/tasks"
    created = client.post(base, json={"title": "Write API", "category": "  backend  "})
    assert created.status_code == 201
    task = created.json()
    assert task["category"] == "backend" and task["position"] == 0
    task_id = task["id"]
    listing = client.get(base, params={"status": ["TODO"], "category": "backend"}).json()
    assert listing["total"] == 1 and listing["items"][0]["id"] == task_id
    assert client.get(base, params={"limit": 101}).status_code == 422
    for params in ({"status": "INVALID"}, {"priority": "URGENT"}, {"offset": 10001}):
        invalid = client.get(base, params=params)
        assert invalid.status_code == 422 and invalid.json()["error"]["code"] == "validation_error"
    assert client.get(f"{base}/{task_id}").status_code == 200
    assert client.get(f"/api/v1/projects/{other_id}/tasks/{task_id}").status_code == 404
    completed = client.patch(f"{base}/{task_id}", json={"status": "DONE"}).json()
    assert completed["completed_at"] is not None
    repeated = client.patch(f"{base}/{task_id}", json={"status": "DONE"}).json()
    assert repeated["completed_at"] == completed["completed_at"]
    conflict = client.patch(f"{base}/{task_id}", json={"status": "BLOCKED"})
    assert conflict.status_code == 409
    assert conflict.json()["error"]["code"] == "invalid_status_transition"
    assert "DONE" in conflict.json()["error"]["message"] and "BLOCKED" in conflict.json()["error"]["message"]
    assert client.patch(f"{base}/{task_id}", json={"typo": 1}).json()["error"]["code"] == "validation_error"
    assert client.post(base, json={"title": "", "priority": "URGENT"}).status_code == 422
    assert client.get("/api/v1/projects/99999/tasks").status_code == 404
    assert client.get(f"{base}/99999").json()["error"]["code"] == "task_not_found"
    deleted = client.delete(f"{base}/{task_id}")
    assert deleted.status_code == 204 and deleted.content == b""
