"""Translate Markdown checklist items into project tasks."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from projectlens.app.db.repository import (
    ProjectNotFoundError,
    create_task,
    get_imported_tasks_by_keys,
    get_max_task_position,
    get_project,
    list_imported_tasks,
    update_task,
)
from projectlens.tracking.todo_parser import ChecklistError, parse_checklist


TITLE_LIMIT = 200
CATEGORY_LIMIT = 80
ITEMS_LIMIT = 200


def _shorten_category(value: str | None) -> str | None:
    """Keep the rightmost 79 characters after an ellipsis for long paths."""
    if not value:
        return None
    value = value.strip()
    if not value:
        return None
    if len(value) > CATEGORY_LIMIT:
        value = "…" + value[-(CATEGORY_LIMIT - 1):]
    return value


def _bounded(values: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], bool]:
    return values[:ITEMS_LIMIT], len(values) > ITEMS_LIMIT


def import_roadmap(session: Session, project_id: int, markdown: str, *, dry_run: bool = False) -> dict[str, Any]:
    """Build and optionally apply one atomic checklist import report.

    The caller owns the surrounding transaction and must commit on success or
    roll it back on any error. Dry runs perform reads only.
    """
    if get_project(session, project_id=project_id) is None:
        raise ProjectNotFoundError(f"project {project_id!r} does not exist")
    parsed = parse_checklist(markdown)
    keys = {item.source_key for item in parsed.items}
    matched = get_imported_tasks_by_keys(session, project_id, keys)
    imported = list_imported_tasks(session, project_id)
    present_keys = keys
    report_items: dict[str, list[dict[str, Any]]] = {
        "created": [], "updated": [], "conflicts": [], "skipped": [], "missing_from_source": []
    }
    counts = {name: 0 for name in report_items}
    counts["unchanged"] = 0

    position = get_max_task_position(session, project_id)
    next_position = 0 if position is None else position + 1
    for item in parsed.items:
        common = {"source_key": item.source_key, "title": item.title}
        if len(item.title) > TITLE_LIMIT:
            counts["skipped"] += 1
            report_items["skipped"].append({**common, "reason": "title_too_long"})
            continue
        existing = matched.get(item.source_key)
        if existing is None:
            counts["created"] += 1
            report_items["created"].append(common)
            if not dry_run:
                category = _shorten_category(" / ".join(item.section_path))
                create_task(
                    session,
                    project_id,
                    title=item.title,
                    status="DONE" if item.checked else "TODO",
                    priority="MEDIUM",
                    category=category,
                    position=next_position,
                    source="import",
                    source_key=item.source_key,
                )
                next_position += 1
            continue
        if item.checked and existing.status == "BLOCKED":
            counts["conflicts"] += 1
            report_items["conflicts"].append({
                **common, "reason": "checked_item_matches_blocked_task"
            })
        elif item.checked and existing.status in {"TODO", "IN_PROGRESS"}:
            counts["updated"] += 1
            report_items["updated"].append(common)
            if not dry_run:
                update_task(session, project_id, existing.id, {"status": "DONE"})
        else:
            counts["unchanged"] += 1

    for task in imported:
        if task.source_key not in present_keys:
            counts["missing_from_source"] += 1
            report_items["missing_from_source"].append({
                "source_key": task.source_key, "title": task.title
            })

    bounded_items: dict[str, list[dict[str, Any]]] = {}
    truncated: dict[str, bool] = {}
    for name, values in report_items.items():
        bounded_items[name], truncated[name] = _bounded(values)
    return {
        "dry_run": dry_run,
        "summary": counts,
        **bounded_items,
        "diagnostics": [
            {"severity": item.severity, "message": item.message, "line": item.line}
            for item in parsed.diagnostics
        ][:ITEMS_LIMIT],
        "truncated": {**truncated, "diagnostics": len(parsed.diagnostics) > ITEMS_LIMIT},
    }


__all__ = ["ChecklistError", "import_roadmap"]
