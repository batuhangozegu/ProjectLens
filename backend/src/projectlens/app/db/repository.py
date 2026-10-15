"""Synchronous persistence operations; transaction ownership stays with callers."""

from __future__ import annotations

import re
import unicodedata
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .models import AnalysisJob, AnalysisSnapshot, Project, Task
from .task_status import validate_transition


class ProjectNotFoundError(LookupError):
    """Raised when a snapshot is requested for a project absent from the database."""


class DuplicateSnapshotError(ValueError):
    """Raised when a project already has this commit/schema snapshot."""


class TaskNotFoundError(LookupError):
    """Raised when a task is absent or does not belong to the requested project."""


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


def create_task(session: Session, project_id: int, *, title: str, description: str | None = None,
                status: str = "TODO", priority: str = "MEDIUM", category: str | None = None,
                position: int | None = None, source: str = "manual", source_key: str | None = None) -> Task:
    if session.get(Project, project_id) is None:
        raise ProjectNotFoundError(f"project {project_id!r} does not exist")
    if category is not None:
        category = category.strip() or None
    if position is None:
        max_position = session.scalar(select(func.max(Task.position)).where(Task.project_id == project_id))
        position = 0 if max_position is None else max_position + 1
    task = Task(project_id=project_id, title=title, description=description, status=status, priority=priority,
                category=category, position=position, source=source, source_key=source_key,
                completed_at=datetime.now(timezone.utc) if status == "DONE" else None)
    session.add(task)
    session.flush()
    return task


def get_task(session: Session, project_id: int, task_id: int) -> Task:
    task = session.scalar(select(Task).where(Task.project_id == project_id, Task.id == task_id))
    if task is None:
        if session.get(Project, project_id) is None:
            raise ProjectNotFoundError(f"project {project_id!r} does not exist")
        raise TaskNotFoundError(f"task {task_id!r} does not exist in project {project_id!r}")
    return task


def list_tasks(session: Session, project_id: int, *, status: list[str] | None = None,
               priority: str | None = None, category: str | None = None, search: str | None = None,
               limit: int = 20, offset: int = 0) -> tuple[list[Task], int]:
    if session.get(Project, project_id) is None:
        raise ProjectNotFoundError(f"project {project_id!r} does not exist")
    if not 1 <= limit <= 100 or not 0 <= offset <= 10000:
        raise ValueError("limit must be 1..100 and offset must be 0..10000")
    query = select(Task).where(Task.project_id == project_id)
    if status:
        query = query.where(Task.status.in_(status))
    if priority:
        query = query.where(Task.priority == priority)
    if category:
        query = query.where(Task.category == category.strip())
    if search:
        query = query.where(Task.title.ilike(f"%{search}%"))
    total = session.scalar(select(func.count()).select_from(query.subquery())) or 0
    items = list(session.scalars(query.order_by(Task.position, Task.id).offset(offset).limit(limit)))
    return items, total


def update_task(session: Session, project_id: int, task_id: int, changes: dict[str, Any]) -> Task:
    task = get_task(session, project_id, task_id)
    if "status" in changes:
        next_status = changes["status"]
        validate_transition(task.status, next_status)
        if next_status != task.status:
            now = datetime.now(timezone.utc)
            task.completed_at = now if next_status == "DONE" else None
            task.status = next_status
    for key in ("title", "description", "priority", "category", "position"):
        if key in changes:
            value = changes[key]
            if key == "category" and value is not None:
                value = value.strip() or None
            setattr(task, key, value)
    session.flush()
    return task


def delete_task(session: Session, project_id: int, task_id: int) -> None:
    session.delete(get_task(session, project_id, task_id))
    session.flush()
