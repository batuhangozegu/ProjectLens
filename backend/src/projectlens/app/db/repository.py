"""Synchronous persistence operations; transaction ownership stays with callers."""

from __future__ import annotations

import re
import unicodedata
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import AnalysisJob, AnalysisSnapshot, Project


class ProjectNotFoundError(LookupError):
    """Raised when a snapshot is requested for a project absent from the database."""


class DuplicateSnapshotError(ValueError):
    """Raised when a project already has this commit/schema snapshot."""


def _slugify(name: str) -> str:
    value = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode("ascii").lower()
    value = re.sub(r"[^a-z0-9]+", "-", value).strip("-")
    if not value:
        raise ValueError("project name must produce a non-empty slug")
    return value[:200].rstrip("-")


def create_project(
    session: Session,
    name: str,
    *,
    slug: str | None = None,
    canonical_repository_url: str | None = None,
    default_branch: str = "main",
) -> Project:
    project = Project(
        name=name,
        slug=slug or _slugify(name),
        canonical_repository_url=canonical_repository_url,
        default_branch=default_branch,
    )
    session.add(project)
    session.flush()
    return project


def get_project(session: Session, *, project_id: int | None = None, slug: str | None = None) -> Project | None:
    if (project_id is None) == (slug is None):
        raise ValueError("provide exactly one of project_id or slug")
    return session.get(Project, project_id) if project_id is not None else session.scalar(
        select(Project).where(Project.slug == slug)
    )


def list_projects(session: Session) -> list[Project]:
    return list(session.scalars(select(Project).order_by(Project.name, Project.id)))


def get_project_by_repository(session: Session, canonical_url: str) -> Project | None:
    return session.scalar(select(Project).where(Project.canonical_repository_url == canonical_url))


def list_project_snapshots(session: Session, project_id: int, *, limit: int = 20, offset: int = 0) -> list[AnalysisSnapshot]:
    return list(session.scalars(
        select(AnalysisSnapshot).where(AnalysisSnapshot.project_id == project_id)
        .order_by(AnalysisSnapshot.created_at.desc(), AnalysisSnapshot.id.desc())
        .offset(offset).limit(limit)
    ))


def get_snapshot_for_project(session: Session, project_id: int, snapshot_id: int) -> AnalysisSnapshot | None:
    return session.scalar(select(AnalysisSnapshot).where(
        AnalysisSnapshot.project_id == project_id, AnalysisSnapshot.id == snapshot_id
    ))


def get_snapshot_record(session: Session, snapshot_id: int) -> AnalysisSnapshot | None:
    return session.get(AnalysisSnapshot, snapshot_id)


def get_snapshot_by_identity(session: Session, project_id: int, commit: str, schema_version: str) -> AnalysisSnapshot | None:
    return session.scalar(select(AnalysisSnapshot).where(
        AnalysisSnapshot.project_id == project_id,
        AnalysisSnapshot.commit_sha == commit.lower(),
        AnalysisSnapshot.analyzer_schema_version == schema_version,
    ))


def create_analysis_job(session: Session, project_id: int, *, branch: str | None, commit: str | None) -> AnalysisJob:
    job = AnalysisJob(project_id=project_id, branch=branch, requested_commit=commit, status="queued")
    session.add(job)
    session.flush()
    return job


def get_analysis_job(session: Session, job_id: int) -> AnalysisJob | None:
    return session.get(AnalysisJob, job_id)


def find_active_job(session: Session, project_id: int, branch: str | None, commit: str | None) -> AnalysisJob | None:
    query = select(AnalysisJob).where(
        AnalysisJob.project_id == project_id,
        AnalysisJob.status.in_(("queued", "running")),
    )
    if commit is not None:
        query = query.where(AnalysisJob.requested_commit == commit.lower())
    else:
        query = query.where(AnalysisJob.requested_commit.is_(None), AnalysisJob.branch == branch)
    return session.scalar(query.order_by(AnalysisJob.id.desc()).limit(1))


