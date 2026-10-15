"""HTTP-only Pydantic schemas; never imported by the analysis core."""
from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator


class ErrorDetail(BaseModel):
    code: str
    message: str


class ErrorEnvelope(BaseModel):
    error: ErrorDetail


class ProjectCreate(BaseModel):
    repository_url: str = Field(min_length=1, max_length=2048)
    branch: str | None = Field(default=None, min_length=1, max_length=255)
    commit: str | None = None

    @model_validator(mode="after")
    def one_revision_selector(self):
        if self.branch is not None and self.commit is not None:
            raise ValueError("provide either branch or commit, not both")
        return self

    @field_validator("commit")
    @classmethod
    def full_commit_sha(cls, value: str | None) -> str | None:
        import re
        if value is not None and not re.fullmatch(r"[0-9a-fA-F]{40}", value):
            raise ValueError("commit must be a full 40-character hexadecimal SHA")
        return value.lower() if value else None


class AnalysisCreate(BaseModel):
    branch: str | None = Field(default=None, min_length=1, max_length=255)
    commit: str | None = None

    @model_validator(mode="after")
    def one_revision_selector(self):
        if self.branch is not None and self.commit is not None:
            raise ValueError("provide either branch or commit, not both")
        return self

    @field_validator("commit")
    @classmethod
    def full_commit_sha(cls, value: str | None) -> str | None:
        import re
        if value is not None and not re.fullmatch(r"[0-9a-fA-F]{40}", value):
            raise ValueError("commit must be a full 40-character hexadecimal SHA")
        return value.lower() if value else None


class SnapshotSummary(BaseModel):
    id: int
    branch: str
    commit_sha: str
    status: str
    partial: bool
    analyzer_schema_version: str
    file_count: int
    python_file_count: int
    python_loc: int
    edge_count: int
    cycle_group_count: int
    diagnostic_count: int
    created_at: datetime


class ProjectSummary(BaseModel):
    id: int
    name: str
    slug: str
    repository_url: str | None = None
    default_branch: str
    created_at: datetime
    updated_at: datetime
    latest_snapshot: SnapshotSummary | None = None


class ProjectList(BaseModel):
    items: list[ProjectSummary]


class ProjectAccepted(BaseModel):
    project_id: int
    job_id: int
    status: Literal["queued", "running", "succeeded", "failed"]
    job_url: str
    project_url: str


class JobResponse(BaseModel):
    id: int
    project_id: int
    status: Literal["queued", "running", "succeeded", "failed"]
    error_code: str | None
    error_message: str | None
    snapshot_id: int | None
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None


class SnapshotList(BaseModel):
    items: list[SnapshotSummary]
    limit: int
    offset: int


class HealthResponse(BaseModel):
    status: str
    database: Literal["ok", "unavailable"]
