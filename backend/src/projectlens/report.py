"""Plain-text terminal reporting for analysis results."""

from __future__ import annotations

from projectlens.analysis.models import AnalysisResult


def format_summary(result: AnalysisResult, root: str, *, max_diagnostics: int = 5) -> str:
    metrics = result.metrics
    dependencies = metrics["dependencies"]
    markers = metrics["comment_markers"]
    lines = ["ProjectLens analysis", f"Root: {root}"]
    if result.partial:
        lines.extend(("*** PARTIAL RESULT: some files or directories could not be fully analyzed. ***", ""))
    lines.extend((
        f"Files: {metrics['total_file_count']} (Python: {metrics['python_file_count']})",
        f"Physical LOC: {metrics['physical_loc']['total']} (known: {metrics['physical_loc']['known_file_count']}, unavailable: {metrics['physical_loc']['unavailable_file_count']})",
        f"Python LOC: {metrics['python_loc']['total']} (known: {metrics['python_loc']['known_file_count']}, unavailable: {metrics['python_loc']['unavailable_file_count']})",
        "Largest files:",
    ))
    if metrics["largest_files"]:
        lines.extend(f"  {item['physical_loc']:>6} LOC  {item['path']}" for item in metrics["largest_files"])
    else:
        lines.append("  (none)")
    lines.extend((
        f"TODO/FIXME: {markers['total']} (TODO: {markers['by_kind']['TODO']}, FIXME: {markers['by_kind']['FIXME']})",
        f"Dependencies: {dependencies['edge_count']} local edges, {dependencies['external_import_count']} external, {dependencies['unresolved_import_count']} unresolved",
        f"Cycle groups: {dependencies['cycle_group_count']}",
    ))
    if result.cycles:
        for index, cycle in enumerate(result.cycles, start=1):
            lines.append(f"  {index}. " + ", ".join(cycle))
    else:
        lines.append("  (none)")
    lines.append(f"Diagnostics: {len(result.diagnostics)}")
    for diagnostic in result.diagnostics[:max_diagnostics]:
        location = f" [{diagnostic.file}]" if diagnostic.file else ""
        lines.append(f"  {diagnostic.stage}/{diagnostic.error_type}{location}: {diagnostic.message}")
    remaining = len(result.diagnostics) - min(len(result.diagnostics), max_diagnostics)
    if remaining:
        lines.append(f"  ... {remaining} more diagnostic(s) not shown")
    return "\n".join(lines)
