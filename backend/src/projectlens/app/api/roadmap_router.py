"""Roadmap import and manual-status progress endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from projectlens.app.api.dependencies import get_session
from projectlens.app.api.schemas import (
    ErrorEnvelope,
    RoadmapImportRequest,
    RoadmapImportResponse,
    RoadmapProgressResponse,
)
from projectlens.app.db.repository import (
    ProjectNotFoundError,
    get_project,
    iter_task_progress_fields,
)
from projectlens.app.services.roadmap_import import ChecklistError, import_roadmap
from projectlens.tracking.progress import TaskProgressInput, compute_progress

router = APIRouter()
MAX_REQUEST_BYTES = 1024 * 1024
FORMULA_DESCRIPTION = (
    "Completed percentage is DONE tasks divided by all tasks; IN_PROGRESS earns no partial credit, "
    "and BLOCKED tasks remain in the denominator. Empty roadmaps have no percentage."
)


def _error(status: int, code: str, message: str):
    raise HTTPException(status, detail={"code": code, "message": message})


@router.post(
    "/projects/{project_id}/roadmap/import",
    response_model=RoadmapImportResponse,
    responses={
        404: {"model": ErrorEnvelope}, 409: {"model": ErrorEnvelope},
        413: {"model": ErrorEnvelope}, 422: {"model": ErrorEnvelope},
    },
)
async def import_project_roadmap(project_id: int, request: Request, session: Session = Depends(get_session)):
    raw = await request.body()
    if len(raw) > MAX_REQUEST_BYTES:
        _error(413, "request_too_large", "Request body exceeds the 1 MiB limit.")
    try:
        body = RoadmapImportRequest.model_validate_json(raw)
    except (ValidationError, ValueError):
        _error(422, "validation_error", "Request validation failed.")

    try:
        report = import_roadmap(session, project_id, body.markdown, dry_run=body.dry_run)
        if body.dry_run:
            session.rollback()
            return report
        session.commit()
        return report
    except IntegrityError:
        # A competing import may have inserted a source key after our read,
        # whether the violation surfaced at flush or commit. Re-plan once.
        session.rollback()
        try:
            report = import_roadmap(session, project_id, body.markdown, dry_run=False)
            session.commit()
            return report
        except IntegrityError:
            session.rollback()
            _error(409, "roadmap_import_conflict", "A concurrent roadmap import could not be reconciled.")
    except ProjectNotFoundError:
        session.rollback()
        _error(404, "project_not_found", "Project was not found.")
    except ChecklistError:
        session.rollback()
        _error(422, "invalid_checklist", "The Markdown checklist could not be parsed.")
    except Exception:
        session.rollback()
        raise


@router.get(
    "/projects/{project_id}/roadmap/progress",
    response_model=RoadmapProgressResponse,
    responses={404: {"model": ErrorEnvelope}, 422: {"model": ErrorEnvelope}},
)
def project_roadmap_progress(
    project_id: int,
    source: str | None = Query(default=None, pattern="^(manual|import)$"),
    session: Session = Depends(get_session),
):
    if get_project(session, project_id=project_id) is None:
        _error(404, "project_not_found", "Project was not found.")
    rows = iter_task_progress_fields(session, project_id, source=source)
    progress = compute_progress(
        TaskProgressInput(status=status, category=category, section=category, priority=priority)
        for status, category, priority in rows
    ).to_dict()
    return {
        **progress,
        "formula": FORMULA_DESCRIPTION,
        "manual_status_only": True,
    }
