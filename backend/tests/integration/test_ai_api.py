import io
import json
from urllib.error import HTTPError, URLError

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")
pytest.importorskip("sqlalchemy")

from fastapi.testclient import TestClient

from projectlens.ai.provider import AIResponse, FakeProvider
from projectlens.ai import clients
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


@pytest.fixture
def real_ai(ai_env, monkeypatch, caplog):
    client, _, project_id = ai_env
    client.app.dependency_overrides.pop(get_ai_provider)
    for name in ("PROVIDER", "MODEL", "BASE_URL", "API_KEY"):
        monkeypatch.delenv(f"PROJECTLENS_AI_{name}", raising=False)
    monkeypatch.setenv("AI_ENABLED", "true")
    monkeypatch.setenv("AI_MAX_CONTEXT_BYTES", "16384")
    monkeypatch.setenv("AI_MAX_OUTPUT_TOKENS", "512")
    monkeypatch.setenv("AI_TIMEOUT_S", "20")
    caplog.set_level("DEBUG")
    return client, project_id


def _chat_bytes(text="OK"):
    return io.BytesIO(json.dumps({"choices": [{"message": {"content": text}}]}).encode())


def test_connection_prompt_is_fixed_and_tiny(real_ai, monkeypatch, caplog):
    client, _ = real_ai
    key = "sk-browser-only-secret"
    requests = []

    def open_request(request, *, timeout):
        payload = json.loads(request.data)
        requests.append(payload)
        assert payload["max_completion_tokens"] == 16
        assert payload["messages"] == [{"role": "system", "content": "You are testing a connection. Reply briefly."},
                                       {"role": "user", "content": "Reply with OK."}]
        assert "src/a.py" not in request.data.decode()
        assert request.get_header("Authorization") == f"Bearer {key}"
        return _chat_bytes()

    monkeypatch.setattr(clients, "urlopen", open_request)
    response = client.post("/api/v1/ai/test", headers={"X-AI-Provider": "openai", "X-AI-Key": key})
    assert response.status_code == 200
    assert response.json() == {"ok": True, "provider": "openai", "model": "gpt-4.1-mini"}
    assert len(requests) == 1
    assert key not in response.text and key not in caplog.text
    # Credentials from a prior request must not be retained.
    assert client.post("/api/v1/ai/test").json()["error"]["code"] == "ai_unavailable"
    assert len(requests) == 1


def test_environment_fallback_and_header_isolation(real_ai, monkeypatch):
    client, _ = real_ai
    monkeypatch.setenv("PROJECTLENS_AI_PROVIDER", "openai")
    monkeypatch.setenv("PROJECTLENS_AI_MODEL", "server-model")
    monkeypatch.setenv("PROJECTLENS_AI_API_KEY", "server-secret")
    seen = []

    def open_request(request, *, timeout):
        seen.append(request)
        return _chat_bytes()

    monkeypatch.setattr(clients, "urlopen", open_request)
    response = client.post("/api/v1/ai/test")
    assert response.status_code == 200
    assert response.json()["model"] == "server-model"
    assert seen[0].get_header("Authorization") == "Bearer server-secret"
    response = client.post("/api/v1/ai/test", headers={"X-AI-Provider": "openai-compatible",
                           "X-AI-Model": "local", "X-AI-Base-Url": "http://localhost:1234/v1"})
    assert response.status_code == 200
    assert response.json() == {"ok": True, "provider": "openai-compatible", "model": "local"}
    assert seen[1].get_header("Authorization") is None


def test_environment_compatible_base_url(real_ai, monkeypatch):
    client, _ = real_ai
    for name, value in {"PROVIDER": "openai-compatible", "MODEL": "local:latest",
                        "BASE_URL": "http://localhost:11434"}.items():
        monkeypatch.setenv(f"PROJECTLENS_AI_{name}", value)

    def open_request(request, *, timeout):
        assert request.full_url == "http://localhost:11434/v1/chat/completions"
        return _chat_bytes()

    monkeypatch.setattr(clients, "urlopen", open_request)
    assert client.post("/api/v1/ai/test").status_code == 200


