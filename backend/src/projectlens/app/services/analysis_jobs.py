"""Persisted analysis jobs and bounded in-process execution."""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from threading import BoundedSemaphore, Lock
from typing import Callable
from sqlalchemy.exc import IntegrityError

from projectlens.analysis.models import AnalysisOptions
from projectlens.analysis.pipeline import analyze
from projectlens.app.db.models import AnalysisJob, Project
from projectlens.app.db.repository import (
    DuplicateSnapshotError, add_snapshot, get_snapshot_by_identity,
)
from projectlens.git.checkout import CheckoutError, CheckoutTimeout, checkout_repository


class QueueFullError(RuntimeError):
    pass


class AnalysisJobManager:
    def __init__(self, session_factory, *, max_workers: int = 2, max_queue: int = 8,
                 checkout_timeout: float = 120.0, checkout_max_bytes: int = 512 * 1024 * 1024,
                 checkout_function: Callable | None = None, executor=None):
        self.session_factory = session_factory
        self.max_workers = max(1, max_workers)
        self.max_queue = max(0, max_queue)
        self.timeout = checkout_timeout
        self.max_bytes = checkout_max_bytes
        self.checkout = checkout_function or checkout_repository
        self.executor = executor or ThreadPoolExecutor(max_workers=self.max_workers, thread_name_prefix="projectlens-analysis")
        self._slots = BoundedSemaphore(self.max_workers + self.max_queue)
        self.enqueue_lock = Lock()

    def reserve(self) -> None:
        if not self._slots.acquire(blocking=False):
            raise QueueFullError

    def submit(self, job_id: int) -> None:
        try:
            self.executor.submit(self._run, job_id)
        except BaseException:
            self._slots.release()
            with self.session_factory() as session, session.begin():
                job = session.get(AnalysisJob, job_id)
                if job:
                    self._fail(job, "worker_unavailable", "Analysis could not be scheduled.")
            raise

    @staticmethod
    def _fail(job: AnalysisJob, code: str, message: str) -> None:
        job.status = "failed"
        job.error_code = code
        job.error_message = message
        job.finished_at = datetime.now(timezone.utc)

    def _run(self, job_id: int) -> None:
        checkout = None
        try:
            with self.session_factory() as session, session.begin():
                job = session.get(AnalysisJob, job_id)
                if job is None or job.status != "queued":
                    return
                project = session.get(Project, job.project_id)
                if project is None:
                    self._fail(job, "project_missing", "The project is no longer available.")
                    return
                job.status = "running"
                job.started_at = datetime.now(timezone.utc)
                url, branch, commit = project.canonical_repository_url, job.branch, job.requested_commit
                default_branch = project.default_branch

            checkout = self.checkout(url, ref=branch if commit is None else None,
                                     commit=commit, timeout=self.timeout, max_bytes=self.max_bytes)
            resolved_branch = checkout.branch or branch or default_branch
            result = analyze(AnalysisOptions(root_path=str(checkout.path)))
            with self.session_factory() as session, session.begin():
                job = session.get(AnalysisJob, job_id)
                if job is None:
                    return
                snapshot = get_snapshot_by_identity(session, job.project_id, checkout.resolved_commit, result.schema_version)
                if snapshot is None:
                    try:
                        with session.begin_nested():
                            snapshot = get_snapshot_by_identity(session, job.project_id, checkout.resolved_commit, result.schema_version)
                            if snapshot is None:
                                snapshot = add_snapshot(session, job.project_id, result, branch=resolved_branch, commit=checkout.resolved_commit)
                    except (DuplicateSnapshotError, IntegrityError):
                        snapshot = get_snapshot_by_identity(session, job.project_id, checkout.resolved_commit, result.schema_version)
                if snapshot is None:
                    self._fail(job, "analysis_failed", "Analysis could not be saved.")
                else:
                    job.snapshot_id = snapshot.id
                    job.status = "succeeded"
                    job.finished_at = datetime.now(timezone.utc)
        except CheckoutTimeout:
            self._record_failure(job_id, "checkout_timeout", "Repository checkout exceeded its time limit.")
        except CheckoutError:
            self._record_failure(job_id, "checkout_failed", "Repository checkout failed or exceeded a safety limit.")
        except (ValueError, TypeError):
            self._record_failure(job_id, "invalid_ref", "The requested branch or commit could not be checked out.")
        except Exception:
            self._record_failure(job_id, "analysis_failed", "Analysis could not be completed.")
        finally:
            if checkout is not None:
                try:
                    checkout.cleanup()
                except Exception:
                    pass
            self._slots.release()

    def _record_failure(self, job_id: int, code: str, message: str) -> None:
        with self.session_factory() as session, session.begin():
            job = session.get(AnalysisJob, job_id)
            if job is not None and job.status not in {"succeeded", "failed"}:
                self._fail(job, code, message)

    def shutdown(self) -> None:
        shutdown = getattr(self.executor, "shutdown", None)
        if shutdown:
            shutdown(wait=False, cancel_futures=False)
