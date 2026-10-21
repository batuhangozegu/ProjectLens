import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")
pytest.importorskip("sqlalchemy")

from fastapi.testclient import TestClient

from projectlens.ai.provider import AIResponse, FakeProvider
from projectlens.app.api import create_app
from projectlens.app.api.ai_router import get_ai_provider
from projectlens.app.db.models import Base
from projectlens.app.db.repository import add_snapshot, create_project
from projectlens.app.db.session import create_db_engine, create_session_factory


@pytest.fixture
def ai_env(test_database):
    engine = create_db_engine(database_url=test_database["url"])
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    factory = create_session_factory(engine)
    with factory.begin() as session:
        project = create_project(session, "AI project")
        project_id = project.id
        add_snapshot(session, project, {"schema_version": "1", "files": [{"path": "src/a.py", "language": "python",
                                                   "file_class": "source"}],
                                        "dependency_edges": [], "cycles": [], "metrics": {}},
                     branch="main", commit="a" * 40)
    app = create_app(session_factory=factory)
    provider = FakeProvider([AIResponse("Architecture summary [metric:files].", 4, 6, "fake")])
    app.dependency_overrides[get_ai_provider] = lambda: provider
    with TestClient(app) as client:
        yield client, provider, project_id
    Base.metadata.drop_all(engine)
    engine.dispose()


def test_ai_disabled_by_default(ai_env, monkeypatch):
    client, _, project_id = ai_env
    monkeypatch.delenv("AI_ENABLED", raising=False)
    response = client.post(f"/api/v1/projects/{project_id}/ai/explanations", json={"kind": "risk"})
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "ai_disabled"


def test_ai_explanation_and_snapshot_errors(ai_env, monkeypatch):
    client, provider, project_id = ai_env
    monkeypatch.setenv("AI_ENABLED", "true")
    response = client.post(f"/api/v1/projects/{project_id}/ai/explanations",
                           json={"kind": "architecture", "snapshot": "latest"})
    assert response.status_code == 200
    assert response.json()["text"].startswith("Architecture summary")
    assert len(provider.requests) == 1
    missing = client.post(f"/api/v1/projects/{project_id}/ai/explanations",
                          json={"kind": "risk", "snapshot": "999"})
    assert missing.status_code == 404 and missing.json()["error"]["code"] == "snapshot_not_found"
    no_project = client.post("/api/v1/projects/999999/ai/explanations", json={"kind": "risk"})
    assert no_project.status_code == 404 and no_project.json()["error"]["code"] == "project_not_found"
