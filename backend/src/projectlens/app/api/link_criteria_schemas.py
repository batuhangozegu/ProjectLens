"""Public schemas for task file links and acceptance criteria."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from projectlens.app.criteria_validation import validate_criterion_params

CriterionKind = Literal[
    "file_exists", "path_has_files", "import_edge_exists", "not_in_cycle",
    "max_todo_markers", "no_analysis_failures", "manual_attestation",
]


class LinkCreate(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")
    path: str = Field(min_length=1, max_length=500)


class LinkResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    task_id: int
    path: str
    created_at: datetime


class LinkList(BaseModel):
    items: list[LinkResponse]


class CriterionCreate(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")
    kind: CriterionKind
    params: dict[str, Any] = Field(default_factory=dict)
    description: str = Field(default="", max_length=500)
    attested: bool | None = None
    position: int | None = Field(default=None, ge=0)

    @field_validator("params")
    @classmethod
    def params_are_object(cls, value):
        if not isinstance(value, dict):
            raise ValueError("params must be an object")
        return value

    @model_validator(mode="after")
    def validate_params_and_attested(self):
        validate_criterion_params(self.kind, self.params)
        if self.kind != "manual_attestation" and self.attested is not None:
            raise ValueError("attested is allowed only for manual_attestation criteria")
        return self


class CriterionPatch(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")
    description: str | None = Field(default=None, max_length=500)
    params: dict[str, Any] | None = None
    attested: bool | None = None
    position: int | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def nonnullable_patch_values(self):
        if "description" in self.model_fields_set and self.description is None:
            raise ValueError("description cannot be null")
        if "params" in self.model_fields_set and self.params is None:
            raise ValueError("params cannot be null")
        if "position" in self.model_fields_set and self.position is None:
            raise ValueError("position cannot be null")
        return self


class CriterionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    task_id: int
    kind: CriterionKind
    params: dict[str, Any]
    description: str
    attested: bool | None
    position: int
    created_at: datetime
    updated_at: datetime


class CriterionList(BaseModel):
    items: list[CriterionResponse]