@pytest.mark.parametrize("headers", [
    {"X-AI-Provider": "unsupported"}, {"X-AI-Model": "model-only"},
    {"X-AI-Provider": "openai", "X-AI-Model": "bad model"},
    {"X-AI-Provider": "openai", "X-AI-Key": "x" * 4097},
    {"X-AI-Provider": "openai", "X-AI-Base-Url": "https://example.org"},
    {"X-AI-Provider": "openai-compatible", "X-AI-Model": "local",
     "X-AI-Base-Url": "https://user:secret@example.org"},
    [("X-AI-Provider", "openai"), ("X-AI-Provider", "anthropic")],
])
@pytest.mark.parametrize("endpoint", ["test", "explain"])
def test_invalid_headers_have_safe_envelope(real_ai, monkeypatch, caplog, headers, endpoint):
    client, project_id = real_ai

    def unexpected(*args, **kwargs):
        pytest.fail("Invalid headers must not make a network request")

    monkeypatch.setattr(clients, "urlopen", unexpected)
    url = "/api/v1/ai/test" if endpoint == "test" else f"/api/v1/projects/{project_id}/ai/explanations"
    response = client.post(url, headers=headers, json={"kind": "repository"})
    assert response.status_code == 422
    assert response.json() == {"error": {"code": "validation_error",
                                       "message": "Invalid AI provider headers or environment configuration."}}
    assert "user:secret" not in response.text and "user:secret" not in caplog.text


@pytest.mark.parametrize("endpoint", ["test", "explain"])
@pytest.mark.parametrize("failure,status,code,attempts", [
    (401, 401, "ai_auth_failed", 1), (403, 401, "ai_auth_failed", 1),
    (429, 503, "ai_unavailable", 2), (500, 503, "ai_unavailable", 2),
    (504, 503, "ai_timeout", 1), (400, 502, "ai_invalid_response", 1),
    ("timeout", 503, "ai_timeout", 1), ("network", 503, "ai_unavailable", 2),
    ("invalid", 502, "ai_invalid_response", 1), ("echo", 502, "ai_invalid_response", 1),
])
def test_errors_do_not_expose_keys(real_ai, monkeypatch, caplog, endpoint, failure, status, code, attempts):
    client, project_id = real_ai
    key = "sk-do-not-store-or-log"
    calls = []

    def fail(request, *, timeout):
        calls.append(request)
        if failure == "timeout":
            raise TimeoutError(key)
        if failure == "network":
            raise URLError(key)
        if failure == "invalid":
            return io.BytesIO(b"bad json")
        if failure == "echo":
            return _chat_bytes(key)
        raise HTTPError(request.full_url, failure, key, {"secret": key}, io.BytesIO(key.encode()))

    monkeypatch.setattr(clients, "urlopen", fail)
    url = "/api/v1/ai/test" if endpoint == "test" else f"/api/v1/projects/{project_id}/ai/explanations"
    response = client.post(url, headers={"X-AI-Provider": "openai", "X-AI-Key": key}, json={"kind": "risk"})
    assert response.status_code == status
    assert response.json()["error"]["code"] == code
    assert len(calls) == attempts
    assert key not in response.text and key not in caplog.text
    assert all(key not in record.getMessage() for record in caplog.records)


def test_real_explanation_sends_bounded_context(real_ai, monkeypatch):
    client, project_id = real_ai

    def open_request(request, *, timeout):
        payload = json.loads(request.data)
        assert payload["max_tokens"] == 512
        assert "<projectlens_context>" in payload["messages"][1]["content"]
        assert "src/a.py" in payload["messages"][1]["content"]
        return _chat_bytes("Explanation [file:src/a.py]")

    monkeypatch.setattr(clients, "urlopen", open_request)
    response = client.post(f"/api/v1/projects/{project_id}/ai/explanations", json={"kind": "repository"},
                           headers={"X-AI-Provider": "openai-compatible", "X-AI-Model": "local",
                                    "X-AI-Base-Url": "http://localhost:1234"})
    assert response.status_code == 200
    assert response.json()["usage"]["model"] == "local"


def test_connection_test_respects_disabled_gate(real_ai, monkeypatch):
    client, _ = real_ai
    monkeypatch.delenv("AI_ENABLED", raising=False)
    response = client.post("/api/v1/ai/test")
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "ai_disabled"


def test_missing_key_maps_auth_failure(real_ai):
    client, _ = real_ai
    response = client.post("/api/v1/ai/test", headers={"X-AI-Provider": "openai"})
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "ai_auth_failed"


def test_user_supplied_credentials_opt_in_even_when_ai_disabled(real_ai, monkeypatch):
    """AI_ENABLED stays off, but a request carrying its own provider headers is not rejected as disabled."""
    client, _ = real_ai
    monkeypatch.delenv("AI_ENABLED", raising=False)
    monkeypatch.setattr(clients, "urlopen", lambda *args, **kwargs: _chat_bytes())
    plain = client.post("/api/v1/ai/test")
    assert plain.status_code == 503 and plain.json()["error"]["code"] == "ai_disabled"
    headers = {"X-AI-Provider": "openai-compatible", "X-AI-Base-Url": "http://127.0.0.1:9", "X-AI-Model": "m"}
    response = client.post("/api/v1/ai/test", headers=headers)
    assert response.status_code == 200 and response.json()["ok"] is True