def mark_orphaned_jobs_interrupted(session: Session) -> int:
    from datetime import datetime, timezone
    jobs = list(session.scalars(select(AnalysisJob).where(AnalysisJob.status.in_(("queued", "running")))))
    now = datetime.now(timezone.utc)
    for job in jobs:
        job.status = "failed"
        job.error_code = "interrupted"
        job.error_message = "Analysis was interrupted by an application restart."
        job.finished_at = now
    return len(jobs)


def _result_dict(result: Any) -> dict[str, Any]:
    if hasattr(result, "to_dict") and callable(result.to_dict):
        value = result.to_dict()
    elif isinstance(result, dict):
        value = result
    else:
        raise TypeError("result must be an AnalysisResult or a result dictionary")
    if not isinstance(value, dict):
        raise TypeError("AnalysisResult.to_dict() must return a dictionary")
    return value


def add_snapshot(
    session: Session,
    project: Project | int,
    result: Any,
    *,
    branch: str,
    commit: str,
    status: str | None = None,
) -> AnalysisSnapshot:
    project_id = project.id if isinstance(project, Project) else project
    if session.get(Project, project_id) is None:
        raise ProjectNotFoundError(f"project {project_id!r} does not exist")
    if len(commit) not in (40, 64) or not re.fullmatch(r"[0-9a-fA-F]+", commit):
        raise ValueError("commit must be a full 40- or 64-character hexadecimal SHA")
    data = _result_dict(result)
    schema_version = str(data["schema_version"])
    existing = session.scalar(
        select(AnalysisSnapshot).where(
            AnalysisSnapshot.project_id == project_id,
            AnalysisSnapshot.commit_sha == commit.lower(),
            AnalysisSnapshot.analyzer_schema_version == schema_version,
        )
    )
    if existing is not None:
        raise DuplicateSnapshotError(
            f"snapshot already exists for project {project_id}, commit {commit.lower()}, schema {schema_version}"
        )
    partial = bool(data.get("partial", False))
    resolved_status = status or ("partial" if partial else "completed")
    if resolved_status not in {"completed", "partial", "failed"}:
        raise ValueError("status must be completed, partial, or failed")
    metrics = data.get("metrics") or {}
    dependencies = metrics.get("dependencies") or {}
    snapshot = AnalysisSnapshot(
        project_id=project_id,
        branch=branch,
        commit_sha=commit.lower(),
        status=resolved_status,
        analyzer_schema_version=schema_version,
        partial=partial,
        result_json=data,
        file_count=int(metrics.get("total_file_count", 0)),
        python_file_count=int(metrics.get("python_file_count", 0)),
        python_loc=int((metrics.get("python_loc") or {}).get("total", 0)),
        edge_count=int(dependencies.get("edge_count", len(data.get("dependency_edges", ())))),
        cycle_group_count=int(dependencies.get("cycle_group_count", len(data.get("cycles", ())))),
        diagnostic_count=len(data.get("diagnostics", ())),
    )
    session.add(snapshot)
    session.flush()
    return snapshot


def get_latest_snapshot(session: Session, project: Project | int) -> AnalysisSnapshot | None:
    project_id = project.id if isinstance(project, Project) else project
    return session.scalar(
        select(AnalysisSnapshot)
        .where(AnalysisSnapshot.project_id == project_id)
        .order_by(AnalysisSnapshot.created_at.desc(), AnalysisSnapshot.id.desc())
        .limit(1)
    )


def list_snapshots(session: Session, project: Project | int) -> list[AnalysisSnapshot]:
    project_id = project.id if isinstance(project, Project) else project
    return list(session.scalars(
        select(AnalysisSnapshot)
        .where(AnalysisSnapshot.project_id == project_id)
        .order_by(AnalysisSnapshot.created_at.desc(), AnalysisSnapshot.id.desc())
    ))


def get_snapshot(session: Session, snapshot_id: int) -> dict[str, Any] | None:
    snapshot = session.get(AnalysisSnapshot, snapshot_id)
    return None if snapshot is None else snapshot.result_json
