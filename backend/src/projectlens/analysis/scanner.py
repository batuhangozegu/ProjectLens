"""Deterministic, non-executing repository file discovery.

File class labels are deliberately heuristic and are not semantic analysis.
The scanner reads ordinary files only to count physical lines; it never imports
or executes repository code.
"""

from __future__ import annotations

import fnmatch
import json
import os
from dataclasses import dataclass
from pathlib import Path

from .models import AnalysisDiagnostic, AnalysisOptions, FileRecord, RESULT_MARKER_KEY, RESULT_MARKER_VALUE


class ScanError(ValueError):
    """Fatal root validation failure."""


def _os_error_message(exc: OSError) -> str:
    """Keep machine-specific filenames out of deterministic result JSON."""
    return exc.strerror or type(exc).__name__


@dataclass(frozen=True)
class ScanResult:
    files: tuple[FileRecord, ...]
    diagnostics: tuple[AnalysisDiagnostic, ...]


_EXCLUDED_DIRS = {
    ".git", ".venv", "venv", "env", "__pycache__", ".mypy_cache",
    ".pytest_cache", ".ruff_cache", ".tox", "node_modules", "build", "dist", ".eggs", ".dart_tool",
}
_LANGUAGES = {
    ".py": "python", ".pyi": "python", ".js": "javascript", ".jsx": "javascript",
    ".ts": "typescript", ".tsx": "typescript", ".java": "java", ".kt": "kotlin",
    ".go": "go", ".rs": "rust", ".c": "c", ".h": "c", ".cpp": "cpp",
    ".cc": "cpp", ".hpp": "cpp", ".cs": "csharp", ".rb": "ruby", ".php": "php",
    ".swift": "swift", ".dart": "dart", ".sh": "shell", ".yaml": "yaml",
    ".yml": "yaml", ".toml": "toml", ".json": "json", ".xml": "xml", ".md": "markdown",
}
_CONFIG_NAMES = {"pyproject.toml", "setup.cfg", "setup.py", "tox.ini", "config.yaml", "config.yml", ".editorconfig", "makefile", "dockerfile", "pubspec.yaml", "pubspec.lock", "analysis_options.yaml"}


def normalize_repo_path(path: str) -> str:
    """Normalize a repository-relative path, including Windows separators."""
    return path.replace("\\", "/").strip("/")


def _classify(path: str, language: str | None) -> str:
    name = path.rsplit("/", 1)[-1].lower()
    parts = path.lower().split("/")
    if language == "python" and (name.startswith("test_") or name.endswith("_test.py") or name == "conftest.py" or "tests" in parts):
        return "test"
    if language == "dart" and (name.endswith("_test.dart") or "test" in parts or "integration_test" in parts):
        return "test"
    if name in _CONFIG_NAMES or name.endswith((".toml", ".ini", ".cfg", ".yaml", ".yml", ".json")) or name.startswith(".") and name in {".gitignore", ".dockerignore"}:
        return "config"
    if name in {"readme", "changelog", "license", "contributing"} or name.endswith((".md", ".rst", ".txt")):
        return "documentation"
    if language == "python":
        return "python_source"
    if language == "dart":
        return "dart_source"
    return "other"


def _excluded(rel: str, is_dir: bool, patterns: tuple[str, ...]) -> bool:
    parts = rel.split("/")
    if any(part in _EXCLUDED_DIRS or part.endswith(".egg-info") for part in parts[:-1] if not is_dir) or is_dir and (parts[-1] in _EXCLUDED_DIRS or parts[-1].endswith(".egg-info")):
        return True
    if any(fnmatch.fnmatchcase(rel, pat) or fnmatch.fnmatchcase(parts[-1], pat) for pat in patterns):
        return True
    return False


