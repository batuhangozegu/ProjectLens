from __future__ import annotations

import hashlib

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from projectlens.app.db.models import AnalysisJob, Project
from projectlens.app.db.repository import (
    create_analysis_job, create_project, find_active_job, get_analysis_job,
    get_latest_snapshot, get_project, get_project_by_repository,
    get_snapshot_for_project, list_project_snapshots, list_projects,
)
from projectlens.app.api.dependencies import get_session
from projectlens.app.api.schemas import (
    AnalysisCreate, ErrorEnvelope, HealthResponse, JobResponse, ProjectAccepted,
    ProjectCreate, ProjectList, ProjectSummary, SnapshotList, SnapshotSummary,
)
from projectlens.app.services.analysis_jobs import QueueFullError
from projectlens.git.url import InvalidRepositoryUrl, validate_repository_url

router = APIRouter()


def _snapshot(snapshot):
    return None if snapshot is None else SnapshotSummary.model_validate(snapshot, from_attributes=True)


def _project(project: Project, session: Session) -> ProjectSummary:
    value = ProjectSummary.model_validate(project, from_attributes=True)
    value.repository_url = project.canonical_repository_url
    value.latest_snapshot = _snapshot(get_latest_snapshot(session, project.id))
    return value


def _job_response(job: AnalysisJob) -> JobResponse:
    return JobResponse.model_validate(job, from_attributes=True)


def _enqueue(request: Request, session: Session, project: Project, branch: str | None, commit: str | None) -> tuple[AnalysisJob, bool]:
    manager = request.app.state.job_manager
    # The API deployment is a single process; this lock closes the in-process
    # check/insert race for active refs. Persisted jobs remain recoverable.
    with manager.enqueue_lock:
        return _enqueue_locked(manager, session, project, branch, commit)


def _enqueue_locked(manager, session: Session, project: Project, branch: str | None, commit: str | None) -> tuple[AnalysisJob, bool]:
    active = find_active_job(session, project.id, branch, commit)
    if active is not None:
        return active, False
    try:
        manager.reserve()
    except QueueFullError:
        raise HTTPException(status_code=503, detail={"code": "queue_full", "message": "The analysis queue is full; retry later."}, headers={"Retry-After": "5"})
    submit_attempted = False
    try:
        job = create_analysis_job(session, project.id, branch=branch, commit=commit)
        session.commit()
        submit_attempted = True
        manager.submit(job.id)
        session.expire_all()
        job = session.get(AnalysisJob, job.id)
        return job, True
    except Exception:
        session.rollback()
        if not submit_attempted:
            manager._slots.release()
        raise


@router.get("/health", response_model=HealthResponse)
def health(request: Request, session: Session = Depends(get_session)):
    from sqlalchemy import text
    try:
        session.execute(text("SELECT 1"))
        db_status = "ok"
    except Exception:
        db_status = "unavailable"
    return {"status": "ok", "database": db_status}


@router.post("/projects", response_model=ProjectAccepted, status_code=202, responses={422: {"model": ErrorEnvelope}, 503: {"model": ErrorEnvelope}})
def create_project_and_analysis(body: ProjectCreate, request: Request, session: Session = Depends(get_session)):
    try:
        canonical, owner, repo = validate_repository_url(body.repository_url)
    except InvalidRepositoryUrl:
        raise HTTPException(status_code=422, detail={"code": "invalid_repository_url", "message": "Only valid public HTTPS GitHub repository URLs are accepted."})
    project = get_project_by_repository(session, canonical)
    if project is None:
        slug_base = f"{owner}-{repo}".lower()[:170].strip("-") or "project"
        suffix = hashlib.sha256(canonical.encode("ascii")).hexdigest()[:12]
        try:
            project = create_project(session, f"{owner}/{repo}", slug=f"{slug_base}-{suffix}", canonical_repository_url=canonical, default_branch=body.branch or "main")
            session.commit()
        except IntegrityError:
            session.rollback()
            project = get_project_by_repository(session, canonical)
            if project is None:
                raise
    job, _created = _enqueue(request, session, project, body.branch, body.commit)
    return ProjectAccepted(project_id=project.id, job_id=job.id, status=job.status,
                           job_url=f"/api/v1/jobs/{job.id}", project_url=f"/api/v1/projects/{project.id}")


@router.get("/projects", response_model=ProjectList)
def projects(session: Session = Depends(get_session)):
    return {"items": [_project(item, session) for item in list_projects(session)]}


@router.get("/projects/{project_id}", response_model=ProjectSummary, responses={404: {"model": ErrorEnvelope}})
def project_detail(project_id: int, session: Session = Depends(get_session)):
    project = get_project(session, project_id=project_id)
    if project is None:
        raise HTTPException(404, detail={"code": "project_not_found", "message": "Project was not found."})
    return _project(project, session)


@router.get("/projects/{project_id}/snapshots", response_model=SnapshotList, responses={404: {"model": ErrorEnvelope}})
def snapshots(project_id: int, limit: int = Query(20, ge=1, le=100), offset: int = Query(0, ge=0, le=10000), session: Session = Depends(get_session)):
    if get_project(session, project_id=project_id) is None:
        raise HTTPException(404, detail={"code": "project_not_found", "message": "Project was not found."})
    items = list_project_snapshots(session, project_id, limit=limit, offset=offset)
    return {"items": [_snapshot(s) for s in items], "limit": limit, "offset": offset}


@router.get("/projects/{project_id}/snapshots/latest", response_model=dict, responses={404: {"model": ErrorEnvelope}})
def latest_snapshot(project_id: int, session: Session = Depends(get_session)):
    if get_project(session, project_id=project_id) is None:
        raise HTTPException(404, detail={"code": "project_not_found", "message": "Project was not found."})
    snapshot = get_latest_snapshot(session, project_id)
    if snapshot is None:
        raise HTTPException(404, detail={"code": "snapshot_not_found", "message": "No snapshot was found for this project."})
    return snapshot.result_json


@router.get("/projects/{project_id}/snapshots/{snapshot_id}", response_model=dict, responses={404: {"model": ErrorEnvelope}})
def snapshot_detail(project_id: int, snapshot_id: int, session: Session = Depends(get_session)):
    snapshot = get_snapshot_for_project(session, project_id, snapshot_id)
    if snapshot is None:
        raise HTTPException(404, detail={"code": "snapshot_not_found", "message": "Snapshot was not found for this project."})
    return snapshot.result_json


@router.post("/projects/{project_id}/analyses", response_model=ProjectAccepted, status_code=202, responses={404: {"model": ErrorEnvelope}, 503: {"model": ErrorEnvelope}})
def reanalyze(project_id: int, body: AnalysisCreate, request: Request, session: Session = Depends(get_session)):
    project = get_project(session, project_id=project_id)
    if project is None:
        raise HTTPException(404, detail={"code": "project_not_found", "message": "Project was not found."})
    job, _ = _enqueue(request, session, project, body.branch, body.commit)
    return ProjectAccepted(project_id=project.id, job_id=job.id, status=job.status,
                           job_url=f"/api/v1/jobs/{job.id}", project_url=f"/api/v1/projects/{project.id}")


@router.get("/jobs/{job_id}", response_model=JobResponse, responses={404: {"model": ErrorEnvelope}})
def job_detail(job_id: int, session: Session = Depends(get_session)):
    job = get_analysis_job(session, job_id)
    if job is None:
        raise HTTPException(404, detail={"code": "job_not_found", "message": "Analysis job was not found."})
    return _job_response(job)
