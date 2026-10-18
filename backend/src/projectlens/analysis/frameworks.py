"""Manifest-only framework detection using tolerant, non-executing text scans.

These scanners intentionally do not parse full TOML/YAML grammars (Python 3.10
has no stdlib TOML reader). They recognize common dependency declaration forms;
the evidence is the original bounded declaration line.
"""

from __future__ import annotations

import re
from collections.abc import Iterable

from .models import FrameworkRecord

_PYTHON = {
    "fastapi": "FastAPI", "django": "Django", "flask": "Flask",
    "starlette": "Starlette", "pytest": "pytest", "sqlalchemy": "SQLAlchemy",
    "pydantic": "Pydantic",
}
_DART = {
    "flutter": ("Flutter", "framework"), "flutter_test": ("Flutter Test", "test framework"),
    "riverpod": ("Riverpod", "state management"), "flutter_riverpod": ("Flutter Riverpod", "state management"),
    "bloc": ("Bloc", "state management"), "flutter_bloc": ("Flutter Bloc", "state management"),
    "provider": ("Provider", "state management"), "get": ("Get", "state management"),
}
_NAME = re.compile(r"^[\s\"']*([A-Za-z0-9][A-Za-z0-9_.-]*)")


def detect_frameworks(manifests: Iterable[tuple[str, str]]) -> tuple[FrameworkRecord, ...]:
    """Return known dependencies declared by (repository path, manifest text)."""
    found: set[FrameworkRecord] = set()
    for path, content in sorted(manifests):
        name = path.rsplit("/", 1)[-1].lower()
        if name == "pubspec.yaml":
            found.update(_scan_pubspec(path, content))
        elif name == "pyproject.toml":
            found.update(_scan_pyproject(path, content))
        elif name.startswith("requirements") and name.endswith(".txt"):
            found.update(_scan_requirements(path, content))
        elif name == "setup.cfg":
            found.update(_scan_setup_cfg(path, content))
    return tuple(sorted(found, key=lambda item: (item.ecosystem, item.name.casefold(), item.evidence_file, item.evidence)))


def _record(path: str, ecosystem: str, package: str, line: str) -> FrameworkRecord | None:
    package = package.lower().replace("_", "-") if ecosystem == "python" else package.lower()
    if ecosystem == "python":
        display = _PYTHON.get(package)
        if not display:
            return None
        return FrameworkRecord(display, ecosystem, path, line.strip()[:240])
    if package not in _DART:
        return None
    display, _ = _DART[package]
    return FrameworkRecord(display, ecosystem, path, line.strip()[:240])


def _package(text: str) -> str | None:
    match = _NAME.match(text.strip().lstrip("-").strip())
    return match.group(1).lower().replace("_", "-") if match else None


def _strip_toml_comment(line: str) -> str:
    quote = ""
    escaped = False
    for index, char in enumerate(line):
        if escaped:
            escaped = False
        elif char == "\\" and quote == '"':
            escaped = True
        elif quote:
            if char == quote:
                quote = ""
        elif char in "\"'":
            quote = char
        elif char == "#":
            return line[:index].rstrip()
    return line


def _scan_requirements(path: str, content: str) -> list[FrameworkRecord]:
    result = []
    for line in content.lstrip("\ufeff").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith(("#", "-", ".", "http:", "https:")):
            continue
        # A whitespace-delimited comment is removed; environment markers remain
        # after the package token and are ignored by the package-name matcher.
        declaration = re.split(r"\s+#", stripped, maxsplit=1)[0]
        package = _package(declaration)
        if package:
            record = _record(path, "python", package, stripped)
            if record:
                result.append(record)
    return result


