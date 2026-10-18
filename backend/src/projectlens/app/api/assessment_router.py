"""Evidence-based assessment endpoints; manual task state is read-only here."""
from __future__ import annotations

import re

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from projectlens.app.api.assessment_schemas import RoadmapAssessmentResponse, TaskAssessmentResponse
from projectlens.app.api.dependencies import get_session
from projectlens.app.db.models import AcceptanceCriterion, Task, TaskFileLink
from projectlens.app.db.repository import (
    get_latest_snapshot,
    get_project,
    get_snapshot_for_project,
    get_task,
)
from projectlens.tracking.evidence import (
    FORMULA_VERSION,
    CriterionInput,
    LinkInput,
    assess_task,
    assess_without_snapshot,
)

router = APIRouter()
# Keep this synchronous aggregate bounded while still supporting substantial roadmaps.
MAX_ASSESSMENT_TASKS = 1000
_STATES = ("no_snapshot", "insufficient_evidence", "estimated")


def _error(status: int, code: str, message: str):
    raise HTTPException(status, detail={"code": code, "message": message})


def _inputs(session: Session, task: Task, *, batch_links=None, batch_criteria=None):
    links = batch_links.get(task.id, []) if batch_links is not None else session.scalars(
        select(TaskFileLink).where(TaskFileLink.task_id == task.id).order_by(TaskFileLink.id)
    )
    criteria = batch_criteria.get(task.id, []) if batch_criteria is not None else session.scalars(
        select(AcceptanceCriterion).where(AcceptanceCriterion.task_id == task.id)
        .order_by(AcceptanceCriterion.position, AcceptanceCriterion.id)
    )
    return (
        [LinkInput(path=item.path) for item in links],
        [CriterionInput(id=item.id, kind=item.kind, params=item.params,
                        description=item.description, attested=item.attested) for item in criteria],
    )


def _snapshot_info(snapshot):
    if snapshot is None:
        return None
    return {"id": snapshot.id, "commit": snapshot.commit_sha, "partial": snapshot.partial}


@router.get("/projects/{project_id}/tasks/{task_id}/assessment", response_model=TaskAssessmentResponse)
def task_assessment(
    project_id: int,
    task_id: int,
    snapshot: str = Query(default="latest"),
    session: Session = Depends(get_session),
):
    try:
        task = get_task(session, project_id, task_id)
    except LookupError:
        if get_project(session, project_id=project_id) is None:
            _error(404, "project_not_found", "Project was not found.")
        _error(404, "task_not_found", "Task was not found.")
    if snapshot == "latest":
        selected = get_latest_snapshot(session, project_id)
    elif re.fullmatch(r"[0-9]+", snapshot):
        selected = get_snapshot_for_project(session, project_id, int(snapshot))
        if selected is None:
            _error(404, "snapshot_not_found", "Snapshot was not found for this project.")
    else:
        _error(422, "validation_error", "snapshot must be 'latest' or a snapshot ID.")
    links, criteria = _inputs(session, task)
    result = (
        assess_without_snapshot(task.status, criteria, links)
        if selected is None
        else assess_task(selected.result_json, manual_status=task.status, criteria=criteria,
                         links=links, snapshot_meta={"id": selected.id, "commit": selected.commit_sha})
    )
    return {"project_id": project_id, "task_id": task_id, **result.to_dict()}


@router.get("/projects/{project_id}/roadmap/assessment", response_model=RoadmapAssessmentResponse)
def roadmap_assessment(project_id: int, session: Session = Depends(get_session)):
    if get_project(session, project_id=project_id) is None:
        _error(404, "project_not_found", "Project was not found.")
    tasks = list(session.scalars(
        select(Task).where(Task.project_id == project_id).order_by(Task.position, Task.id)
        .limit(MAX_ASSESSMENT_TASKS + 1)
    ))
    if len(tasks) > MAX_ASSESSMENT_TASKS:
        _error(413, "assessment_task_limit", f"Roadmap assessment is limited to {MAX_ASSESSMENT_TASKS} tasks.")
    selected = get_latest_snapshot(session, project_id)
    task_ids = [task.id for task in tasks]
    links_by_task: dict[int, list] = {}
    criteria_by_task: dict[int, list] = {}
    if task_ids:
        for item in session.scalars(select(TaskFileLink).where(TaskFileLink.task_id.in_(task_ids))
                                    .order_by(TaskFileLink.task_id, TaskFileLink.id)):
            links_by_task.setdefault(item.task_id, []).append(item)
        for item in session.scalars(select(AcceptanceCriterion).where(AcceptanceCriterion.task_id.in_(task_ids))
                                    .order_by(AcceptanceCriterion.task_id, AcceptanceCriterion.position,
                                              AcceptanceCriterion.id)):
            criteria_by_task.setdefault(item.task_id, []).append(item)
    counts = {state: 0 for state in _STATES}
    confidence = {level: 0 for level in ("high", "medium", "low", "none")}
    divergence_counts: dict[str, int] = {}
    estimate_total = 0.0
    with_estimate = unknown_criteria = without_criteria = total_diverging = 0
    for task in tasks:
        links, criteria = _inputs(session, task, batch_links=links_by_task,
                                  batch_criteria=criteria_by_task)
        result = (assess_without_snapshot(task.status, criteria, links) if selected is None else
                  assess_task(selected.result_json, manual_status=task.status, criteria=criteria,
                              links=links, snapshot_meta={"id": selected.id, "commit": selected.commit_sha}))
        item = result.to_dict()
        counts[item["state"]] = counts.get(item["state"], 0) + 1
        confidence[item["confidence"]] = confidence.get(item["confidence"], 0) + 1
        if item["estimated_percent"] is not None:
            with_estimate += 1
            estimate_total += item["estimated_percent"]
        unknown_criteria += bool(item["unknown_criteria"])
        without_criteria += not criteria
        if item["divergence"] is not None:
            total_diverging += 1
            divergence_counts[item["divergence"]] = divergence_counts.get(item["divergence"], 0) + 1
    return {
        "project_id": project_id,
        "formula_version": FORMULA_VERSION,
        "snapshot": _snapshot_info(selected),
        "total_tasks": len(tasks),
        "counts_by_state": counts,
        "confidence": confidence,
        "tasks_with_estimate": with_estimate,
        "tasks_without_estimate": len(tasks) - with_estimate,
        "tasks_with_unknown_criteria": unknown_criteria,
        "divergence_counts": divergence_counts,
        "total_diverging": total_diverging,
        "tasks_without_criteria": without_criteria,
        "average_estimated_percent": round(estimate_total / with_estimate, 1) if with_estimate else None,
        "notes": [
            "Manual progress from /roadmap/progress is unchanged by assessment.",
            "This endpoint reports evidence-based estimates; estimated progress is not blended with manual progress.",
        ],
    }
