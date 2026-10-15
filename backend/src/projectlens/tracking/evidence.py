"""Pure, versioned evaluation of code-aware task evidence.

Rule contract (formula version 1)
=================================
Snapshots are plain AnalysisResult dictionaries. Paths are repository-relative:
backslashes are converted to ``/``, leading ``./`` segments are removed, and
absolute paths or any ``..`` segment are invalid. A fully analyzed file has
status ``scanned``, ``analyzed`` or ``analyzed_with_diagnostics``; the latter
still counts as fully analyzed for file presence. ``parse_failed``,
``unreadable`` and ``skipped_size_limit`` are not fully analyzed.

Supported automatic criteria are ``file_exists {path}``,
``path_has_files {prefix, min_count=1, language?, file_class?}``,
``import_edge_exists {source, target}``, ``not_in_cycle {path}``,
``max_todo_markers {path, max}``, and ``no_analysis_failures {path}``.
``path_has_files`` requires a trailing slash and min_count in 1..100000.
``max_todo_markers`` accepts a file or trailing-slash prefix. Known marker
counts exceeding max prove failure even if some files are unavailable; counts
at or below max with incomplete coverage are unknown. Missing paths in a
partial snapshot are generally unknown where absence cannot be established.
Unknown kinds, malformed parameters and unsafe paths return ``unknown`` with
an ``invalid_criterion: ...`` reason. ``manual_attestation {}`` is always
unknown to automatic evaluation and its optional ``attested`` value is reported
separately; it never affects the estimate.

The estimate uses automatic criteria only. ``automatic_percent`` is
``met / (met + unmet) * 100`` using integer arithmetic and round-half-up to
one decimal place; unknown outcomes do not enter the denominator. If there
are no met or unmet automatic criteria, percent is ``None``, confidence is
``none`` and state is ``insufficient_evidence`` (never 0% or 100%). Otherwise
state is ``estimated``. Confidence is high with at least 3 evaluated criteria,
zero unknown automatic criteria and a complete snapshot; medium with at least
2 evaluated criteria and no more unknown criteria than evaluated criteria;
otherwise low. The threshold is first selected from the evaluated/unknown
counts (three clean evaluated criteria select high); a partial snapshot then
lowers that selected level one step (high to medium, medium to low; low stays
low).

Links are sorted context only: they report path existence and, for directories,
the number of fully analyzed files below the prefix. Links have zero weight.
With links and no criteria, the estimate is insufficient and its reason states
that linked-file existence is not completion evidence. Attestations are
reported as attested/total and do not affect confidence or percent.

Manual states are TODO, IN_PROGRESS, DONE and BLOCKED and are never changed.
DONE with a non-null estimate below 100% diverges as ``done_but_unmet``.
TODO or BLOCKED with a 100% estimate and medium/high confidence diverges as
``evidence_complete_but_not_done``. IN_PROGRESS never triggers divergence.
Evidence arrays are capped at 20 entries; when capped, the last item is the
literal ``truncated`` marker. All emitted mappings and lists are JSON-safe and
deterministically ordered.
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

FORMULA_VERSION = "1"
STATUSES = ("TODO", "IN_PROGRESS", "DONE", "BLOCKED")
FULLY_ANALYZED = frozenset(("scanned", "analyzed", "analyzed_with_diagnostics"))
FAILED_ANALYSIS = frozenset(("parse_failed", "unreadable", "skipped_size_limit"))
_EVIDENCE_LIMIT = 20


@dataclass(frozen=True)
class CriterionInput:
    id: int | str
    kind: str
    params: Mapping[str, Any]
    description: str = ""
    attested: bool | None = None

    def to_dict(self) -> dict[str, Any]:
        return {"id": self.id, "kind": self.kind, "params": _json_value(self.params),
                "description": self.description, "attested": self.attested}


@dataclass(frozen=True)
class LinkInput:
    path: str

    def to_dict(self) -> dict[str, str]:
        return {"path": self.path}


@dataclass(frozen=True)
class SnapshotInfo:
    partial: bool
    schema_version: Any = None
    id: Any = None
    commit: Any = None

    @classmethod
    def from_snapshot(cls, snapshot: Mapping[str, Any], snapshot_meta: Mapping[str, Any] | None = None) -> "SnapshotInfo":
        meta = snapshot_meta if isinstance(snapshot_meta, Mapping) else {}
        return cls(bool(snapshot.get("partial", False)), snapshot.get("schema_version"),
                   meta.get("id"), meta.get("commit", meta.get("commit_sha")))

    def to_dict(self) -> dict[str, Any]:
        value = {"partial": self.partial, "schema_version": _json_value(self.schema_version)}
        if self.id is not None:
            value["id"] = _json_value(self.id)
        if self.commit is not None:
            value["commit"] = _json_value(self.commit)
        return value


@dataclass(frozen=True)
class CriterionResult:
    criterion_id: int | str
    kind: str
    outcome: str
    reason: str
    evidence: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {"criterion_id": self.criterion_id, "kind": self.kind, "outcome": self.outcome,
                "reason": self.reason, "evidence": list(self.evidence)}


@dataclass(frozen=True)
class TaskAssessment:
    formula_version: str
    state: str
    manual_status: str
    estimated_percent: float | None
    confidence: str
    reasons: tuple[str, ...]
    criteria_results: tuple[CriterionResult, ...]
    unknown_criteria: tuple[Mapping[str, Any], ...]
    attestations: Mapping[str, int]
    context: tuple[Mapping[str, Any], ...]
    divergence: str | None
    divergence_reason: str | None
    snapshot: SnapshotInfo | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "formula_version": self.formula_version, "state": self.state,
            "manual_status": self.manual_status, "estimated_percent": self.estimated_percent,
            "confidence": self.confidence, "reasons": list(self.reasons),
            "criteria_results": [item.to_dict() for item in self.criteria_results],
            "unknown_criteria": [_json_value(item) for item in self.unknown_criteria],
            "attestations": dict(self.attestations), "context": [_json_value(item) for item in self.context],
            "divergence": self.divergence, "divergence_reason": self.divergence_reason,
            "snapshot": self.snapshot.to_dict() if self.snapshot else None,
        }


def _json_value(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, Mapping):
        return {str(key): _json_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_value(item) for item in value]
    return str(value)


def _bounded(items: Sequence[str]) -> tuple[str, ...]:
    if len(items) <= _EVIDENCE_LIMIT:
        return tuple(items)
    return tuple(items[:_EVIDENCE_LIMIT - 1]) + ("truncated",)


def _path(value: Any, *, prefix: bool = False) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError("path must be a non-empty string")
    value = value.replace("\\", "/")
    while value.startswith("./"):
        value = value[2:]
    if value.startswith("/") or (len(value) >= 2 and value[1] == ":"):
        raise ValueError("absolute paths are not allowed")
    parts = value.split("/")
    if ".." in parts:
        raise ValueError("'..' path segments are not allowed")
    if any(ord(ch) < 32 for ch in value):
        raise ValueError("control characters are not allowed")
    if prefix and not value.endswith("/"):
        raise ValueError("prefix must end with '/'")
    if not prefix and value.endswith("/"):
        raise ValueError("expected a file path, not a directory prefix")
    return value


def _files(snapshot: Mapping[str, Any]) -> list[dict[str, Any]]:
    raw = snapshot.get("files", ())
    if not isinstance(raw, (list, tuple)):
        return []
    return sorted((dict(item) for item in raw if isinstance(item, Mapping)), key=lambda item: str(item.get("path", "")))


def _matching_files(snapshot: Mapping[str, Any], path: str) -> list[dict[str, Any]]:
    if path.endswith("/"):
        return [item for item in _files(snapshot) if isinstance(item.get("path"), str) and item["path"].replace("\\", "/").startswith(path)]
    return [item for item in _files(snapshot) if item.get("path", "").replace("\\", "/") == path]


def _edges(snapshot: Mapping[str, Any]) -> list[dict[str, Any]]:
    raw = snapshot.get("dependency_edges", ())
    return [dict(item) for item in raw if isinstance(item, Mapping)] if isinstance(raw, (list, tuple)) else []


def _invalid(criterion: CriterionInput, error: str) -> CriterionResult:
    return CriterionResult(getattr(criterion, "id", ""), str(getattr(criterion, "kind", "")),
                          "unknown", f"invalid_criterion: {error}", ())


def evaluate_criterion(snapshot: Mapping[str, Any], criterion: CriterionInput) -> CriterionResult:
    """Evaluate one criterion without raising for malformed criterion data."""
    try:
        if not isinstance(snapshot, Mapping):
            raise ValueError("snapshot must be a mapping")
        if not isinstance(criterion, CriterionInput):
            raise ValueError("criterion must be a CriterionInput")
        if not isinstance(criterion.kind, str) or not isinstance(criterion.params, Mapping):
            raise ValueError("kind must be a string and params must be a mapping")
        kind, params = criterion.kind, criterion.params
        partial = bool(snapshot.get("partial", False))
        files = _files(snapshot)
        if kind == "manual_attestation":
            if params:
                raise ValueError("manual_attestation takes no params")
            return CriterionResult(criterion.id, kind, "unknown", "manual attestation is user-reported, not automatic evidence", ())
        if kind == "file_exists":
            _keys(params, {"path"})
            path = _path(params["path"])
            found = next((f for f in files if f.get("path") == path), None)
            if found is None:
                return CriterionResult(criterion.id, kind, "unknown" if partial else "unmet",
                    "file is absent from a partial snapshot" if partial else "file is absent from the snapshot", (path,))
            status = found.get("analysis_status")
            if status in FULLY_ANALYZED:
                return CriterionResult(criterion.id, kind, "met", "file is present and analyzed", (path, str(status)))
            if status in FAILED_ANALYSIS:
                return CriterionResult(criterion.id, kind, "unknown", f"file exists but is not fully analyzed ({status})", (path, str(status)))
            return CriterionResult(criterion.id, kind, "unknown", f"file analysis status is not recognized ({status})", (path, str(status)))
        if kind == "path_has_files":
            _keys(params, {"prefix", "min_count", "language", "file_class"}, {"prefix"})
            path = _path(params["prefix"], prefix=True)
            minimum = params.get("min_count", 1)
            if isinstance(minimum, bool) or not isinstance(minimum, int) or not 1 <= minimum <= 100000:
                raise ValueError("min_count must be an integer from 1 to 100000")
            for key in ("language", "file_class"):
                if key in params and not isinstance(params[key], str):
                    raise ValueError(f"{key} must be a string")
            covered = [f for f in files if str(f.get("path", "")).replace("\\", "/").startswith(path)
                       and f.get("analysis_status") in FULLY_ANALYZED
                       and all(key not in params or f.get(key) == params[key] for key in ("language", "file_class"))]
            if len(covered) >= minimum:
                return CriterionResult(criterion.id, kind, "met", f"found {len(covered)} fully analyzed matching files (minimum {minimum})", _bounded(tuple(str(f.get("path")) for f in covered)))
            outcome = "unknown" if partial else "unmet"
            return CriterionResult(criterion.id, kind, outcome, f"found {len(covered)} fully analyzed matching files; minimum is {minimum}" + (" and snapshot is partial" if partial else ""), _bounded(tuple(str(f.get("path")) for f in covered)))
        if kind == "import_edge_exists":
            _keys(params, {"source", "target"})
            source, target = _path(params["source"]), _path(params["target"])
            found = any(edge.get("source") == source and edge.get("target") == target for edge in _edges(snapshot))
            if found:
                edge = next(edge for edge in _edges(snapshot) if edge.get("source") == source and edge.get("target") == target)
                return CriterionResult(criterion.id, kind, "met", "local import edge is present", _bounded((source, target, *(str(x) for x in edge.get("evidence_lines", ()) if isinstance(x, (str, int))))))
            states = {f.get("path"): f.get("analysis_status") for f in files}
            incomplete = any(path not in states or states[path] not in FULLY_ANALYZED for path in (source, target))
            outcome = "unknown" if incomplete or partial else "unmet"
            reason = "source or target file is absent or not fully analyzed" if incomplete else ("edge is absent from a partial snapshot" if partial else "local import edge is absent")
            return CriterionResult(criterion.id, kind, outcome, reason, (source, target))
        if kind == "not_in_cycle":
            _keys(params, {"path"})
            path = _path(params["path"])
            found = any(isinstance(group, (list, tuple)) and path in group for group in snapshot.get("cycles", ()) if isinstance(snapshot.get("cycles", ()), (list, tuple)))
            if not any(f.get("path") == path for f in files):
                return CriterionResult(criterion.id, kind, "unknown", "file is absent from the snapshot", (path,))
            if found:
                members = sorted({str(member) for group in snapshot.get("cycles", ()) if isinstance(group, (list, tuple)) and path in group for member in group})
                return CriterionResult(criterion.id, kind, "unmet", "file belongs to a dependency cycle", _bounded(tuple(members)))
            file_record = next(f for f in files if f.get("path") == path)
            if partial and file_record.get("analysis_status") not in FULLY_ANALYZED:
                return CriterionResult(criterion.id, kind, "unknown", "file is not fully analyzed in a partial snapshot", (path,))
            return CriterionResult(criterion.id, kind, "met", "file is not in a reported dependency cycle", (path,))
        if kind == "max_todo_markers":
            _keys(params, {"path", "max"})
            path = _path(params["path"], prefix=str(params["path"]).endswith("/"))
            maximum = params["max"]
            if isinstance(maximum, bool) or not isinstance(maximum, int) or maximum < 0:
                raise ValueError("max must be a non-negative integer")
            covered = _matching_files(snapshot, path)
            if not covered:
                return CriterionResult(criterion.id, kind, "unknown", "no files are covered by this path", (path,))
            metrics = snapshot.get("metrics", {})
            markers = metrics.get("comment_markers", {}) if isinstance(metrics, Mapping) else {}
            by_file = markers.get("by_file", {}) if isinstance(markers, Mapping) else {}
            unavailable = set(markers.get("unavailable_files", ())) if isinstance(markers, Mapping) and isinstance(markers.get("unavailable_files", ()), (list, tuple)) else set()
            total = 0
            incomplete: list[str] = []
            for record in covered:
                fp = str(record.get("path", ""))
                marker = by_file.get(fp, {}) if isinstance(by_file, Mapping) else {}
                if isinstance(marker, Mapping) and fp in by_file:
                    count = marker.get("total", 0)
                    if isinstance(count, int) and not isinstance(count, bool) and count >= 0:
                        total += count
                    if marker.get("available") is False or fp in unavailable or record.get("analysis_status") not in FULLY_ANALYZED:
                        incomplete.append(fp)
                else:
                    incomplete.append(fp)
            evidence = _bounded(tuple([*(f"{fp}: TODO/FIXME data incomplete" for fp in sorted(set(incomplete))), f"known total: {total}"]))
            if total > maximum:
                return CriterionResult(criterion.id, kind, "unmet", f"known marker total {total} exceeds maximum {maximum}" + ("; more markers may exist" if incomplete else ""), evidence)
            if incomplete:
                return CriterionResult(criterion.id, kind, "unknown", f"known marker total {total} is within maximum {maximum}, but coverage is incomplete", evidence)
            return CriterionResult(criterion.id, kind, "met", f"marker total {total} is at most {maximum}", evidence)
        if kind == "no_analysis_failures":
            _keys(params, {"path"})
            path = _path(params["path"], prefix=str(params["path"]).endswith("/"))
            covered = _matching_files(snapshot, path)
            if not covered:
                return CriterionResult(criterion.id, kind, "unknown", "no files are covered by this path", (path,))
            failed = sorted(str(f.get("path")) for f in covered if f.get("analysis_status") in FAILED_ANALYSIS)
            if failed:
                return CriterionResult(criterion.id, kind, "unmet", "one or more covered files have analysis failures", _bounded(tuple(failed)))
            return CriterionResult(criterion.id, kind, "met", "no covered files have a known analysis failure", _bounded(tuple(str(f.get("path")) for f in covered)))
        raise ValueError(f"unknown criterion kind {kind!r}")
    except (ValueError, TypeError, KeyError, AttributeError) as exc:
        return _invalid(criterion, str(exc))


def _keys(params: Mapping[str, Any], allowed: set[str], required: set[str] | None = None) -> None:
    required = allowed if required is None else required
    extra = set(params) - allowed
    missing = required - set(params)
    if extra or missing:
        raise ValueError(f"unexpected params {sorted(extra)}; missing params {sorted(missing)}")


def _rounded_percent(met: int, evaluated: int) -> float:
    tenths, remainder = divmod(met * 1000, evaluated)
    if remainder * 2 >= evaluated:
        tenths += 1
    return tenths / 10


def _context(snapshot: Mapping[str, Any], links: Sequence[LinkInput]) -> tuple[Mapping[str, Any], ...]:
    output = []
    paths = sorted((_path(link.path, prefix=link.path.replace("\\", "/").endswith("/")) for link in links))
    for path in paths:
        matched = _matching_files(snapshot, path)
        exists = bool(matched)
        item: dict[str, Any] = {"path": path, "exists": exists}
        if path.endswith("/"):
            analyzed = [f for f in matched if f.get("analysis_status") in FULLY_ANALYZED]
            item["analyzed_file_count"] = len(analyzed)
            item["files"] = list(_bounded(tuple(str(f.get("path")) for f in analyzed)))
        else:
            record = matched[0] if matched else None
            item["analysis_status"] = record.get("analysis_status") if record else None
            item["analyzed"] = bool(record and record.get("analysis_status") in FULLY_ANALYZED)
        output.append(item)
    return tuple(output)


def _assess(snapshot: Mapping[str, Any] | None, manual_status: str, criteria: Sequence[CriterionInput], links: Sequence[LinkInput], snapshot_meta: Mapping[str, Any] | None) -> TaskAssessment:
    if manual_status not in STATUSES:
        raise ValueError(f"Unknown task status {manual_status!r}; expected one of {', '.join(STATUSES)}")
    if snapshot is None:
        attested = [criterion for criterion in criteria if criterion.kind == "manual_attestation"]
        results = tuple(CriterionResult(item.id, item.kind, "unknown",
            "manual attestation is user-reported, not automatic evidence" if item.kind == "manual_attestation" else "no analysis snapshot is available", ())
            for item in criteria)
        unknown = tuple({"id": result.criterion_id, "reason": result.reason}
                        for result in results if result.kind != "manual_attestation")
        return TaskAssessment(FORMULA_VERSION, "no_snapshot", manual_status, None, "none",
            ("No analysis snapshot is available; progress cannot be estimated.",), results, unknown,
            {"attested": sum(item.attested is True for item in attested), "total": len(attested)}, (), None, None, None)
    if not isinstance(snapshot, Mapping):
        raise ValueError("snapshot must be a mapping")
    results = tuple(evaluate_criterion(snapshot, criterion) for criterion in criteria)
    automatic = [result for result in results if result.kind != "manual_attestation"]
    met = sum(result.outcome == "met" for result in automatic)
    unmet = sum(result.outcome == "unmet" for result in automatic)
    unknown = [result for result in automatic if result.outcome == "unknown"]
    evaluated = met + unmet
    percent = _rounded_percent(met, evaluated) if evaluated else None
    partial = bool(snapshot.get("partial", False))
    if not evaluated:
        confidence, state = "none", "insufficient_evidence"
    else:
        state = "estimated"
        if evaluated >= 3 and not unknown:
            confidence = "high"
        elif evaluated >= 2 and len(unknown) <= evaluated:
            confidence = "medium"
        else:
            confidence = "low"
        if partial:
            confidence = {"high": "medium", "medium": "low", "low": "low"}[confidence]
    reasons = []
    if evaluated:
        reasons.append(f"Estimate uses {met} met and {unmet} unmet automatic criteria; {len(unknown)} unknown criteria are excluded from the percentage.")
        reasons.append(f"Confidence is {confidence}{' because the snapshot is partial.' if partial else '.'}")
    else:
        reasons.append("No automatic criteria produced met or unmet evidence, so no percentage is estimated.")
        if links and not criteria:
            reasons.append("Linked files provide context only; their existence is not completion evidence.")
        elif unknown:
            reasons.append(f"All {len(unknown)} automatic criteria are unknown.")
    if any(result.kind == "manual_attestation" for result in results):
        reasons.append("Manual attestations are reported separately and do not affect the estimate.")
    attestations = [criterion for criterion in criteria if criterion.kind == "manual_attestation"]
    attestation_counts = {"attested": sum(item.attested is True for item in attestations), "total": len(attestations)}
    divergence = divergence_reason = None
    if manual_status == "DONE" and percent is not None and percent < 100.0:
        divergence = "done_but_unmet"
        divergence_reason = "Manual status is DONE while automatic evidence estimates less than 100% completion."
    elif manual_status in ("TODO", "BLOCKED") and percent == 100.0 and confidence in ("medium", "high"):
        divergence = "evidence_complete_but_not_done"
        divergence_reason = "Automatic evidence estimates 100% with medium or high confidence while manual status is not DONE."
    unknown_items = tuple({"id": result.criterion_id, "reason": result.reason} for result in unknown)
    return TaskAssessment(FORMULA_VERSION, state, manual_status, percent, confidence, tuple(reasons), results,
        unknown_items, attestation_counts, _context(snapshot, links), divergence, divergence_reason,
        SnapshotInfo.from_snapshot(snapshot, snapshot_meta))


def assess_task(snapshot: Mapping[str, Any], *, manual_status: str, criteria: Sequence[CriterionInput], links: Sequence[LinkInput], snapshot_meta: Mapping[str, Any] | None = None) -> TaskAssessment:
    """Assess a task from its stored analysis snapshot and plain inputs."""
    return _assess(snapshot, manual_status, criteria, links, snapshot_meta)


def assess_without_snapshot(manual_status: str, criteria: Sequence[CriterionInput], links: Sequence[LinkInput]) -> TaskAssessment:
    """Return an explicit no-snapshot assessment without automatic evidence."""
    return _assess(None, manual_status, criteria, links, None)
