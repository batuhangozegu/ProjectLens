import pytest

pytest.importorskip("sqlalchemy")
pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, StatementError

from projectlens.app.api import create_app
from projectlens.app.db.models import AcceptanceCriterion, Base, Project, Task, TaskFileLink
from projectlens.app.db.repository import create_project, create_task
from projectlens.app.db.session import create_db_engine, create_session_factory


@pytest.fixture
def links_env(test_database):
    engine = create_db_engine(database_url=test_database["url"])
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    factory = create_session_factory(engine)
    with factory.begin() as session:
        project = create_project(session, "Links project")
        other = create_project(session, "Other project")
        task = create_task(session, project.id, title="Task")
        other_task = create_task(session, other.id, title="Other task")
        ids = project.id, task.id, other.id, other_task.id
    app = create_app(session_factory=factory)
    with TestClient(app) as client:
        yield client, factory, engine, ids
    Base.metadata.drop_all(engine)
    engine.dispose()


def test_link_criterion_api_happy_paths_and_scoping(links_env):
    client, _factory, _engine, (project_id, task_id, other_id, other_task_id) = links_env
    base = f"/api/v1/projects/{project_id}/tasks/{task_id}"
    link = client.post(f"{base}/links", json={"path": "./src\\pkg//"})
    assert link.status_code == 201 and link.json()["path"] == "src/pkg/"
    duplicate = client.post(f"{base}/links", json={"path": "src/pkg/"})
    assert duplicate.status_code == 409 and duplicate.json()["error"]["code"] == "duplicate_link"
    assert client.get(f"{base}/links").json()["items"][0]["id"] == link.json()["id"]
    assert client.delete(f"{base}/links/{link.json()['id']}").status_code == 204

    criterion = client.post(f"{base}/criteria", json={
        "kind": "file_exists", "params": {"path": "./src\\main.py"}, "description": "main",
    })
    assert criterion.status_code == 201
    assert criterion.json()["params"] == {"path": "src/main.py"}
    criterion_id = criterion.json()["id"]
    assert client.get(f"{base}/criteria/{criterion_id}").status_code == 200
    patched = client.patch(f"{base}/criteria/{criterion_id}", json={"params": {"path": "lib//main.py"}})
    assert patched.status_code == 200 and patched.json()["params"] == {"path": "lib/main.py"}
    assert client.patch(f"{base}/criteria/{criterion_id}", json={"params": {"path": "../x.py"}}).status_code == 422
    assert client.patch(f"{base}/criteria/{criterion_id}", json={"kind": "not_in_cycle"}).status_code == 422
    assert client.patch(f"{base}/criteria/{criterion_id}", json={"attested": True}).status_code == 422
    assert client.delete(f"{base}/criteria/{criterion_id}").status_code == 204
    assert client.get(f"{base}/criteria/{criterion_id}").json()["error"]["code"] == "criterion_not_found"
    assert client.get(f"/api/v1/projects/{other_id}/tasks/{task_id}/links").status_code == 404
    assert client.get(f"/api/v1/projects/{project_id}/tasks/{other_task_id}/criteria/{criterion_id}").status_code == 404
    assert client.get("/api/v1/projects/999999/tasks/1/criteria").json()["error"]["code"] == "project_not_found"
    invalid = client.post(f"{base}/criteria", json={"kind": "manual_attestation", "params": {"extra": 1}})
    assert invalid.status_code == 422 and invalid.json()["error"]["code"] == "validation_error"


def test_limits_attestation_rules_order_and_constraints(links_env):
    client, factory, _engine, (project_id, task_id, _other_id, _other_task_id) = links_env
    base = f"/api/v1/projects/{project_id}/tasks/{task_id}"
    for index in range(50):
        assert client.post(f"{base}/links", json={"path": f"files/{index}.py"}).status_code == 201
        assert client.post(f"{base}/criteria", json={"kind": "manual_attestation", "attested": False}).status_code == 201
    assert client.post(f"{base}/links", json={"path": "overflow.py"}).json()["error"]["code"] == "link_limit_reached"
    assert client.post(f"{base}/criteria", json={"kind": "file_exists", "params": {"path": "x.py"}}).json()["error"]["code"] == "criteria_limit_reached"
    assert client.get(f"{base}/criteria").json()["items"][0]["position"] == 0
    with factory() as session:
        with pytest.raises(IntegrityError):
            session.add(TaskFileLink(task_id=task_id, path="files/0.py")); session.flush()
        session.rollback()
        with pytest.raises(IntegrityError):
            session.add(AcceptanceCriterion(task_id=task_id, kind="unknown", params={}, description="", position=55)); session.flush()
        session.rollback()
        with pytest.raises(IntegrityError):
            session.add(AcceptanceCriterion(task_id=task_id, kind="file_exists", params={}, description="", attested=True, position=55)); session.flush()
        session.rollback()
        with pytest.raises(StatementError):
            session.add(AcceptanceCriterion(task_id=task_id, kind="manual_attestation", params=[], description="", position=55)); session.flush()
        session.rollback()
    assert client.post(f"{base}/criteria", json={"kind": "file_exists", "params": {"path": "x.py"}, "attested": True}).status_code == 422


def test_criteria_order_uses_position_then_id_and_patch_position(links_env):
    client, _factory, _engine, (project_id, task_id, _other_id, _other_task_id) = links_env
    base = f"/api/v1/projects/{project_id}/tasks/{task_id}/criteria"
    second = client.post(base, json={"kind": "manual_attestation", "position": 20}).json()
    first = client.post(base, json={"kind": "manual_attestation", "position": 10}).json()
    assert [item["id"] for item in client.get(base).json()["items"]] == [first["id"], second["id"]]
    moved = client.patch(f"{base}/{second['id']}", json={"position": 0}).json()
    assert moved["position"] == 0
    assert [item["id"] for item in client.get(base).json()["items"]] == [second["id"], first["id"]]


@pytest.mark.parametrize("delete_project", [False, True])
def test_task_and_project_cascade_links_and_criteria(links_env, delete_project):
    _client, factory, _engine, (project_id, task_id, _other_id, _other_task_id) = links_env
    with factory.begin() as session:
        session.add(TaskFileLink(task_id=task_id, path="src/a.py"))
        session.add(AcceptanceCriterion(task_id=task_id, kind="manual_attestation", params={}, description="", position=0))
    with factory.begin() as session:
        if delete_project:
            session.delete(session.get(Project, project_id))
        else:
            session.delete(session.get(Task, task_id))
    with factory() as session:
        assert session.scalar(select(TaskFileLink.id).where(TaskFileLink.task_id == task_id)) is None
        assert session.scalar(select(AcceptanceCriterion.id).where(AcceptanceCriterion.task_id == task_id)) is None
