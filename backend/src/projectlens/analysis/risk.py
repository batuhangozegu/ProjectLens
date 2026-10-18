"""Versioned, explainable file risk heuristic; not a defect prediction model."""

from __future__ import annotations

from collections import Counter
from typing import Any, Sequence

from .models import DependencyEdge, FileRecord, TestMatchRecord

CHURN_MEDIUM_COMMITS = 4
CHURN_HIGH_COMMITS = 10
CHURN_MEDIUM_POINTS = 1
CHURN_HIGH_POINTS = 2
SIZE_MEDIUM_LOC = 500
SIZE_HIGH_LOC = 1000
SIZE_MEDIUM_POINTS = 1
SIZE_HIGH_POINTS = 2
CYCLE_POINTS = 1
UNTESTED_POINTS = 1
FAN_IN_THRESHOLD = 10
FAN_IN_POINTS = 1
LEVEL_LOW_POINTS = 1
LEVEL_MEDIUM_POINTS = 3
LEVEL_HIGH_POINTS = 5
MAX_TOP_RISKS = 20


def compute_risk(
    files: Sequence[FileRecord], dependency_edges: Sequence[DependencyEdge],
    cycles: Sequence[Sequence[str]], test_matches: Sequence[TestMatchRecord],
    git_history_metrics: dict[str, Any] | None,
) -> dict[str, Any]:
    churn_available = bool(git_history_metrics and git_history_metrics.get("available"))
    churn_by_path: dict[str, int] = {}
    if churn_available:
        churn_by_path = dict((git_history_metrics or {}).get("_churn_by_path", {}))
        if not churn_by_path:
            churn_by_path = {item["path"]: item["commits"] for item in (git_history_metrics or {}).get("top_churn", ())}
    cycle_paths = {path for cycle in cycles for path in cycle}
    incoming = Counter(edge.target for edge in dependency_edges)
    tested = {item.source for item in test_matches if item.tests}
    candidates = []
    levels: Counter[str] = Counter()
    for file in sorted(files, key=lambda item: item.path):
        if file.file_class not in {"python_source", "dart_source"} or not file.analysis_status.startswith("analyzed"):
            continue
        factors: list[dict[str, Any]] = []
        commits = churn_by_path.get(file.path)
        if commits is not None:
            points = CHURN_HIGH_POINTS if commits >= CHURN_HIGH_COMMITS else CHURN_MEDIUM_POINTS if commits >= CHURN_MEDIUM_COMMITS else 0
            if points:
                factors.append({"id": "churn", "points": points, "reason": f"{commits} commits in the history window"})
        loc = file.physical_loc
        if loc is not None:
            points = SIZE_HIGH_POINTS if loc >= SIZE_HIGH_LOC else SIZE_MEDIUM_POINTS if loc >= SIZE_MEDIUM_LOC else 0
            if points:
                factors.append({"id": "size", "points": points, "reason": f"{loc} physical LOC"})
        if file.path in cycle_paths:
            cycle_count = sum(file.path in cycle for cycle in cycles)
            factors.append({"id": "cycle", "points": CYCLE_POINTS, "reason": f"file is in {cycle_count} dependency cycle group(s)"})
        if file.path not in tested:
            factors.append({"id": "untested", "points": UNTESTED_POINTS, "reason": "0 matching test files (name/import heuristic, not coverage)"})
        fan_in = incoming[file.path]
        if fan_in >= FAN_IN_THRESHOLD:
            factors.append({"id": "fan_in", "points": FAN_IN_POINTS, "reason": f"{fan_in} incoming local dependency edges"})
        points = sum(item["points"] for item in factors)
        level = "high" if points >= LEVEL_HIGH_POINTS else "medium" if points >= LEVEL_MEDIUM_POINTS else "low" if points >= LEVEL_LOW_POINTS else "minimal"
        levels[level] += 1
        if level != "minimal":
            candidates.append({"path": file.path, "level": level, "points": points, "factors": factors})
    candidates.sort(key=lambda item: (-item["points"], item["path"]))
    return {
        "formula_version": "1",
        "basis": "explainable heuristic; not a prediction of defects",
        "churn_available": churn_available,
        "counts_by_level": {level: levels[level] for level in ("high", "medium", "low", "minimal")},
        "top_risks": candidates[:MAX_TOP_RISKS],
        "thresholds": {
            "churn_medium_commits": CHURN_MEDIUM_COMMITS, "churn_high_commits": CHURN_HIGH_COMMITS,
            "churn_medium_points": CHURN_MEDIUM_POINTS, "churn_high_points": CHURN_HIGH_POINTS,
            "size_medium_physical_loc": SIZE_MEDIUM_LOC, "size_high_physical_loc": SIZE_HIGH_LOC,
            "size_medium_points": SIZE_MEDIUM_POINTS, "size_high_points": SIZE_HIGH_POINTS,
            "cycle_points": CYCLE_POINTS, "untested_points": UNTESTED_POINTS,
            "fan_in_incoming_edges": FAN_IN_THRESHOLD,
            "fan_in_points": FAN_IN_POINTS,
            "level_low_points": LEVEL_LOW_POINTS, "level_medium_points": LEVEL_MEDIUM_POINTS,
            "level_high_points": LEVEL_HIGH_POINTS, "top_risks_limit": MAX_TOP_RISKS,
        },
        "confidence": "high" if churn_available else "medium",
    }
