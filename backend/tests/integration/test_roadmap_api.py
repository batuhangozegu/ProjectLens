import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")
pytest.importorskip("sqlalchemy")

from fastapi.testclient import TestClient
from sqlalchemy import select

from projectlens.app.api import create_app
from projectlens.app.db.models import Base, Task
from projectlens.app.db.repository import create_project, create_task, update_task
from projectlens.app.db.session import create_db_engine, create_session_factory
from projectlens.tracking.todo_parser import parse_checklist


@pytest.fixture
def roadmap_env(test_database):
    engine = create_db_engine(database_url=test_database["url"])
    Base.metadata.create_all(engine)
    factory = create_session_factory(engine)
    with factory.begin() as session:
        project = create_project(session, "Roadmap")
        project_id = project.id
    with TestClient(create_app(session_factory=factory)) as client:
        yield client, factory, project_id
    Base.metadata.drop_all(engine)
    engine.dispose()


def _import(client, project_id, markdown, *, dry_run=False):
    return client.post(
        f"/api/v1/projects/{project_id}/roadmap/import",
        json={"markdown": markdown, "dry_run": dry_run},
    )


def test_import_order_mapping_reimport_and_new_item(roadmap_env):
    client, factory, project_id = roadmap_env
    with factory.begin() as session:
        manual = create_task(session, project_id, title="First")
    text = "# Plan\n- [ ] First\n## Area\n- [x] Second\n"
    response = _import(client, project_id, text)
    assert response.status_code == 200
    report = response.json()
    assert report["summary"]["created"] == 2
    with factory() as session:
        tasks = list(session.scalars(select(Task).where(Task.project_id == project_id).order_by(Task.position)))
        assert [(t.title, t.position, t.category, t.status, t.source) for t in tasks] == [
            ("First", manual.position, None, "TODO", "manual"),
            ("First", 1, "Plan", "TODO", "import"),
            ("Second", 2, "Plan / Area", "DONE", "import"),
        ]
    assert _import(client, project_id, text).json()["summary"]["created"] == 0
    second = _import(client, project_id, text + "- [ ] Third\n").json()
    assert second["summary"]["created"] == 1
    assert second["created"][0]["title"] == "Third"


def test_import_transitions_conflicts_done_and_missing_are_safe(roadmap_env):
    client, factory, project_id = roadmap_env
    text = "# Work\n- [ ] Todo\n- [ ] Active\n- [ ] Blocked\n- [x] Done\n- [ ] Gone\n"
    assert _import(client, project_id, text).status_code == 200
    with factory.begin() as session:
        by_title = {t.title: t for t in session.scalars(select(Task).where(Task.project_id == project_id))}
        update_task(session, project_id, by_title["Active"].id, {"status": "IN_PROGRESS"})
        update_task(session, project_id, by_title["Blocked"].id, {"status": "BLOCKED"})
    report = _import(
        client,
        project_id,
        "# Work\n- [x] Todo\n- [x] Active\n- [x] Blocked\n- [ ] Done\n",
    ).json()
    assert report["summary"] == {
        "created": 0, "updated": 2, "unchanged": 1, "conflicts": 1,
        "skipped": 0, "missing_from_source": 1,
    }
    assert report["conflicts"][0]["reason"] == "checked_item_matches_blocked_task"
    assert report["missing_from_source"][0]["title"] == "Gone"
    with factory() as session:
        states = {t.title: t for t in session.scalars(select(Task).where(Task.project_id == project_id))}
        assert states["Todo"].status == states["Active"].status == "DONE"
        assert states["Todo"].completed_at is not None
        assert states["Blocked"].status == "BLOCKED"
        assert states["Done"].status == "DONE"
        assert states["Gone"].status == "TODO"
        assert session.scalar(select(Task.id).where(Task.title == "Gone")) is not None


def test_dry_run_invalid_shapes_oversize_and_long_title(roadmap_env):
    client, factory, project_id = roadmap_env
    with factory.begin() as session:
        create_task(session, project_id, title="Existing")
    before = _snapshot(factory, project_id)
    text = "# Long\n- [ ] " + ("x" * 201) + "\n- [x] Add\n"
    dry = _import(client, project_id, text, dry_run=True)
    assert dry.status_code == 200
    assert dry.json()["summary"]["created"] == 1
    assert dry.json()["summary"]["skipped"] == 1
    assert dry.json()["skipped"][0]["reason"] == "title_too_long"
    assert _snapshot(factory, project_id) == before
    assert client.post(
        f"/api/v1/projects/{project_id}/roadmap/import", json={"markdown": 3}
    ).status_code == 422
    assert client.post(
        f"/api/v1/projects/{project_id}/roadmap/import", json={"markdown": "", "extra": 1}
    ).json()["error"]["code"] == "validation_error"
    oversized = client.post(
        f"/api/v1/projects/{project_id}/roadmap/import",
        content=b'{"markdown":"' + b"x" * (1024 * 1024) + b'"}',
        headers={"Content-Type": "application/json"},
    )
    assert oversized.status_code == 413
    assert oversized.json()["error"]["code"] == "request_too_large"


