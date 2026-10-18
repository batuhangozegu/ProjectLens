"""Explainable source-to-test name and resolved-import heuristics."""

from __future__ import annotations

import posixpath
from collections import Counter, defaultdict
from collections.abc import Sequence

from .models import DependencyEdge, FileRecord, TestMatchRecord

_GENERATED = (".g.dart", ".freezed.dart")


def match_tests(files: Sequence[FileRecord], edges: Sequence[DependencyEdge]) -> tuple[tuple[TestMatchRecord, ...], dict[str, object]]:
    records = {item.path: item for item in files}
    sources = sorted(item.path for item in files if item.file_class in {"python_source", "dart_source"} and not _excluded(item.path))
    tests = sorted(item.path for item in files if item.file_class == "test" and not _excluded(item.path))
    imports: dict[str, set[str]] = defaultdict(set)
    for edge in edges:
        if records.get(edge.source) and records[edge.source].file_class == "test" and records.get(edge.target) and records[edge.target].file_class in {"python_source", "dart_source"}:
            imports[edge.target].add(edge.source)

    output = []
    counts: Counter[str] = Counter()
    for source in sources:
        matches: dict[str, str] = {path: "import" for path in imports.get(source, ()) if path in tests}
        for test in tests:
            if test not in matches and _name_matches(source, test, records):
                matches[test] = "name"
        ordered = tuple({"path": path, "rule": matches[path]} for path in sorted(matches, key=lambda path: (0 if matches[path] == "import" else 1, path)))
        counts.update(match["rule"] for match in ordered)
        output.append(TestMatchRecord(source, ordered))
    matched = sum(bool(item.tests) for item in output)
    summary: dict[str, object] = {
        "sources_total": len(sources),
        "sources_with_matching_test": matched,
        "sources_without": len(sources) - matched,
        "by_rule": {rule: counts[rule] for rule in ("import", "name")},
        "basis": "name/import heuristics; not coverage",
    }
    return tuple(output), summary


def _excluded(path: str) -> bool:
    name = path.rsplit("/", 1)[-1].lower()
    return name in {"__init__.py", "conftest.py"} or name.endswith(_GENERATED)


def _name_matches(source: str, test: str, records: dict[str, FileRecord]) -> bool:
    source_record = records[source]
    test_record = records[test]
    source_name = source.rsplit("/", 1)[-1]
    test_name = test.rsplit("/", 1)[-1]
    if source_record.language == "python" and test_record.language == "python":
        stem = source_name[:-3] if source_name.endswith(".py") else source_name
        expected = {f"test_{stem}.py", f"{stem}_test.py"}
        if test_name in expected:
            return True
        parts = test.split("/")
        if "tests" in parts:
            index = len(parts) - 1 - parts[::-1].index("tests")
            relative = "/".join(parts[index + 1:])
            return relative in {source, source_name, f"test_{source_name}", f"test_{stem}.py", f"{stem}_test.py"}
    if source_record.language == "dart" and test_record.language == "dart":
        source_root = _package_root(source)
        test_root = _package_root(test)
        if source_root != test_root:
            return False
        lib_prefix = f"{source_root}/lib/" if source_root else "lib/"
        test_prefix = f"{source_root}/test/" if source_root else "test/"
        if source.startswith(lib_prefix) and test.startswith(test_prefix):
            relative = source[len(lib_prefix):]
            mirrored = test_prefix + relative[:-5] + "_test.dart"
            if test == mirrored:
                return True
        source_stem = source_name[:-5]
        return test_name == source_stem + "_test.dart"
    return False


def _package_root(path: str) -> str:
    parts = path.split("/")
    for index in range(len(parts) - 1, -1, -1):
        if parts[index] in {"lib", "test", "integration_test"}:
            return "/".join(parts[:index])
    return posixpath.dirname(path)