def scan_repository(options: AnalysisOptions) -> ScanResult:
    """Scan a local directory; per-entry OS failures become diagnostics."""
    root = Path(options.root_path)
    if not root.exists():
        raise ScanError(f"repository root does not exist: {root}")
    if not root.is_dir():
        raise ScanError(f"repository root is not a directory: {root}")
    try:
        with os.scandir(root):
            pass
    except OSError as exc:
        raise ScanError(f"repository root is not readable: {root}: {exc}") from exc

    patterns = tuple(options.exclude_patterns)
    files: list[FileRecord] = []
    diagnostics: list[AnalysisDiagnostic] = []
    exact_exclusions: dict[Path, str] = {}
    try:
        root_resolved = root.resolve()
        for configured in options.excluded_paths:
            candidate = Path(configured).resolve(strict=False)
            try:
                relative = normalize_repo_path(os.path.relpath(candidate, root_resolved))
            except ValueError:
                continue
            if relative == ".." or relative.startswith("../") or os.path.isabs(relative):
                continue
            exact_exclusions[candidate] = relative
            diagnostics.append(AnalysisDiagnostic("scan", relative, "Excluded", "analysis output path excluded"))
    except OSError:
        exact_exclusions = {}
    pending = [root]
    while pending:
        directory = pending.pop()
        try:
            with os.scandir(directory) as entries:
                children = sorted(entries, key=lambda e: normalize_repo_path(os.path.relpath(e.path, root)).casefold())
        except OSError as exc:
            rel_dir = "" if directory == root else normalize_repo_path(os.path.relpath(directory, root))
            diagnostics.append(AnalysisDiagnostic("scan", rel_dir or None, "UnreadableDirectory", _os_error_message(exc)))
            continue
        subdirs = []
        for entry in children:
            rel = normalize_repo_path(os.path.relpath(entry.path, root))
            try:
                if entry.is_symlink():
                    diagnostics.append(AnalysisDiagnostic("scan", rel, "SymlinkSkipped", "symlink was not followed or read"))
                elif entry.is_dir(follow_symlinks=False):
                    resolved_entry = Path(entry.path).resolve(strict=False)
                    if resolved_entry in exact_exclusions:
                        continue
                    if _excluded(rel, True, patterns):
                        diagnostics.append(AnalysisDiagnostic("scan", rel, "Excluded", "directory excluded by scanner rules"))
                    else:
                        # Cheap virtualenv marker detection.
                        try:
                            if any(os.path.isfile(os.path.join(entry.path, marker)) for marker in ("pyvenv.cfg",)):
                                diagnostics.append(AnalysisDiagnostic("scan", rel, "Excluded", "virtual environment detected by pyvenv.cfg"))
                                continue
                        except OSError:
                            pass
                        subdirs.append(Path(entry.path))
                elif entry.is_file(follow_symlinks=False):
                    resolved_entry = Path(entry.path).resolve(strict=False)
                    if resolved_entry in exact_exclusions:
                        continue
                    if _excluded(rel, False, patterns):
                        diagnostics.append(AnalysisDiagnostic("scan", rel, "Excluded", "file excluded by scanner rules"))
                        continue
                    language = _LANGUAGES.get(Path(rel).suffix.lower())
                    try:
                        size = entry.stat(follow_symlinks=False).st_size
                        if size > options.max_file_size_bytes:
                            status, loc = "skipped_size_limit", None
                            diagnostics.append(AnalysisDiagnostic("scan", rel, "FileTooLarge", f"{size} bytes exceeds limit of {options.max_file_size_bytes}"))
                        else:
                            with open(entry.path, "rb") as stream:
                                data = stream.read()
                            if Path(rel).suffix.lower() == ".json" and _is_projectlens_result(data):
                                diagnostics.append(AnalysisDiagnostic("scan", rel, "Excluded", "ProjectLens result JSON excluded"))
                                continue
                            status = "scanned"
                            loc = len(data.splitlines())
                    except OSError as exc:
                        status, loc = "unreadable", None
                        diagnostics.append(AnalysisDiagnostic("scan", rel, "UnreadableFile", _os_error_message(exc)))
                    files.append(FileRecord(rel, language, _classify(rel, language), loc, status))
            except OSError as exc:
                diagnostics.append(AnalysisDiagnostic("scan", rel, "ScanEntryError", _os_error_message(exc)))
        pending.extend(reversed(subdirs))
    files.sort(key=lambda item: item.path)
    diagnostics.sort(key=lambda item: (item.file or "", item.error_type, item.message))
    return ScanResult(tuple(files), tuple(diagnostics))


def _is_projectlens_result(data: bytes) -> bool:
    """Recognize a ProjectLens export by its stable top-level format marker."""
    try:
        value = json.loads(data)
    except (UnicodeDecodeError, json.JSONDecodeError, RecursionError):
        return False
    return isinstance(value, dict) and value.get(RESULT_MARKER_KEY) == RESULT_MARKER_VALUE
