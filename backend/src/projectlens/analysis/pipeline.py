"""Synchronous orchestration for deterministic local repository analysis."""

from __future__ import annotations

from dataclasses import asdict, replace
from pathlib import Path

from .dependency import build_dependency_graph
from .languages.base import LanguageParser
from .languages.dart import DartParser
from .languages.python import PythonParser, decode_source
from .metrics import compute_metrics
from .models import AnalysisDiagnostic, AnalysisOptions, AnalysisResult, FileRecord, ParsedFile
from .scanner import scan_repository


_PARSERS: tuple[LanguageParser, ...] = (PythonParser(), DartParser())
_FATAL_PARSE_DIAGNOSTICS = {
    "SyntaxError", "NullByteError", "ValueError", "EncodingError", "RecursionError", "MemoryError",
}
_PARTIAL_SCAN_DIAGNOSTICS = {
    "UnreadableDirectory", "UnreadableFile", "ScanEntryError", "FileTooLarge",
}


def analyze(options: AnalysisOptions, *, largest_limit: int = 10) -> AnalysisResult:
    """Scan, parse, resolve dependencies, and measure a repository.

    Fatal root validation errors from the scanner propagate as ``ScanError``.
    Problems attached to individual files or scan entries are returned as
    diagnostics and represented in file statuses, while other files continue.
    """
    scan = scan_repository(options)
    root = Path(options.root_path)
    records: list[FileRecord] = []
    parsed_files: list[ParsedFile] = []
    diagnostics = list(scan.diagnostics)

    for record in scan.files:
        if record.analysis_status != "scanned":
            records.append(record)
            continue

        parser = next((candidate for candidate in _PARSERS if candidate.supports(record.path)), None)
        if parser is None:
            records.append(record)
            continue

        try:
            data = (root / Path(record.path)).read_bytes()
        except OSError as exc:
            diagnostic = AnalysisDiagnostic("read", record.path, "UnreadableFile", exc.strerror or type(exc).__name__)
            diagnostics.append(diagnostic)
            records.append(replace(record, analysis_status="unreadable"))
            continue

        source, decode_diagnostic = decode_source(data, record.path)
        if decode_diagnostic is not None:
            parsed = ParsedFile(record.path, diagnostics=(decode_diagnostic,))
        else:
            try:
                parsed = parser.parse(record.path, source or "")
            except Exception as exc:  # parser-specific failures remain file-local
                parsed = ParsedFile(
                    record.path,
                    diagnostics=(AnalysisDiagnostic("parse", record.path, "ParserError", f"{type(exc).__name__}: {exc}"),),
                )
        parsed_files.append(parsed)
        diagnostics.extend(parsed.diagnostics)
        kinds = {item.error_type for item in parsed.diagnostics}
        if kinds & _FATAL_PARSE_DIAGNOSTICS or "ParserError" in kinds:
            status = "parse_failed"
        elif parsed.diagnostics:
            status = "analyzed_with_diagnostics"
        else:
            status = "analyzed"
        records.append(replace(record, analysis_status=status))

    python_paths = [item.path for item in records if item.language == "python"]
    dependency = build_dependency_graph(python_paths, parsed_files)
    diagnostics.extend(dependency.diagnostics)
    metrics = compute_metrics(records, parsed_files, dependency, largest_limit=largest_limit)
    partial = any(item.analysis_status in {"unreadable", "skipped_size_limit", "parse_failed", "analyzed_with_diagnostics"} for item in records)
    partial = partial or any(item.error_type in _PARTIAL_SCAN_DIAGNOSTICS for item in diagnostics)

    return AnalysisResult(
        files=tuple(records),
        dependency_edges=dependency.edges,
        cycles=dependency.cycle_groups,
        external_imports=tuple(asdict(item) for item in dependency.external_imports),
        unresolved_imports=tuple(asdict(item) for item in dependency.unresolved_imports),
        metrics=metrics,
        diagnostics=tuple(sorted(diagnostics, key=lambda item: (item.stage, item.file or "", item.error_type, item.message))),
        partial=partial,
    )
