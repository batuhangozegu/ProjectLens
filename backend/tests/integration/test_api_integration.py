import subprocess
import json
from concurrent.futures import Future

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")
pytest.importorskip("sqlalchemy")

from fastapi.testclient import TestClient
from projectlens.app.api import APISettings, create_app
from projectlens.app.db.models import Base
from projectlens.app.db.repository import create_analysis_job, create_project
from projectlens.app.db.session import create_db_engine, create_session_factory
from projectlens.analysis.models import AnalysisOptions
from projectlens.analysis.pipeline import analyze
from projectlens.git.checkout import checkout_repository


class InlineExecutor:
    def submit(self, fn, *args):
        future = Future()
        try:
            future.set_result(fn(*args))
        except BaseException as exc:
            future.set_exception(exc)
        return future

    def shutdown(self, **_kwargs):
        pass


class HoldingExecutor:
    def submit(self, fn, *args):
        self.task = (fn, args)
        return Future()

    def shutdown(self, **_kwargs):
        pass


@pytest.fixture
def api_factory(tmp_path, test_database):
    database_url = test_database["url"]
    engine = create_db_engine(database_url=database_url)
    Base.metadata.create_all(engine)
    source = tmp_path / "repo"
    source.mkdir()
    (source / "module.py").write_text("def hello():\n    return 'hi'\n", encoding="utf-8")
    subprocess.run(["git", "init", "-q", str(source)], check=True)
    subprocess.run(["git", "-C", str(source), "config", "user.email", "test@example.invalid"], check=True)
    subprocess.run(["git", "-C", str(source), "config", "user.name", "Test"], check=True)
    subprocess.run(["git", "-C", str(source), "add", "module.py"], check=True)
    subprocess.run(["git", "-C", str(source), "commit", "-qm", "initial"], check=True)
    commit = subprocess.check_output(["git", "-C", str(source), "rev-parse", "HEAD"], text=True).strip()

    def checkout(url, *, ref=None, commit=None, **kwargs):
        return checkout_repository(url, ref=ref, commit=commit, _clone_url_override=str(source), **kwargs)

    yield database_url, source, commit, checkout
    engine.dispose()


def _client(api_factory, *, executor=None, checkout=None, max_workers=2, max_queue=8):
    database_url, _source, _commit, default_checkout = api_factory
    app = create_app(
        APISettings(database_url=database_url, max_workers=max_workers, max_queue=max_queue),
        checkout_function=checkout or default_checkout,
        executor=executor or InlineExecutor(),
    )
    return TestClient(app)


def test_create_job_snapshot_and_idempotency(api_factory):
    _db, source, commit, checkout = api_factory
    with _client(api_factory, checkout=checkout) as client:
        body = {"repository_url": "https://github.com/example/repo.git", "commit": commit}
        created = client.post("/api/v1/projects", json=body)
        assert created.status_code == 202
        accepted = created.json()
        assert accepted["status"] == "succeeded"
        job = client.get(accepted["job_url"]).json()
        assert job["status"] == "succeeded"
        assert job["snapshot_id"]
        again = client.post("/api/v1/projects", json={"repository_url": "https://github.com/example/repo/", "commit": commit})
        assert again.status_code == 202
        assert again.json()["project_id"] == accepted["project_id"]
        assert client.get(again.json()["job_url"]).json()["snapshot_id"] == job["snapshot_id"]
        project_id = accepted["project_id"]
        listing = client.get(f"/api/v1/projects/{project_id}/snapshots").json()
        assert len(listing["items"]) == 1
        full = client.get(f"/api/v1/projects/{project_id}/snapshots/latest").json()
        expected = json.loads(analyze(AnalysisOptions(str(source))).to_json())
        # The source repo has a .git directory; the checkout analyzed by the job does not.
        expected["diagnostics"] = [d for d in expected["diagnostics"] if d.get("file") != ".git"]
        assert full == expected
        assert client.get(f"/api/v1/projects/{project_id}/snapshots/{job['snapshot_id']}").json() == full
        assert client.get("/api/v1/health").json() == {"status": "ok", "database": "ok"}


