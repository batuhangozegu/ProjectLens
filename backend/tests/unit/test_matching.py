from projectlens.analysis.models import DependencyEdge, FileRecord
from projectlens.analysis.test_matching import match_tests


def file(path, language, file_class):
    return FileRecord(path, language, file_class, 1, "scanned")


def test_python_test_name_and_tests_directory_mirror():
    files = (
        file("src/alpha.py", "python", "python_source"),
        file("src/beta.py", "python", "python_source"),
        file("tests/test_alpha.py", "python", "test"),
        file("tests/src/beta.py", "python", "test"),
        file("src/alone.py", "python", "python_source"),
    )
    matches, summary = match_tests(files, ())
    assert [(item.source, item.tests) for item in matches] == [
        ("src/alone.py", ()),
        ("src/alpha.py", ({"path": "tests/test_alpha.py", "rule": "name"},)),
        ("src/beta.py", ({"path": "tests/src/beta.py", "rule": "name"},)),
    ]
    assert summary["sources_without"] == 1
    assert summary["by_rule"] == {"import": 0, "name": 2}


def test_resolved_test_import_matches_even_without_name_similarity():
    files = (file("src/model.py", "python", "python_source"), file("tests/unrelated.py", "python", "test"))
    matches, summary = match_tests(files, (DependencyEdge("tests/unrelated.py", "src/model.py", 2),))
    assert matches[0].tests == ({"path": "tests/unrelated.py", "rule": "import"},)
    assert summary["by_rule"]["import"] == 1


def test_dart_mirror_and_basename_fallback_with_exclusions():
    files = (
        file("pkg/lib/src/a.dart", "dart", "dart_source"),
        file("pkg/lib/other.dart", "dart", "dart_source"),
        file("pkg/test/src/a_test.dart", "dart", "test"),
        file("pkg/test/other_test.dart", "dart", "test"),
        file("pkg/test/ignored_test.g.dart", "dart", "test"),
        file("pkg/lib/gen.g.dart", "dart", "dart_source"),
    )
    matches, summary = match_tests(files, ())
    by_source = {item.source: item.tests for item in matches}
    assert by_source == {
        "pkg/lib/other.dart": ({"path": "pkg/test/other_test.dart", "rule": "name"},),
        "pkg/lib/src/a.dart": ({"path": "pkg/test/src/a_test.dart", "rule": "name"},),
    }
    assert summary["sources_total"] == 2


def test_test_files_and_python_support_files_are_never_sources():
    files = (
        file("tests/test_mod.py", "python", "test"),
        file("conftest.py", "python", "test"),
        file("src/__init__.py", "python", "python_source"),
        file("src/foo_test.py", "python", "test"),
        file("src/foo.py", "python", "python_source"),
    )
    matches, summary = match_tests(files, ())
    assert [item.source for item in matches] == ["src/foo.py"]
    assert summary["sources_without"] == 0 and summary["sources_with_matching_test"] == 1
