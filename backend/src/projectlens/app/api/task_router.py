"""Manual task CRUD endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.orm import Session

from projectlens.app.api.dependencies import get_session
from projectlens.app.api.schemas import ErrorEnvelope, TaskCreate, TaskList, TaskPatch, TaskResponse
from projectlens.app.db.repository import (
    ProjectNotFoundError, TaskNotFoundError, create_task, delete_task, get_task,
    list_tasks, update_task,
)
from projectlens.app.db.task_status import InvalidTransition

router = APIRouter()


def _not_found(exc: LookupError):
    code = "project_not_found" if isinstance(exc, ProjectNotFoundError) else "task_not_found"
    message = "Project was not found." if code == "project_not_found" else "Task was not found for this project."
    raise HTTPException(404, detail={"code": code, "message": message})


@router.post("/projects/{project_id}/tasks", response_model=TaskResponse, status_code=201,
             responses={404: {"model": ErrorEnvelope}})
def create_project_task(project_id: int, body: TaskCreate, session: Session = Depends(get_session)):
    try:
        task = create_task(session, project_id, **body.model_dump())
        session.commit()
        session.refresh(task)
        return task
    except ProjectNotFoundError as exc:
        session.rollback()
        _not_found(exc)


@router.get("/projects/{project_id}/tasks", response_model=TaskList,
            responses={404: {"model": ErrorEnvelope}})
def project_tasks(project_id: int, status: list[str] | None = Query(default=None),
                  priority: str | None = None, category: str | None = Query(default=None, max_length=80),
                  search: str | None = Query(default=None, max_length=200),
                  limit: int = Query(20, ge=1, le=100), offset: int = Query(0, ge=0, le=10000),
                  session: Session = Depends(get_session)):
    allowed_status = {"TODO", "IN_PROGRESS", "DONE", "BLOCKED"}
    allowed_priority = {"LOW", "MEDIUM", "HIGH", "CRITICAL"}
    if status is not None and any(value not in allowed_status for value in status):
        raise HTTPException(422, detail={"code": "validation_error", "message": "Request validation failed."})
    if priority is not None and priority not in allowed_priority:
        raise HTTPException(422, detail={"code": "validation_error", "message": "Request validation failed."})
    try:
        items, total = list_tasks(session, project_id, status=status, priority=priority, category=category,
                                  search=search, limit=limit, offset=offset)
    except ProjectNotFoundError as exc:
        _not_found(exc)
    return {"items": items, "total": total, "limit": limit, "offset": offset}


@router.get("/projects/{project_id}/tasks/{task_id}", response_model=TaskResponse,
            responses={404: {"model": ErrorEnvelope}})
def task_detail(project_id: int, task_id: int, session: Session = Depends(get_session)):
    try:
        return get_task(session, project_id, task_id)
    except (ProjectNotFoundError, TaskNotFoundError) as exc:
        _not_found(exc)


@router.patch("/projects/{project_id}/tasks/{task_id}", response_model=TaskResponse,
              responses={404: {"model": ErrorEnvelope}, 409: {"model": ErrorEnvelope}})
def patch_task(project_id: int, task_id: int, body: TaskPatch, session: Session = Depends(get_session)):
    try:
        task = update_task(session, project_id, task_id, body.model_dump(exclude_unset=True))
        session.commit()
        session.refresh(task)
        return task
    except (ProjectNotFoundError, TaskNotFoundError) as exc:
        session.rollback()
        _not_found(exc)
    except InvalidTransition as exc:
        session.rollback()
        raise HTTPException(409, detail={"code": "invalid_status_transition", "message": str(exc)})


@router.delete("/projects/{project_id}/tasks/{task_id}", status_code=204,
               responses={404: {"model": ErrorEnvelope}})
def remove_task(project_id: int, task_id: int, session: Session = Depends(get_session)):
    try:
        delete_task(session, project_id, task_id)
        session.commit()
        return Response(status_code=204)
    except (ProjectNotFoundError, TaskNotFoundError) as exc:
        session.rollback()
        _not_found(exc)
