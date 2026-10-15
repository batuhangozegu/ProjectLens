import pytest

from projectlens.app.criteria_validation import validate_criterion_params
from projectlens.app.path_validation import normalize_file_path, normalize_task_path


@pytest.mark.parametrize(("raw", "expected"), [
    ("./src\\pkg//a.py", "src/pkg/a.py"),
    ("src//pkg///", "src/pkg/"),
    ("café/文件.py", "café/文件.py"),
    ("./src/", "src/"),
])
def test_normalize_paths(raw, expected):
    assert normalize_task_path(raw) == expected


@pytest.mark.parametrize("raw", ["", "./", "/etc/passwd", "\\\\server\\share", "C:\\src\\a.py",
                                  "../secret", "src/../secret", "a\x00b", "a\nb", "a" * 501])
def test_reject_unsafe_or_long_paths(raw):
    with pytest.raises(ValueError):
        normalize_task_path(raw)


def test_file_path_rejects_directory_prefix():
    with pytest.raises(ValueError):
        normalize_file_path("src/pkg/")


@pytest.mark.parametrize(("kind", "params", "expected"), [
    ("file_exists", {"path": "./src\\a.py"}, {"path": "src/a.py"}),
    ("path_has_files", {"prefix": "src\\pkg\\", "language": "python"}, {"prefix": "src/pkg/", "language": "python", "min_count": 1}),
    ("import_edge_exists", {"source": "a.py", "target": "./b.py"}, {"source": "a.py", "target": "b.py"}),
    ("not_in_cycle", {"path": "x.py"}, {"path": "x.py"}),
    ("max_todo_markers", {"path": "src/", "max": 0}, {"path": "src/", "max": 0}),
    ("no_analysis_failures", {"path": "src/a.py"}, {"path": "src/a.py"}),
    ("manual_attestation", {}, {}),
])
def test_criterion_params_by_kind(kind, params, expected):
    assert validate_criterion_params(kind, params) == expected


@pytest.mark.parametrize(("kind", "params"), [
    ("file_exists", {"path": "a/", "extra": 1}),
    ("path_has_files", {"prefix": "src", "min_count": 1}),
    ("path_has_files", {"prefix": "src/", "min_count": True}),
    ("path_has_files", {"prefix": "src/", "language": "x" * 41}),
    ("import_edge_exists", {"source": "a.py"}),
    ("not_in_cycle", {"path": "../x.py"}),
    ("max_todo_markers", {"path": "x.py", "max": -1}),
    ("no_analysis_failures", {"path": "x.py", "unknown": True}),
    ("manual_attestation", {"path": "x.py"}),
])
def test_criterion_params_reject_invalid_contract(kind, params):
    with pytest.raises(ValueError):
        validate_criterion_params(kind, params)
