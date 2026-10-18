"""Deterministic heuristic findings for oversized symbols and coupling."""

from __future__ import annotations

from collections import Counter
from typing import Sequence

from .models import DependencyEdge, FileRecord, ParsedFile

FORMULA_VERSION = "1"
LARGE_FUNCTION_LINES = 80
LARGE_FUNCTION_WARNING_LINES = 150
LARGE_CLASS_LINES = 400
LARGE_CLASS_WARNING_LINES = 800
MANY_MEMBERS_COUNT = 30
MANY_MEMBERS_WARNING_COUNT = 60
HIGH_FAN_OUT_COUNT = 15
HIGH_FAN_OUT_WARNING_COUNT = 30
HIGH_FAN_IN_COUNT = 10
MAX_FINDINGS = 50

_KINDS = ("large_function", "large_class", "many_members", "high_fan_out", "high_fan_in", "mutual_dependency")
_CONTAINERS = {"class", "mixin", "enum", "extension"}
_GENERATED_SUFFIXES = (".g.dart", ".freezed.dart", ".gr.dart")


def compute_findings(
    files: Sequence[FileRecord], parsed_files: Sequence[ParsedFile],
    dependency_edges: Sequence[DependencyEdge], cycles: Sequence[Sequence[str]],
) -> dict:
    """Return sorted static size/coupling findings without mutating inputs."""
    del cycles  # Cycles already have their own report and are intentionally not duplicated.
    records = {item.path: item for item in files if item.analysis_status.startswith("analyzed")}
    parsed = {item.path: item for item in parsed_files}
    findings: list[dict] = []

    def add(kind: str, severity: str, path: str, symbol: str | None, start: int | None,
            end: int | None, value: int, threshold: int, reason: str) -> None:
        identity = f"{kind}:{path}" + (f":{symbol}" if symbol is not None else "")
        findings.append({"id": identity, "kind": kind, "severity": severity, "path": path,
                         "symbol": symbol, "start_line": start, "end_line": end,
                         "value": value, "threshold": threshold, "reason": reason})

    for path, record in sorted(records.items()):
        source = parsed.get(path)
        if source is None or record.file_class == "test" or path.lower().endswith(_GENERATED_SUFFIXES):
            continue
        symbols = [s for s in source.symbols if s.end_line >= s.start_line]
        for symbol in symbols:
            span = symbol.end_line - symbol.start_line + 1
            if symbol.kind in {"function", "method"} and span >= LARGE_FUNCTION_LINES:
                severity = "warning" if span >= LARGE_FUNCTION_WARNING_LINES else "notice"
                add("large_function", severity, path, symbol.name, symbol.start_line, symbol.end_line, span,
                    LARGE_FUNCTION_LINES, f"Function spans {span} lines; threshold is {LARGE_FUNCTION_LINES} lines.")
            elif symbol.kind in _CONTAINERS and span >= LARGE_CLASS_LINES:
                severity = "warning" if span >= LARGE_CLASS_WARNING_LINES else "notice"
                add("large_class", severity, path, symbol.name, symbol.start_line, symbol.end_line, span,
                    LARGE_CLASS_LINES, f"Class-like declaration spans {span} lines; threshold is {LARGE_CLASS_LINES} lines.")
        containers = [s for s in symbols if s.kind in _CONTAINERS]
        methods = [s for s in symbols if s.kind == "method"]
        for container in containers:
            prefix = container.name + "."
            count = sum(1 for method in methods if method.name.startswith(prefix)
                        and "." not in method.name[len(prefix):])
            if count >= MANY_MEMBERS_COUNT:
                severity = "warning" if count >= MANY_MEMBERS_WARNING_COUNT else "notice"
                add("many_members", severity, path, container.name, container.start_line, container.end_line,
                    count, MANY_MEMBERS_COUNT,
                    f"Class-like declaration has {count} direct methods; threshold is {MANY_MEMBERS_COUNT} methods.")

    neighbors_out: dict[str, set[str]] = {path: set() for path in records}
    neighbors_in: dict[str, set[str]] = {path: set() for path in records}
    for edge in dependency_edges:
        if edge.source in records and edge.target in records:
            neighbors_out[edge.source].add(edge.target)
            neighbors_in[edge.target].add(edge.source)
    for path in sorted(records):
        out_count = len(neighbors_out[path])
        if out_count >= HIGH_FAN_OUT_COUNT:
            severity = "warning" if out_count >= HIGH_FAN_OUT_WARNING_COUNT else "notice"
            add("high_fan_out", severity, path, None, None, None, out_count, HIGH_FAN_OUT_COUNT,
                f"File has {out_count} distinct local dependencies; threshold is {HIGH_FAN_OUT_COUNT}.")
        in_count = len(neighbors_in[path])
        if in_count >= HIGH_FAN_IN_COUNT:
            add("high_fan_in", "notice", path, None, None, None, in_count, HIGH_FAN_IN_COUNT,
                f"File has {in_count} distinct local dependents; threshold is {HIGH_FAN_IN_COUNT}; it is a central dependency where changes have wide impact, not necessarily a defect.")

    findings.sort(key=lambda item: (0 if item["severity"] == "warning" else 1, -item["value"], item["path"], item["symbol"] or "", item["kind"]))
    counts_kind = Counter(item["kind"] for item in findings)
    counts_severity = Counter(item["severity"] for item in findings)
    thresholds = {
        "large_function": {"notice_lines": LARGE_FUNCTION_LINES, "warning_lines": LARGE_FUNCTION_WARNING_LINES},
        "large_class": {"notice_lines": LARGE_CLASS_LINES, "warning_lines": LARGE_CLASS_WARNING_LINES},
        "many_members": {"notice_count": MANY_MEMBERS_COUNT, "warning_count": MANY_MEMBERS_WARNING_COUNT},
        "high_fan_out": {"notice_count": HIGH_FAN_OUT_COUNT, "warning_count": HIGH_FAN_OUT_WARNING_COUNT},
        "high_fan_in": {"notice_count": HIGH_FAN_IN_COUNT},
        "mutual_dependency": {"skipped": "Two-file strongly connected pairs are already represented as cycles."},
    }
    return {"formula_version": FORMULA_VERSION,
            "basis": "static size/coupling thresholds; heuristic, not a defect prediction",
            "counts_by_kind": {kind: counts_kind[kind] for kind in _KINDS},
            "counts_by_severity": {severity: counts_severity[severity] for severity in ("warning", "notice")},
            "total": len(findings), "truncated": len(findings) > MAX_FINDINGS,
            "top_findings": findings[:MAX_FINDINGS], "thresholds": thresholds}
