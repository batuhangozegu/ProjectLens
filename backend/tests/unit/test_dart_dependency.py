from __future__ import annotations

import random

from projectlens.analysis.dependency_dart import build_dart_dependency_graph, read_pubspec_name
from projectlens.analysis.models import ImportRecord, ParsedFile


def graph(paths, imports, specs):
    parsed = [ParsedFile(path, imports=tuple(ImportRecord(path, uri, (), 0, line) for uri, line in imports.get(path, []))) for path in paths]
    return build_dart_dependency_graph(paths, parsed, specs)


def edges(result):
    return [(item.source, item.target) for item in result.edges]


def test_uri_kinds_local_packages_and_merge_evidence():
    result = graph(
        ["lib/a.dart", "lib/b.dart", "lib/self.dart", "lib/alone.dart"],
        {"lib/a.dart": [("package:app/b.dart", 1), ("./b.dart", 2), ("dart:core", 3), ("package:external/x.dart", 4), ("missing.dart", 5), ("https://example/a.dart", 6), ("file:///tmp/a.dart", 7), ("package:app/not_scanned.dart", 8)], "lib/self.dart": [("self.dart", 9)]},
        {"pubspec.yaml": "app"},
    )
    assert edges(result) == [("lib/a.dart", "lib/b.dart"), ("lib/self.dart", "lib/self.dart")]
    assert result.edges[0].evidence_lines == (1, 2)
    assert [(item.module, item.kind) for item in result.external_imports] == [("dart:core", "dart_sdk"), ("package:external/x.dart", "package")]
    assert [(item.module, item.kind) for item in result.unresolved_imports] == [
        ("missing.dart", "missing_local_file"),
        ("https://example/a.dart", "unsupported_uri"),
        ("file:///tmp/a.dart", "unsupported_uri"),
        ("package:app/not_scanned.dart", "missing_local_file"),
    ]
    assert result.cycle_groups == (("lib/self.dart",),)
    assert result.incoming_counts["lib/alone.dart"] == result.outgoing_counts["lib/alone.dart"] == 0


def test_nearest_package_roots_and_duplicate_names():
    result = graph(
        ["lib/root.dart", "packages/one/lib/a.dart", "packages/two/lib/b.dart", "packages/two/lib/c.dart"],
        {"packages/two/lib/b.dart": [("package:app/c.dart", 1), ("package:dupe/x.dart", 2)]},
        {"pubspec.yaml": "app", "packages/two/pubspec.yaml": "app", "packages/one/pubspec.yaml": "one", "packages/other/pubspec.yaml": "dupe", "packages/another/pubspec.yaml": "dupe"},
    )
    # Nearest package owns a file, but duplicate package names are always ambiguous.
    assert not result.edges
    assert [(item.kind, item.module) for item in result.unresolved_imports] == [("ambiguous_package", "package:app/c.dart"), ("ambiguous_package", "package:dupe/x.dart")]
    assert {d.error_type for d in result.diagnostics} == {"AmbiguousPackageName"}


def test_local_package_resolution_uses_nearest_declared_package():
    result = graph(["lib/a.dart", "packages/sub/lib/a.dart", "packages/sub/lib/b.dart"], {"packages/sub/lib/b.dart": [("package:sub/a.dart", 1)]}, {"pubspec.yaml": "root", "packages/sub/pubspec.yaml": "sub"})
    assert edges(result) == [("packages/sub/lib/b.dart", "packages/sub/lib/a.dart")]


def test_escape_cycle_and_input_order_determinism():
    paths = ["lib/a.dart", "lib/b.dart", "lib/c.dart"]
    imports = {"lib/a.dart": [("../../outside.dart", 1), ("b.dart", 2)], "lib/b.dart": [("a.dart", 3)]}
    expected = graph(paths, imports, {})
    assert expected.cycle_groups == (("lib/a.dart", "lib/b.dart"),)
    assert expected.unresolved_imports[0].kind == "path_escapes_repository"
    random.Random(5).shuffle(paths)
    assert graph(paths, imports, {}) == expected


def test_pubspec_reader_handles_bom_quotes_comments_and_crlf():
    assert read_pubspec_name("\ufeff# comment\r\nname: 'my_app' # comment\r\n") == "my_app"
    assert read_pubspec_name("dependencies:\n  name: nested\n") is None
    assert read_pubspec_name("name: [odd, value]\n") is None
