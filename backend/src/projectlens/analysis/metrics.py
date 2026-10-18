"""Deterministic repository metrics over scanner and parser output."""

from __future__ import annotations

from collections import Counter
from typing import Any, Sequence

from .dependency import DependencyGraphResult
from .models import FileRecord, ParsedFile


def compute_metrics(
    files: Sequence[FileRecord],
    parsed_files: Sequence[ParsedFile],
    dependencies: DependencyGraphResult,
    *,
    largest_limit: int = 10,
) -> dict[str, Any]:
    """Compute size, parser marker, and dependency facts without touching disk.

    LOC sums include only files for which the scanner obtained a line count.
    The accompanying known/unavailable counts make that partial coverage clear.
    Marker totals count only parser-produced comment tokens; unavailable files
    are listed so callers do not mistake an unknown count for zero.
    """
    if largest_limit < 0:
        raise ValueError("largest_limit must be non-negative")

    ordered_files = tuple(sorted(files, key=lambda item: item.path))
    python_files = tuple(item for item in ordered_files if item.language == "python")
    known_loc = [item for item in ordered_files if item.physical_loc is not None]
    known_python_loc = [item for item in python_files if item.physical_loc is not None]
    parsed_by_path = {item.path: item for item in parsed_files}

    marker_counts: dict[str, dict[str, int]] = {}
    unavailable_markers: list[str] = []
    totals = Counter()
    for file in ordered_files:
        if file.language not in {"python", "dart"}:
            continue
        parsed = parsed_by_path.get(file.path)
        counts = Counter()
        complete = parsed is not None
        if parsed is not None:
            for marker in parsed.comment_markers:
                kind = marker.split(":", 1)[0]
                if kind in ("TODO", "FIXME"):
                    counts[kind] += 1
            if any(d.error_type in ("EncodingError", "TokenizeError") for d in parsed.diagnostics):
                complete = False
            if file.language == "dart" and any(d.error_type == "SyntaxError" for d in parsed.diagnostics):
                complete = False
        if not complete:
            unavailable_markers.append(file.path)
        normalized = {kind: counts[kind] for kind in ("TODO", "FIXME")}
        normalized["total"] = sum(normalized.values())
        normalized["available"] = complete
        marker_counts[file.path] = normalized
        totals.update({kind: counts[kind] for kind in ("TODO", "FIXME")})

    largest = sorted(
        (item for item in ordered_files if item.physical_loc is not None),
        key=lambda item: (-item.physical_loc, item.path),
    )[:largest_limit]

    return {
        "total_file_count": len(ordered_files),
        "python_file_count": len(python_files),
        "physical_loc": {
            "total": sum(item.physical_loc or 0 for item in known_loc),
            "known_file_count": len(known_loc),
            "unavailable_file_count": len(ordered_files) - len(known_loc),
            "unavailable_files": [item.path for item in ordered_files if item.physical_loc is None],
        },
        "python_loc": {
            "total": sum(item.physical_loc or 0 for item in known_python_loc),
            "known_file_count": len(known_python_loc),
            "unavailable_file_count": len(python_files) - len(known_python_loc),
            "unavailable_files": [item.path for item in python_files if item.physical_loc is None],
        },
        "largest_files": [
            {"path": item.path, "physical_loc": item.physical_loc} for item in largest
        ],
        "comment_markers": {
            "total": sum(totals.values()),
            "by_kind": {kind: totals[kind] for kind in ("TODO", "FIXME")},
            "by_file": marker_counts,
            "unavailable_files": unavailable_markers,
        },
        "dependencies": {
            "edge_count": len(dependencies.edges),
            "external_import_count": len(dependencies.external_imports),
            "unresolved_import_count": len(dependencies.unresolved_imports),
            "cycle_group_count": len(dependencies.cycle_groups),
        },
    }
