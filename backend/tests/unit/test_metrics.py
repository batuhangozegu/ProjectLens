import pytest

from projectlens.analysis.dependency import build_dependency_graph
from projectlens.analysis.languages.python import PythonParser
from projectlens.analysis.metrics import compute_metrics
from projectlens.analysis.models import FileRecord


def measure(files=(), parsed=(), largest_limit=10):
    dependencies = build_dependency_graph([item.path for item in files if item.language == "python"], parsed)
    return compute_metrics(files, parsed, dependencies, largest_limit=largest_limit)


def test_empty_repository_metrics():
    result = measure()
    assert result["total_file_count"] == result["python_file_count"] == 0
    assert result["physical_loc"]["total"] == result["python_loc"]["total"] == 0
    assert result["largest_files"] == []
    assert result["comment_markers"]["total"] == 0
    assert result["dependencies"] == {
        "edge_count": 0, "external_import_count": 0,
        "unresolved_import_count": 0, "cycle_group_count": 0,
    }


def test_non_python_files_count_toward_total_and_loc_only():
    files = (FileRecord("README.md", None, "documentation", 3, "scanned"), FileRecord("data.bin", None, "other", None, "unreadable"))
    result = measure(files)
    assert result["total_file_count"] == 2
    assert result["python_file_count"] == 0
    assert result["physical_loc"] == {"total": 3, "known_file_count": 1, "unavailable_file_count": 1, "unavailable_files": ["data.bin"]}
    assert result["python_loc"]["total"] == 0


def test_largest_files_ties_sort_by_path_and_limit_is_configurable():
    files = tuple(FileRecord(path, None, "other", 2, "scanned") for path in ("z.txt", "a.txt", "b.txt"))
    assert measure(files, largest_limit=2)["largest_files"] == [
        {"path": "a.txt", "physical_loc": 2}, {"path": "b.txt", "physical_loc": 2},
    ]
    with pytest.raises(ValueError):
        measure(files, largest_limit=-1)


def test_markers_count_parser_comment_occurrences_per_kind_and_file():
    files = (FileRecord("a.py", "python", "python_source", 2, "analyzed"),)
    parsed = (PythonParser().parse("a.py", 'value = "TODO FIXME"\n# TODO FIXME TODOs FIXME!\n'),)
    markers = measure(files, parsed)["comment_markers"]
    assert markers["total"] == 3
    assert markers["by_kind"] == {"TODO": 1, "FIXME": 2}
    assert markers["by_file"] == {"a.py": {"TODO": 1, "FIXME": 2, "total": 3, "available": True}}


def test_marker_string_without_parsed_comment_data_is_reported_unavailable():
    files = (FileRecord("skip.py", "python", "python_source", None, "skipped_size_limit"),)
    markers = measure(files)["comment_markers"]
    assert markers["total"] == 0
    assert markers["unavailable_files"] == ["skip.py"]
