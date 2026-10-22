"""Synchronous persistence operations; transaction ownership stays with callers."""

from __future__ import annotations

import re
import unicodedata
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .models import AcceptanceCriterion, AnalysisJob, AnalysisSnapshot, Project, Task, TaskFileLink
from .task_status import validate_transition
from projectlens.app.path_validation import normalize_task_path
from projectlens.app.criteria_validation import validate_criterion_params


class ProjectNotFoundError(LookupError):
    """Raised when a snapshot is requested for a project absent from the database."""


class DuplicateSnapshotError(ValueError):
    """Raised when a project already has this commit/schema snapshot."""


class TaskNotFoundError(LookupError):
    """Raised when a task is absent or does not belong to the requested project."""


class TaskItemNotFoundError(LookupError):
    """Raised when an item is absent from the scoped task."""


class TaskFileLinkNotFoundError(TaskItemNotFoundError):
    pass


class AcceptanceCriterionNotFoundError(TaskItemNotFoundError):
    pass


class ResourceLimitError(ValueError):
    def __init__(self, resource: str):
        self.resource = resource
        super().__init__(f"task {resource} limit reached")


class DuplicateLinkError(ValueError):
    pass


def _enforce_item_limit(session: Session, model, task_id: int, resource: str) -> None:
    count = session.scalar(select(func.count()).select_from(model).where(model.task_id == task_id)) or 0
    if count >= 50:
        raise ResourceLimitError(resource)


def _lock_task(session: Session, project_id: int, task_id: int) -> Task:
    task = get_task(session, project_id, task_id)
    # Serialize per-task inserts on PostgreSQL so concurrent writers cannot
    # pass the bounded-item check together; SQLite ignores FOR UPDATE.
    return session.scalar(select(Task).where(Task.id == task.id).with_for_update()) or task


def create_task_file_link(session: Session, project_id: int, task_id: int, path: str) -> TaskFileLink:
    task = _lock_task(session, project_id, task_id)
    normalized = normalize_task_path(path)
    if session.scalar(select(TaskFileLink.id).where(TaskFileLink.task_id == task.id, TaskFileLink.path == normalized)) is not None:
        raise DuplicateLinkError("duplicate task file link")
    _enforce_item_limit(session, TaskFileLink, task.id, "links")
    item = TaskFileLink(task_id=task.id, path=normalized)
    session.add(item); session.flush()
    return item


def list_task_file_links(session: Session, project_id: int, task_id: int) -> list[TaskFileLink]:
    task = get_task(session, project_id, task_id)
    return list(session.scalars(select(TaskFileLink).where(TaskFileLink.task_id == task.id).order_by(TaskFileLink.id)))


def get_task_file_link(session: Session, project_id: int, task_id: int, link_id: int) -> TaskFileLink:
    task = get_task(session, project_id, task_id)
    item = session.scalar(select(TaskFileLink).where(TaskFileLink.id == link_id, TaskFileLink.task_id == task.id))
    if item is None:
        raise TaskFileLinkNotFoundError("task file link not found")
    return item


def delete_task_file_link(session: Session, project_id: int, task_id: int, link_id: int) -> None:
    item = get_task_file_link(session, project_id, task_id, link_id)
    session.delete(item); session.flush()


def create_acceptance_criterion(session: Session, project_id: int, task_id: int, *, kind: str,
                                params: dict, description: str = "", attested: bool | None = None,
                                position: int | None = None) -> AcceptanceCriterion:
    task = _lock_task(session, project_id, task_id)
    normalized = validate_criterion_params(kind, params)
    if kind != "manual_attestation" and attested is not None:
        raise ValueError("attested is allowed only for manual_attestation criteria")
    if attested is not None and type(attested) is not bool:
        raise ValueError("attested must be a boolean or null")
    _enforce_item_limit(session, AcceptanceCriterion, task.id, "criteria")
    if position is None:
        maximum = session.scalar(select(func.max(AcceptanceCriterion.position)).where(AcceptanceCriterion.task_id == task.id))
        position = 0 if maximum is None else maximum + 1
    item = AcceptanceCriterion(task_id=task.id, kind=kind, params=normalized, description=description,
                               attested=attested, position=position)
    session.add(item); session.flush()
    return item


