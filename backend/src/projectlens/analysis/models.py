"""Stable, standard-library data contracts for repository analysis."""

from __future__ import annotations

import json
import posixpath
from dataclasses import asdict, dataclass, field
from pathlib import PureWindowsPath
from typing import Any

SCHEMA_VERSION = "4"
RESULT_MARKER_KEY = "projectlens_format"
RESULT_MARKER_VALUE = "projectlens-analysis"


def _repo_path(path: str) -> str:
    """Use the schema's platform-independent path separator."""
    normalized = posixpath.normpath(path.replace("\\", "/"))
    if normalized.startswith("/") or PureWindowsPath(path).drive or normalized == ".." or normalized.startswith("../"):
        raise ValueError("repository paths must be relative to the repository root")
    return normalized


@dataclass(frozen=True)
class AnalysisOptions:
    root_path: str
    exclude_patterns: tuple[str, ...] = ()
    max_file_size_bytes: int = 1_000_000
    excluded_paths: tuple[str, ...] = ()
    git_history: bool = False
    history_days: int = 180

    def __post_init__(self) -> None:
        if type(self.history_days) is not int or not 1 <= self.history_days <= 3650:
            raise ValueError("history_days must be between 1 and 3650")


@dataclass(frozen=True)
class FileRecord:
    path: str
    language: str | None
    file_class: str
    physical_loc: int | None
    analysis_status: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "path", _repo_path(self.path))


@dataclass(frozen=True)
class SymbolRecord:
    file: str
    name: str
    kind: str
    start_line: int
    end_line: int

    def __post_init__(self) -> None:
        object.__setattr__(self, "file", _repo_path(self.file))


@dataclass(frozen=True)
class ImportRecord:
    source_file: str
    module: str | None
    imported_names: tuple[str, ...] = ()
    relative_level: int = 0
    line: int = 0

    def __post_init__(self) -> None:
        object.__setattr__(self, "source_file", _repo_path(self.source_file))


@dataclass(frozen=True)
class AnalysisDiagnostic:
    stage: str
    file: str | None
    error_type: str
    message: str

    def __post_init__(self) -> None:
        if self.file is not None:
            object.__setattr__(self, "file", _repo_path(self.file))


@dataclass(frozen=True)
class ParsedFile:
    path: str
    symbols: tuple[SymbolRecord, ...] = ()
    imports: tuple[ImportRecord, ...] = ()
    comment_markers: tuple[str, ...] = ()
    diagnostics: tuple[AnalysisDiagnostic, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "path", _repo_path(self.path))


@dataclass(frozen=True)
class DependencyEdge:
    source: str
    target: str
    import_line: int
    evidence_lines: tuple[int, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "source", _repo_path(self.source))
        object.__setattr__(self, "target", _repo_path(self.target))
        lines = tuple(sorted(set(self.evidence_lines or (self.import_line,))))
        object.__setattr__(self, "evidence_lines", lines)
        object.__setattr__(self, "import_line", lines[0] if lines else self.import_line)


@dataclass(frozen=True)
class FrameworkRecord:
    name: str
    ecosystem: str
    evidence_file: str
    evidence: str
    kind: str = "manifest"

    def __post_init__(self) -> None:
        object.__setattr__(self, "evidence_file", _repo_path(self.evidence_file))


@dataclass(frozen=True)
class TestMatchRecord:
    source: str
    tests: tuple[dict[str, str], ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "source", _repo_path(self.source))
        object.__setattr__(self, "tests", tuple({"path": _repo_path(item["path"]), "rule": item["rule"]} for item in self.tests))


@dataclass(frozen=True)
class AnalysisResult:
    files: tuple[FileRecord, ...] = ()
    dependency_edges: tuple[DependencyEdge, ...] = ()
    cycles: tuple[tuple[str, ...], ...] = ()
    external_imports: tuple[dict[str, Any], ...] = ()
    unresolved_imports: tuple[dict[str, Any], ...] = ()
    frameworks: tuple[FrameworkRecord, ...] = ()
    test_matches: tuple[TestMatchRecord, ...] = ()
    metrics: dict[str, Any] = field(default_factory=dict)
    diagnostics: tuple[AnalysisDiagnostic, ...] = ()
    partial: bool = False
    schema_version: str = SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        """Return a canonical JSON-compatible structure with stable collection ordering."""
        value = asdict(self)
        value[RESULT_MARKER_KEY] = RESULT_MARKER_VALUE
        value["files"] = [asdict(item) for item in sorted(self.files, key=lambda item: item.path)]
        value["dependency_edges"] = [
            asdict(item)
            for item in sorted(self.dependency_edges, key=lambda item: (item.source, item.target, item.evidence_lines))
        ]
        value["cycles"] = [
            sorted(_repo_path(path) for path in cycle)
            for cycle in sorted(self.cycles, key=lambda cycle: tuple(sorted(_repo_path(path) for path in cycle)))
        ]
        for key in ("external_imports", "unresolved_imports"):
            value[key] = [
                dict(item)
                for item in sorted(getattr(self, key), key=lambda item: (
                    item["source_file"], item["line"], item["module"], item["kind"]
                ))
            ]
        value["frameworks"] = [asdict(item) for item in sorted(self.frameworks, key=lambda item: (item.ecosystem, item.name.casefold(), item.evidence_file, item.evidence))]
        value["test_matches"] = [
            {"source": item.source, "tests": [dict(test) for test in sorted(item.tests, key=lambda test: (0 if test["rule"] == "import" else 1, test["path"]))]}
            for item in sorted(self.test_matches, key=lambda item: item.source)
        ]
        value["diagnostics"] = [
            asdict(item)
            for item in sorted(
                self.diagnostics,
                key=lambda item: (item.stage, item.file or "", item.error_type, item.message),
            )
        ]
        return value

    def to_json(self) -> str:
        """Serialize without timestamps or other run-specific metadata."""
        return json.dumps(self.to_dict(), ensure_ascii=False, sort_keys=True, separators=(",", ":"))

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> AnalysisResult:
        return cls(
            files=tuple(FileRecord(**item) for item in value.get("files", ())),
            dependency_edges=tuple(DependencyEdge(**item) for item in value.get("dependency_edges", ())),
            cycles=tuple(tuple(cycle) for cycle in value.get("cycles", ())),
            external_imports=tuple(dict(item) for item in value.get("external_imports", ())),
            unresolved_imports=tuple(dict(item) for item in value.get("unresolved_imports", ())),
            frameworks=tuple(FrameworkRecord(**item) for item in value.get("frameworks", ())),
            test_matches=tuple(TestMatchRecord(item["source"], tuple(dict(test) for test in item.get("tests", ()))) for item in value.get("test_matches", ())),
            metrics=value.get("metrics", {}),
            diagnostics=tuple(AnalysisDiagnostic(**item) for item in value.get("diagnostics", ())),
            partial=value.get("partial", False),
            schema_version=value.get("schema_version", SCHEMA_VERSION),
        )

    @classmethod
    def from_json(cls, content: str) -> AnalysisResult:
        return cls.from_dict(json.loads(content))
