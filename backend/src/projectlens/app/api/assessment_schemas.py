"""HTTP response schemas for code-aware task assessments."""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict


class AssessmentSchema(BaseModel):
    model_config = ConfigDict(extra="allow")


class TaskAssessmentResponse(AssessmentSchema):
    project_id: int
    task_id: int
    formula_version: str
    state: str
    manual_status: str
    estimated_percent: float | None
    confidence: str
    reasons: list[Any]
    criteria_results: list[Any]
    unknown_criteria: list[Any]
    attestations: dict[str, Any]
    context: list[Any]
    divergence: str | None
    divergence_reason: str | None
    snapshot: dict[str, Any] | None


class RoadmapAssessmentResponse(AssessmentSchema):
    project_id: int
    formula_version: str
    snapshot: dict[str, Any] | None
    total_tasks: int
    counts_by_state: dict[str, int]
    confidence: dict[str, int]
    tasks_with_estimate: int
    tasks_without_estimate: int
    tasks_with_unknown_criteria: int
    divergence_counts: dict[str, int]
    total_diverging: int
    tasks_without_criteria: int
    average_estimated_percent: float | None
    notes: list[str]
