"""SQLAlchemy persistence models, separate from analysis dataclasses."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    JSON,
    MetaData,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.types import TypeDecorator


NAMING_CONVENTION = {
    "ix": "ix_%(table_name)s_%(column_0_name)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class UTCDateTime(TypeDecorator):
    """Store UTC values portably and restore timezone awareness on SQLite reads."""

    impl = DateTime
    cache_ok = True

    def __init__(self):
        super().__init__(timezone=True)

    def process_bind_param(self, value: datetime | None, _dialect):
        if value is None:
            return None
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)

    def process_result_value(self, value: datetime | None, _dialect):
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)


class JSONObject(TypeDecorator):
    """JSON storage that keeps criterion params as objects on every dialect."""

    impl = JSON
    cache_ok = True

    def process_bind_param(self, value, _dialect):
        if value is not None and not isinstance(value, dict):
            raise ValueError("JSON value must be an object")
        return value


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)


class Project(Base):
    __tablename__ = "projects"
    __table_args__ = (
        UniqueConstraint("slug"),
        UniqueConstraint("canonical_repository_url", name="uq_project_canonical_repository_url"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    slug: Mapped[str] = mapped_column(String(200), nullable=False)
    canonical_repository_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    default_branch: Mapped[str] = mapped_column(String(255), nullable=False, default="main")
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        UTCDateTime(), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    snapshots: Mapped[list[AnalysisSnapshot]] = relationship(
        back_populates="project", cascade="all, delete-orphan", passive_deletes=True
    )
    tasks: Mapped[list[Task]] = relationship(back_populates="project", cascade="all, delete-orphan", passive_deletes=True)


class AnalysisSnapshot(Base):
    __tablename__ = "analysis_snapshots"
    __table_args__ = (
        UniqueConstraint("project_id", "commit_sha", "analyzer_schema_version", name="uq_snapshot_identity"),
        CheckConstraint("status IN ('completed', 'partial', 'failed')", name="snapshot_status_valid"),
        Index("ix_snapshot_project_created", "project_id", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    branch: Mapped[str] = mapped_column(String(255), nullable=False)
    commit_sha: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    analyzer_schema_version: Mapped[str] = mapped_column(String(32), nullable=False)
    partial: Mapped[bool] = mapped_column(nullable=False, default=False)
    result_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    file_count: Mapped[int] = mapped_column(Integer, nullable=False)
    python_file_count: Mapped[int] = mapped_column(Integer, nullable=False)
    python_loc: Mapped[int] = mapped_column(Integer, nullable=False)
    edge_count: Mapped[int] = mapped_column(Integer, nullable=False)
    cycle_group_count: Mapped[int] = mapped_column(Integer, nullable=False)
    diagnostic_count: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False, server_default=func.now())

    project: Mapped[Project] = relationship(back_populates="snapshots")


class AnalysisJob(Base):
    __tablename__ = "analysis_jobs"
    __table_args__ = (
        CheckConstraint("status IN ('queued', 'running', 'succeeded', 'failed')", name="job_status_valid"),
        Index("ix_job_project_status", "project_id", "status"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    branch: Mapped[str | None] = mapped_column(String(255), nullable=True)
    requested_commit: Mapped[str | None] = mapped_column(String(40), nullable=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="queued")
    error_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    error_message: Mapped[str | None] = mapped_column(String(240), nullable=True)
    snapshot_id: Mapped[int | None] = mapped_column(ForeignKey("analysis_snapshots.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False, server_default=func.now())
    started_at: Mapped[datetime | None] = mapped_column(UTCDateTime(), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(UTCDateTime(), nullable=True)


class Task(Base):
    __tablename__ = "tasks"
    __table_args__ = (
        CheckConstraint("length(title) BETWEEN 1 AND 200", name="task_title_length"),
        CheckConstraint("description IS NULL OR length(description) <= 4000", name="task_description_length"),
        CheckConstraint("status IN ('TODO', 'IN_PROGRESS', 'DONE', 'BLOCKED')", name="task_status_valid"),
        CheckConstraint("priority IN ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL')", name="task_priority_valid"),
        CheckConstraint("source IN ('manual', 'import')", name="task_source_valid"),
        CheckConstraint("category IS NULL OR (length(category) BETWEEN 1 AND 80 AND category = trim(category))", name="task_category_valid"),
        CheckConstraint("position >= 0", name="task_position_nonnegative"),
        UniqueConstraint("project_id", "source_key", name="uq_task_project_source_key"),
        Index("ix_tasks_project_status", "project_id", "status"),
        Index("ix_tasks_project_priority", "project_id", "priority"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(String(4000), nullable=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="TODO", server_default="TODO")
    priority: Mapped[str] = mapped_column(String(16), nullable=False, default="MEDIUM", server_default="MEDIUM")
    category: Mapped[str | None] = mapped_column(String(80), nullable=True)
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    source: Mapped[str] = mapped_column(String(16), nullable=False, default="manual", server_default="manual")
    source_key: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False, server_default=func.now(), onupdate=func.now())
    completed_at: Mapped[datetime | None] = mapped_column(UTCDateTime(), nullable=True)
    project: Mapped[Project] = relationship(back_populates="tasks")
    file_links: Mapped[list[TaskFileLink]] = relationship(back_populates="task", cascade="all, delete-orphan", passive_deletes=True)
    acceptance_criteria: Mapped[list[AcceptanceCriterion]] = relationship(back_populates="task", cascade="all, delete-orphan", passive_deletes=True)


class TaskFileLink(Base):
    __tablename__ = "task_file_links"
    __table_args__ = (
        CheckConstraint("length(path) BETWEEN 1 AND 500", name="task_file_link_path_length"),
        UniqueConstraint("task_id", "path", name="uq_task_file_link_task_path"),
        Index("ix_task_file_links_task_id", "task_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    task_id: Mapped[int] = mapped_column(ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False)
    path: Mapped[str] = mapped_column(String(500), nullable=False)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False, server_default=func.now())
    task: Mapped[Task] = relationship(back_populates="file_links")


class AcceptanceCriterion(Base):
    __tablename__ = "acceptance_criteria"
    __table_args__ = (
        CheckConstraint("kind IN ('file_exists', 'path_has_files', 'import_edge_exists', 'not_in_cycle', 'max_todo_markers', 'no_analysis_failures', 'manual_attestation')", name="acceptance_criterion_kind_valid"),
        CheckConstraint("length(description) <= 500", name="acceptance_criterion_description_length"),
        CheckConstraint("kind = 'manual_attestation' OR attested IS NULL", name="acceptance_criterion_attested_kind"),
        CheckConstraint("position >= 0", name="acceptance_criterion_position_nonnegative"),
        Index("ix_acceptance_criteria_task_id", "task_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    task_id: Mapped[int] = mapped_column(ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False)
    kind: Mapped[str] = mapped_column(String(32), nullable=False)
    params: Mapped[dict] = mapped_column(JSONObject(), nullable=False, default=dict)
    description: Mapped[str] = mapped_column(String(500), nullable=False, default="", server_default="")
    attested: Mapped[bool | None] = mapped_column(nullable=True)
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False, server_default=func.now(), onupdate=func.now())
    task: Mapped[Task] = relationship(back_populates="acceptance_criteria")
