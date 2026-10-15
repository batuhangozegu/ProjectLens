"""Pure, versioned roadmap progress calculation.

Formula version 1: ``percent_complete = DONE / total * 100``. Only DONE tasks
count as complete; IN_PROGRESS earns no partial credit, and BLOCKED tasks stay
in the denominator. Empty roadmaps have ``percent_complete=None`` and state
``"empty"`` (never 0% or 100%). Manual task status is independent of any
analysis-derived estimate, and file existence alone never proves completion.
Percentages are rounded to one decimal place using exact integer arithmetic
and round-half-up. Breakdown labels sort lexically, with missing values last.
"""

from collections.abc import Iterable, Mapping
from dataclasses import dataclass

PROGRESS_FORMULA_VERSION = "1"
STATUSES = ("TODO", "IN_PROGRESS", "DONE", "BLOCKED")
_UNCATEGORIZED = "(uncategorized)"
_NO_SECTION = "(no section)"


@dataclass(frozen=True)
class TaskProgressInput:
    status: str
    category: str | None = None
    section: str | None = None
    priority: str | None = None


@dataclass(frozen=True)
class RoadmapProgress:
    total: int
    counts: Mapping[str, int]
    completed: int
    percent_complete: float | None
    state: str
    has_blocked: bool
    remaining: int
    breakdown_by_category: Mapping[str, "RoadmapProgress"]
    breakdown_by_section: Mapping[str, "RoadmapProgress"]
    formula_version: str = PROGRESS_FORMULA_VERSION

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-safe, deterministically ordered plain dictionary."""
        return {
            "formula_version": self.formula_version,
            "total": self.total,
            "counts": {status: self.counts[status] for status in STATUSES},
            "completed": self.completed,
            "percent_complete": self.percent_complete,
            "state": self.state,
            "has_blocked": self.has_blocked,
            "remaining": self.remaining,
            "breakdown_by_category": {
                key: value.to_dict() for key, value in self.breakdown_by_category.items()
            },
            "breakdown_by_section": {
                key: value.to_dict() for key, value in self.breakdown_by_section.items()
            },
        }


def _rounded_percent(done: int, total: int) -> float:
    # Round (done * 100 / total) to tenths, half-up, without floating point.
    tenths, remainder = divmod(done * 1000, total)
    if remainder * 2 >= total:
        tenths += 1
    return tenths / 10


def _aggregate(tasks: list[TaskProgressInput]) -> RoadmapProgress:
    counts = {status: 0 for status in STATUSES}
    for task in tasks:
        counts[task.status] += 1
    total = len(tasks)
    done = counts["DONE"]
    if total == 0:
        state, percent = "empty", None
    elif done == total:
        state, percent = "complete", 100.0
    else:
        percent = _rounded_percent(done, total)
        state = "in_progress" if counts["IN_PROGRESS"] else "not_started"
    return RoadmapProgress(
        total=total,
        counts=counts,
        completed=done,
        percent_complete=percent,
        state=state,
        has_blocked=counts["BLOCKED"] > 0,
        remaining=total - done,
        breakdown_by_category={},
        breakdown_by_section={},
    )


def _sort_key(item: tuple[str | None, list[TaskProgressInput]], missing_label: str) -> tuple[bool, str]:
    label, _ = item
    return (label is None, missing_label if label is None else label)


def compute_progress(tasks: Iterable[TaskProgressInput]) -> RoadmapProgress:
    """Calculate progress from plain task data without mutating the input."""
    collected = list(tasks)
    for task in collected:
        if task.status not in STATUSES:
            raise ValueError(
                f"Unknown task status {task.status!r}; expected one of {', '.join(STATUSES)}"
            )

    result = _aggregate(collected)
    categories: dict[str | None, list[TaskProgressInput]] = {}
    sections: dict[str | None, list[TaskProgressInput]] = {}
    for task in collected:
        categories.setdefault(task.category, []).append(task)
        sections.setdefault(task.section, []).append(task)
    category_results = {
        _UNCATEGORIZED if label is None else label: _aggregate(group)
        for label, group in sorted(categories.items(), key=lambda item: _sort_key(item, _UNCATEGORIZED))
    }
    section_results = {
        _NO_SECTION if label is None else label: _aggregate(group)
        for label, group in sorted(sections.items(), key=lambda item: _sort_key(item, _NO_SECTION))
    }
    return RoadmapProgress(
        total=result.total,
        counts=result.counts,
        completed=result.completed,
        percent_complete=result.percent_complete,
        state=result.state,
        has_blocked=result.has_blocked,
        remaining=result.remaining,
        breakdown_by_category=category_results,
        breakdown_by_section=section_results,
    )