def test_import_rolls_back_everything_when_a_create_fails(roadmap_env, monkeypatch):
    client, factory, project_id = roadmap_env
    import projectlens.app.services.roadmap_import as importer

    original = importer.create_task
    calls = 0

    def fail_second(*args, **kwargs):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise RuntimeError("injected")
        return original(*args, **kwargs)

    monkeypatch.setattr(importer, "create_task", fail_second)
    response = _import(TestClient(client.app, raise_server_exceptions=False), project_id, "# R\n- [ ] One\n- [ ] Two\n")
    assert response.status_code == 500
    assert _snapshot(factory, project_id) == []


def test_repository_todo_import_and_progress_filters(roadmap_env):
    client, _factory, project_id = roadmap_env
    todo_path = __import__("pathlib").Path(__file__).resolve().parents[3] / "TODO.md"
    markdown = todo_path.read_text(encoding="utf-8")
    expected = len(parse_checklist(markdown).items)
    imported = _import(client, project_id, markdown)
    assert imported.status_code == 200
    assert imported.json()["summary"]["created"] == expected
    progress = client.get(f"/api/v1/projects/{project_id}/roadmap/progress").json()
    assert progress["total"] == expected
    assert progress["counts"]["DONE"] + progress["counts"]["TODO"] + progress["counts"]["IN_PROGRESS"] + progress["counts"]["BLOCKED"] == expected
    assert progress["manual_status_only"] is True
    assert progress["formula_version"] == "1"


def test_progress_empty_mixed_blocked_source_filter_and_missing_project(roadmap_env):
    client, factory, project_id = roadmap_env
    base = f"/api/v1/projects/{project_id}/roadmap/progress"
    empty = client.get(base).json()
    assert empty["state"] == "empty" and empty["percent_complete"] is None
    with factory.begin() as session:
        create_task(session, project_id, title="Done", status="DONE", source="manual")
        create_task(session, project_id, title="Blocked", status="BLOCKED", source="import", source_key="k")
        create_task(session, project_id, title="Working", status="IN_PROGRESS", source="import", source_key="k2")
    all_tasks = client.get(base).json()
    assert all_tasks["total"] == 3 and all_tasks["counts"]["BLOCKED"] == 1
    assert all_tasks["percent_complete"] == 33.3 and all_tasks["has_blocked"] is True
    imported = client.get(base, params={"source": "import"}).json()
    assert imported["total"] == 2 and imported["percent_complete"] == 0.0
    assert client.get(base, params={"source": "bad"}).status_code == 422
    assert client.get("/api/v1/projects/999999/roadmap/progress").status_code == 404
    assert _import(client, 999999, "- [ ] x").status_code == 404


def test_category_shortening_is_deterministic_and_within_task_limit(roadmap_env):
    client, factory, project_id = roadmap_env
    heading = "A" * 50
    nested = "B" * 50
    response = _import(client, project_id, f"# {heading}\n## {nested}\n- [ ] Item\n")
    assert response.status_code == 200
    with factory() as session:
        task = session.scalar(select(Task).where(Task.project_id == project_id, Task.source == "import"))
        expected = "…" + (f"{heading} / {nested}")[-79:]
        assert task.category == expected
        assert len(task.category) == 80


def test_import_report_lists_are_capped_but_counts_are_exact(roadmap_env):
    client, _factory, project_id = roadmap_env
    markdown = "# Many\n" + "".join(f"- [ ] Task {number}\n" for number in range(205))
    response = _import(client, project_id, markdown)
    assert response.status_code == 200
    report = response.json()
    assert report["summary"]["created"] == 205
    assert len(report["created"]) == 200
    assert report["truncated"]["created"] is True


def _snapshot(factory, project_id):
    with factory() as session:
        return [
            (task.title, task.status, task.position, task.source, task.source_key, task.completed_at)
            for task in session.scalars(select(Task).where(Task.project_id == project_id).order_by(Task.position))
        ]