def _scan_pyproject(path: str, content: str) -> list[FrameworkRecord]:
    result = []
    section = ""
    in_multiline = False
    for raw in content.lstrip("\ufeff").splitlines():
        line = _strip_toml_comment(raw).strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("[") and line.endswith("]"):
            section = line.strip("[] ").strip('"\'').lower()
            in_multiline = False
            continue
        relevant = section in {"project", "project.dependencies", "project.optional-dependencies", "tool.poetry.dependencies", "tool.poetry.dev-dependencies", "tool.poetry.group.dev.dependencies"}
        if not relevant:
            continue
        if section == "project" and re.match(r"dependencies\s*=", line, re.I):
            value = line.split("=", 1)[1]
            for package in re.findall(r"[\"']([A-Za-z0-9][A-Za-z0-9_.-]*)", value):
                record = _record(path, "python", package, raw)
                if record:
                    result.append(record)
            in_multiline = "]" not in value
            continue
        if section == "project" and re.match(r"optional-dependencies\s*=", line, re.I):
            value = line.split("=", 1)[1]
            for package in re.findall(r"[\"']([A-Za-z0-9][A-Za-z0-9_.-]*)", value):
                record = _record(path, "python", package, raw)
                if record:
                    result.append(record)
            in_multiline = "]" not in value
            continue
        if section in {"project.dependencies", "project.optional-dependencies"} and "=" in line and not in_multiline:
            value = line.split("=", 1)[1]
            for package in re.findall(r"[\"']([A-Za-z0-9][A-Za-z0-9_.-]*)", value):
                record = _record(path, "python", package, raw)
                if record:
                    result.append(record)
            in_multiline = "[" in value and "]" not in value
            continue
        if in_multiline:
            if "]" in line:
                in_multiline = False
            candidate = line.lstrip("- ").strip(",[] ")
            package = _package(candidate)
            if package:
                record = _record(path, "python", package, raw)
                if record:
                    result.append(record)
            continue
        # Poetry tables use dependency names as keys. PEP 621 inline arrays are
        # supported as well as the usual multiline arrays.
        key = re.match(r"[\"']?([A-Za-z0-9][A-Za-z0-9_.-]*)[\"']?\s*=", line)
        candidates = [key.group(1)] if key else []
        if section in {"project.dependencies", "project.optional-dependencies"} and "=" in line and not in_multiline:
            value = line.split("=", 1)[1]
            candidates.extend(match.group(1) for match in re.finditer(r"[\"']([A-Za-z0-9][A-Za-z0-9_.-]*)", value))
        for package in candidates:
            record = _record(path, "python", package, raw)
            if record:
                result.append(record)
    return result


def _scan_setup_cfg(path: str, content: str) -> list[FrameworkRecord]:
    result = []
    active = False
    for raw in content.lstrip("\ufeff").splitlines():
        stripped = raw.strip()
        if stripped.startswith("[") and stripped.endswith("]"):
            active = stripped.lower() == "[options]"
            continue
        if active and re.match(r"install_requires\s*=", stripped, re.I):
            continue
        if active and raw[:1].isspace() and stripped and not stripped.startswith("#"):
            package = _package(stripped)
            if package:
                record = _record(path, "python", package, stripped)
                if record:
                    result.append(record)
    return result


def _scan_pubspec(path: str, content: str) -> list[FrameworkRecord]:
    result = []
    current_section = ""
    dependency_indent = -1
    current_package: str | None = None
    package_indent = -1
    for raw in content.lstrip("\ufeff").splitlines():
        stripped = raw.strip()
        if not stripped or stripped.startswith("#"):
            continue
        indent = len(raw) - len(raw.lstrip())
        top = re.match(r"^(dependencies|dev_dependencies)\s*:\s*(?:#.*)?$", stripped)
        if indent == 0:
            current_section = top.group(1) if top else ""
            dependency_indent = indent if top else -1
            current_package = None
            package_indent = -1
            continue
        if not current_section or indent <= dependency_indent:
            current_package = None
            continue
        entry = re.match(r"^['\"]?([A-Za-z0-9_-]+)['\"]?\s*:\s*(.*)$", stripped)
        if entry and (package_indent < 0 or indent <= package_indent):
            current_package = entry.group(1).lower()
            package_indent = indent
            evidence = raw.strip()
            # Flutter itself is identified by its SDK declaration.
            if current_package == "flutter" and re.search(r"\bsdk\s*:\s*['\"]?flutter['\"]?", stripped):
                result.append(FrameworkRecord("Flutter", "dart", path, evidence[:240]))
            elif current_package != "flutter":
                record = _record(path, "dart", current_package, evidence)
                if record:
                    result.append(record)
            continue
        if current_package == "flutter" and re.match(r"^sdk\s*:\s*['\"]?flutter['\"]?", stripped):
            result.append(FrameworkRecord("Flutter", "dart", path, raw.strip()[:240]))
    return result