@pytest.mark.parametrize("url", [
    "ssh://git@github.com/example/repo", "http://github.com/example/repo",
    "https://evil.example/example/repo", "https://user:pass@github.com/example/repo",
    "https://github.com/example/repo?x=<script>",
])
def test_invalid_url_returns_safe_error_envelope(api_factory, url):
    with _client(api_factory) as client:
        response = client.post("/api/v1/projects", json={"repository_url": url})
        assert response.status_code == 422
        assert response.json()["error"]["code"] == "invalid_repository_url"
        assert set(response.json()) == {"error"}


def test_failed_checkout_and_unknown_resources_are_safe(api_factory):
    def bad_checkout(*_args, **_kwargs):
        raise RuntimeError("C:\\private\\secret\\stacktrace")
    with _client(api_factory, checkout=bad_checkout) as client:
        created = client.post("/api/v1/projects", json={"repository_url": "https://github.com/example/repo"}).json()
        job = client.get(created["job_url"]).json()
        assert job["status"] == "failed"
        assert job["error_code"] == "analysis_failed"
        assert "private" not in job["error_message"]
        for path in ("/api/v1/projects/999", "/api/v1/projects/999/snapshots/latest", "/api/v1/projects/999/snapshots/999", "/api/v1/jobs/999"):
            response = client.get(path)
            assert response.status_code == 404
            assert set(response.json()) == {"error"}


def test_timeout_code_cleanup_and_pagination_bounds(api_factory):
    cleaned_paths = []
    _db, source, _commit, _checkout = api_factory

    def timed_checkout(url, **kwargs):
        result = checkout_repository(url, ref=kwargs.get("ref"), commit=kwargs.get("commit"),
                                     _clone_url_override=str(source), timeout=kwargs["timeout"], max_bytes=kwargs["max_bytes"])
        cleaned_paths.append(result.path)
        from projectlens.git.checkout import CheckoutTimeout
        result.cleanup()
        raise CheckoutTimeout("private path must not escape")

    with _client(api_factory, checkout=timed_checkout) as client:
        created = client.post("/api/v1/projects", json={"repository_url": "https://github.com/example/repo"}).json()
        job = client.get(created["job_url"]).json()
        assert job["status"] == "failed"
        assert job["error_code"] == "checkout_timeout"
        assert "private" not in job["error_message"]
        assert cleaned_paths and not cleaned_paths[0].exists()
        for params in ({"limit": 0}, {"limit": 101}, {"offset": 10001}):
            response = client.get(f"/api/v1/projects/{created['project_id']}/snapshots", params=params)
            assert response.status_code == 422
            assert response.json()["error"]["code"] == "validation_error"


def test_startup_marks_orphaned_jobs_interrupted(api_factory):
    database_url, _source, _commit, checkout = api_factory
    engine = create_db_engine(database_url=database_url)
    factory = create_session_factory(engine)
    with factory() as session, session.begin():
        project = create_project(session, "Orphan", canonical_repository_url="https://github.com/example/orphan")
        job = create_analysis_job(session, project.id, branch="main", commit=None)
        job_id = job.id
    engine.dispose()

    with _client(api_factory, checkout=checkout) as client:
        job = client.get(f"/api/v1/jobs/{job_id}").json()
        assert job["status"] == "failed"
        assert job["error_code"] == "interrupted"


def test_queue_full_and_duplicate_active_reuse(api_factory):
    held = HoldingExecutor()
    with _client(api_factory, executor=held, max_workers=1, max_queue=0) as client:
        body = {"repository_url": "https://github.com/example/repo"}
        first = client.post("/api/v1/projects", json=body)
        second = client.post("/api/v1/projects", json=body)
        assert first.status_code == second.status_code == 202
        assert first.json()["job_id"] == second.json()["job_id"]
        full = client.post("/api/v1/projects/1/analyses", json={"branch": "other"})
        assert full.status_code == 503
        assert full.headers["retry-after"] == "5"
        assert full.json()["error"]["code"] == "queue_full"