def list_acceptance_criteria(session: Session, project_id: int, task_id: int) -> list[AcceptanceCriterion]:
    task = get_task(session, project_id, task_id)
    return list(session.scalars(select(AcceptanceCriterion).where(AcceptanceCriterion.task_id == task.id)
                                .order_by(AcceptanceCriterion.position, AcceptanceCriterion.id)))


def get_acceptance_criterion(session: Session, project_id: int, task_id: int, criterion_id: int) -> AcceptanceCriterion:
    task = get_task(session, project_id, task_id)
    item = session.scalar(select(AcceptanceCriterion).where(AcceptanceCriterion.id == criterion_id,
                            AcceptanceCriterion.task_id == task.id))
    if item is None:
        raise AcceptanceCriterionNotFoundError("acceptance criterion not found")
    return item


def update_acceptance_criterion(session: Session, project_id: int, task_id: int, criterion_id: int,
                                changes: dict) -> AcceptanceCriterion:
    item = get_acceptance_criterion(session, project_id, task_id, criterion_id)
    if "kind" in changes:
        raise ValueError("criterion kind is immutable")
    if "params" in changes:
        changes = dict(changes)
        changes["params"] = validate_criterion_params(item.kind, changes["params"])
    if "attested" in changes and item.kind != "manual_attestation":
        raise ValueError("attested is allowed only for manual_attestation criteria")
    if "attested" in changes and changes["attested"] is not None and type(changes["attested"]) is not bool:
        raise ValueError("attested must be a boolean or null")
    for key, value in changes.items():
        setattr(item, key, value)
    session.flush()
    return item


def delete_acceptance_criterion(session: Session, project_id: int, task_id: int, criterion_id: int) -> None:
    session.delete(get_acceptance_criterion(session, project_id, task_id, criterion_id)); session.flush()


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


def delete_project(session: Session, project_id: int) -> bool:
    """Delete a project and flush its database cascades; commit belongs to caller."""
    project = get_project(session, project_id=project_id)
    if project is None:
        return False
    session.delete(project)
    session.flush()
    return True


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


def find_active_project_job(session: Session, project_id: int) -> AnalysisJob | None:
    """Return the newest queued or running job for a project, regardless of ref."""
    return session.scalar(
        select(AnalysisJob)
        .where(AnalysisJob.project_id == project_id, AnalysisJob.status.in_(("queued", "running")))
        .order_by(AnalysisJob.id.desc())
        .limit(1)
    )


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


def get_imported_tasks_by_keys(session: Session, project_id: int, source_keys: set[str]) -> dict[str, Task]:
    """Load imported tasks matching checklist keys for one project."""
    if not source_keys:
        return {}
    tasks = session.scalars(
        select(Task).where(
            Task.project_id == project_id,
            Task.source == "import",
            Task.source_key.in_(source_keys),
        )
    )
    return {task.source_key: task for task in tasks if task.source_key is not None}


def list_imported_tasks(session: Session, project_id: int) -> list[Task]:
    """List imported tasks in stable document/insertion order."""
    return list(session.scalars(
        select(Task).where(Task.project_id == project_id, Task.source == "import")
        .order_by(Task.position, Task.id)
    ))


def get_max_task_position(session: Session, project_id: int) -> int | None:
    """Return the current highest position for a project's tasks."""
    return session.scalar(select(func.max(Task.position)).where(Task.project_id == project_id))


def iter_task_progress_fields(session: Session, project_id: int, *, source: str | None = None):
    """Stream only the task fields needed for progress calculation."""
    query = select(Task.status, Task.category, Task.priority).where(Task.project_id == project_id)
    if source is not None:
        query = query.where(Task.source == source)
    return session.execute(query.execution_options(yield_per=500))


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
