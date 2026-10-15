"""Project and task scoped CRUD for file links and acceptance criteria."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from projectlens.app.api.dependencies import get_session
from projectlens.app.api.link_criteria_schemas import (
    CriterionCreate, CriterionList, CriterionPatch, CriterionResponse,
    LinkCreate, LinkList, LinkResponse,
)
from projectlens.app.db.repository import (
    AcceptanceCriterionNotFoundError, DuplicateLinkError, ProjectNotFoundError, ResourceLimitError,
    TaskFileLinkNotFoundError,
    TaskNotFoundError, create_acceptance_criterion,
    create_task_file_link, delete_acceptance_criterion, delete_task_file_link,
    get_acceptance_criterion, list_acceptance_criteria, list_task_file_links,
    update_acceptance_criterion,
)

router = APIRouter()


def _not_found(exc: LookupError):
    if isinstance(exc, ProjectNotFoundError):
        code, message = "project_not_found", "Project was not found."
    elif isinstance(exc, TaskNotFoundError):
        code, message = "task_not_found", "Task was not found for this project."
    elif isinstance(exc, TaskFileLinkNotFoundError):
        code, message = "link_not_found", "Task file link was not found."
    elif isinstance(exc, AcceptanceCriterionNotFoundError):
        code, message = "criterion_not_found", "Acceptance criterion was not found."
    else:
        code, message = "task_item_not_found", "Task item was not found for this task."
    raise HTTPException(404, detail={"code": code, "message": message})


def _validation(exc: ValueError):
    raise HTTPException(422, detail={"code": "validation_error", "message": "Request validation failed."})


def _limit(exc: ResourceLimitError):
    code = "link_limit_reached" if exc.resource == "links" else "criteria_limit_reached"
    raise HTTPException(409, detail={"code": code, "message": "This task has reached its item limit."})


@router.post("/projects/{project_id}/tasks/{task_id}/links", response_model=LinkResponse, status_code=201)
def create_link(project_id: int, task_id: int, body: LinkCreate, session: Session = Depends(get_session)):
    try:
        item = create_task_file_link(session, project_id, task_id, body.path)
        session.commit(); session.refresh(item)
        return item
    except (ProjectNotFoundError, TaskNotFoundError) as exc:
        session.rollback(); _not_found(exc)
    except DuplicateLinkError:
        session.rollback()
        raise HTTPException(409, detail={"code": "duplicate_link", "message": "This path is already linked to the task."})
    except ResourceLimitError as exc:
        session.rollback(); _limit(exc)
    except ValueError as exc:
        session.rollback(); _validation(exc)
    except IntegrityError:
        session.rollback()
        raise HTTPException(409, detail={"code": "duplicate_link", "message": "This path is already linked to the task."})


@router.get("/projects/{project_id}/tasks/{task_id}/links", response_model=LinkList)
def list_links(project_id: int, task_id: int, session: Session = Depends(get_session)):
    try:
        return {"items": list_task_file_links(session, project_id, task_id)}
    except (ProjectNotFoundError, TaskNotFoundError) as exc:
        _not_found(exc)


@router.delete("/projects/{project_id}/tasks/{task_id}/links/{link_id}", status_code=204)
def remove_link(project_id: int, task_id: int, link_id: int, session: Session = Depends(get_session)):
    try:
        delete_task_file_link(session, project_id, task_id, link_id)
        session.commit()
        return Response(status_code=204)
    except (ProjectNotFoundError, TaskNotFoundError, TaskFileLinkNotFoundError) as exc:
        session.rollback(); _not_found(exc)


@router.post("/projects/{project_id}/tasks/{task_id}/criteria", response_model=CriterionResponse, status_code=201)
def create_criterion(project_id: int, task_id: int, body: CriterionCreate, session: Session = Depends(get_session)):
    try:
        item = create_acceptance_criterion(session, project_id, task_id, **body.model_dump())
        session.commit(); session.refresh(item)
        return item
    except (ProjectNotFoundError, TaskNotFoundError) as exc:
        session.rollback(); _not_found(exc)
    except ResourceLimitError as exc:
        session.rollback(); _limit(exc)
    except ValueError as exc:
        session.rollback(); _validation(exc)


@router.get("/projects/{project_id}/tasks/{task_id}/criteria", response_model=CriterionList)
def list_criteria(project_id: int, task_id: int, session: Session = Depends(get_session)):
    try:
        return {"items": list_acceptance_criteria(session, project_id, task_id)}
    except (ProjectNotFoundError, TaskNotFoundError) as exc:
        _not_found(exc)


@router.get("/projects/{project_id}/tasks/{task_id}/criteria/{criterion_id}", response_model=CriterionResponse)
def criterion_detail(project_id: int, task_id: int, criterion_id: int, session: Session = Depends(get_session)):
    try:
        return get_acceptance_criterion(session, project_id, task_id, criterion_id)
    except (ProjectNotFoundError, TaskNotFoundError, AcceptanceCriterionNotFoundError) as exc:
        _not_found(exc)


@router.patch("/projects/{project_id}/tasks/{task_id}/criteria/{criterion_id}", response_model=CriterionResponse)
def patch_criterion(project_id: int, task_id: int, criterion_id: int, body: CriterionPatch, session: Session = Depends(get_session)):
    try:
        item = update_acceptance_criterion(session, project_id, task_id, criterion_id,
                                           body.model_dump(exclude_unset=True))
        session.commit(); session.refresh(item)
        return item
    except (ProjectNotFoundError, TaskNotFoundError, AcceptanceCriterionNotFoundError) as exc:
        session.rollback(); _not_found(exc)
    except ValueError as exc:
        session.rollback(); _validation(exc)


@router.delete("/projects/{project_id}/tasks/{task_id}/criteria/{criterion_id}", status_code=204)
def remove_criterion(project_id: int, task_id: int, criterion_id: int, session: Session = Depends(get_session)):
    try:
        delete_acceptance_criterion(session, project_id, task_id, criterion_id)
        session.commit()
        return Response(status_code=204)
    except (ProjectNotFoundError, TaskNotFoundError, AcceptanceCriterionNotFoundError) as exc:
        session.rollback(); _not_found(exc)
