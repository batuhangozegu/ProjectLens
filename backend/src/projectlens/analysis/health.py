"""Versioned, explainable heuristic health indicator."""

from __future__ import annotations

from typing import Any, Sequence

from .models import DependencyEdge, FileRecord

FORMULA_VERSION = "1"
CYCLE_WEIGHT = 0.30
UNRESOLVED_IMPORT_WEIGHT = 0.20
TEST_PRESENCE_WEIGHT = 0.30
TODO_DENSITY_WEIGHT = 0.20
CYCLE_SATURATION_MULTIPLIER = 4.0
UNRESOLVED_SATURATION_MULTIPLIER = 2.0
TODO_MARKERS_PER_KLOC_SATURATION = 20.0
LOC_PER_KLOC = 1000.0

_COMPONENTS = (
    ("cycles", "Dependency cycles", CYCLE_WEIGHT),
    ("unresolved_imports", "Unresolved imports", UNRESOLVED_IMPORT_WEIGHT),
    ("test_presence", "Test file presence by name/import heuristic, not coverage", TEST_PRESENCE_WEIGHT),
    ("todo_density", "TODO/FIXME density", TODO_DENSITY_WEIGHT),
)


def compute_health(
    files: Sequence[FileRecord],
    dependency_edges: Sequence[DependencyEdge],
    cycles: Sequence[Sequence[str]],
    unresolved_imports: Sequence[dict[str, Any]],
    metrics: dict[str, Any],
    partial: bool,
) -> dict[str, Any]:
    """Calculate health from analyzer facts only; never infer missing values."""
    eligible = {f.path for f in files if f.language in {"python", "dart"} and f.file_class in {"python_source", "dart_source", "test"}}
    analyzed = {f.path for f in files if f.path in eligible and f.analysis_status.startswith("analyzed")}
    graph_nodes = {edge.source for edge in dependency_edges} | {edge.target for edge in dependency_edges}
    graph_nodes |= analyzed
    graph_files = eligible & graph_nodes
    cycle_files = {path for cycle in cycles for path in cycle} & eligible
    cycle_count, graph_count = len(cycle_files), len(graph_files)
    cycle_ratio = cycle_count / graph_count if graph_count else None

    local_references = sum(max(1, len(edge.evidence_lines)) for edge in dependency_edges)
    unresolved_count = len(unresolved_imports)
    import_total = local_references + unresolved_count
    unresolved_ratio = unresolved_count / import_total if import_total else None

    test_metrics = metrics.get("test_matching", {})
    source_count = test_metrics.get("sources_total", 0)
    matched_count = test_metrics.get("sources_with_matching_test", 0)
    test_ratio = matched_count / source_count if source_count else None

    marker_metrics = metrics.get("comment_markers", {})
    loc = sum(f.physical_loc or 0 for f in files if f.language in {"python", "dart"} and f.analysis_status.startswith("analyzed") and f.physical_loc is not None)
    markers = marker_metrics.get("total", 0)
    marker_incomplete = bool(marker_metrics.get("unavailable_files"))
    density = markers * LOC_PER_KLOC / loc if loc else None

    component_specs = (
        (cycle_ratio, cycle_count, graph_count, lambda r: 100 * (1 - min(1, CYCLE_SATURATION_MULTIPLIER * r)), f"{cycle_count} of {graph_count} graph files are in cycles ({cycle_ratio:.3f}); 25% saturates the penalty." if cycle_ratio is not None else f"No eligible Python/Dart graph files are available (0 denominator)."),
        (unresolved_ratio, unresolved_count, import_total, lambda r: 100 * (1 - min(1, UNRESOLVED_SATURATION_MULTIPLIER * r)), f"{unresolved_count} of {import_total} local or unresolved import references are unresolved ({unresolved_ratio:.3f}); external imports are excluded." if unresolved_ratio is not None else "No local or unresolved import references are available (0 denominator)."),
        (test_ratio, matched_count, source_count, lambda r: 100 * r, f"{matched_count} of {source_count} source files have a matching test file by name/import heuristic, not coverage ({test_ratio:.3f})." if test_ratio is not None else "No source files are available for test file presence by name/import heuristic, not coverage (0 denominator)."),
        (None if marker_incomplete else density, markers, loc, lambda d: 100 * (1 - min(1, d / TODO_MARKERS_PER_KLOC_SATURATION)), f"{markers} TODO/FIXME markers across {loc} physical LOC ({density:.1f} per KLOC); 20 per KLOC saturates the penalty." if density is not None and not marker_incomplete else (f"Marker data is incomplete ({len(marker_metrics.get('unavailable_files', []))} files unavailable), with {markers} known markers across {loc} LOC; TODO/FIXME density cannot be scored." if marker_incomplete else f"Known physical LOC is {loc} and marker count is {markers}; zero LOC prevents a density score.")),
    )

    components = []
    for (component_id, label, weight), (value, _numerator, _denominator, score_fn, reason) in zip(_COMPONENTS, component_specs):
        available = value is not None
        components.append({"id": component_id, "label": label, "weight": weight, "value": round(value, 4) if available else None,
                           "score": round(score_fn(value), 1) if available else None, "reason": reason, "available": available})
    available_components = [component for component in components if component["available"]]
    if len(available_components) >= 2:
        weight_total = sum(component["weight"] for component in available_components)
        score = round(sum(component["score"] * component["weight"] for component in available_components) / weight_total, 1)
        reason = f"Weighted mean of {len(available_components)} available components; weights renormalized to {weight_total:.2f}."
        level = "good" if score >= 80 else "fair" if score >= 60 else "attention" if score >= 40 else "poor"
        confidence = "high" if len(available_components) == 4 and not partial else "medium" if len(available_components) >= 3 else "low"
    else:
        score, level, confidence = None, None, "none"
        reason = f"Only {len(available_components)} of 4 components are available; at least 2 are required for an overall score."
    missing = [{"id": c["id"], "reason": c["reason"]} for c in components if not c["available"]]
    return {
        "formula_version": FORMULA_VERSION, "score": score, "level": level, "confidence": confidence,
        "partial": bool(partial), "reason": reason, "components": components, "missing": missing,
        "thresholds": {"cycle_saturation_multiplier": CYCLE_SATURATION_MULTIPLIER,
                       "cycle_saturation_ratio": 1 / CYCLE_SATURATION_MULTIPLIER,
                       "unresolved_import_saturation_multiplier": UNRESOLVED_SATURATION_MULTIPLIER,
                       "unresolved_import_saturation_ratio": 1 / UNRESOLVED_SATURATION_MULTIPLIER,
                       "todo_markers_per_kloc_saturation": TODO_MARKERS_PER_KLOC_SATURATION,
                       "loc_per_kloc": LOC_PER_KLOC,
                       "component_weights": {item[0]: item[2] for item in _COMPONENTS},
                       "levels": {"good": 80, "fair": 60, "attention": 40}},
        "basis": "heuristic indicator from static analysis; not a measure of correctness or coverage",
    }
