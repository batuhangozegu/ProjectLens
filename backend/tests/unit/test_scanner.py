import os

import pytest

from projectlens.analysis.models import AnalysisOptions
from projectlens.analysis.scanner import ScanError, normalize_repo_path, scan_repository


def scan(path, **kwargs):
    return scan_repository(AnalysisOptions(str(path), **kwargs))


def test_empty_and_stable_sorted_tree(tmp_path):
    assert scan(tmp_path).files == ()
    (tmp_path / "z.py").write_text("x\n")
    (tmp_path / "a" / "b").mkdir(parents=True)
    (tmp_path / "a" / "b" / "test_x.py").write_text("\n")
    first, second = scan(tmp_path), scan(tmp_path)
    assert first == second
    assert [f.path for f in first.files] == ["a/b/test_x.py", "z.py"]
    assert all("\\" not in f.path for f in first.files)
    assert first.files[0].physical_loc == 1


def test_default_and_custom_exclusions(tmp_path):
    for folder in (".git", ".venv", "node_modules", "pkg.egg-info", "normal"):
        (tmp_path / folder).mkdir()
        (tmp_path / folder / "x.py").write_text("pass\n")
    (tmp_path / "keep.py").write_text("pass\n")
    result = scan(tmp_path, exclude_patterns=("keep.py",))
    assert [f.path for f in result.files] == ["normal/x.py"]
    assert len([d for d in result.diagnostics if d.error_type == "Excluded"]) == 5


def test_size_limit_keeps_record_without_loc(tmp_path):
    (tmp_path / "large.py").write_bytes(b"12345")
    result = scan(tmp_path, max_file_size_bytes=4)
    record = result.files[0]
    assert record.analysis_status == "skipped_size_limit"
    assert record.physical_loc is None
    assert result.diagnostics[0].error_type == "FileTooLarge"


def test_invalid_root(tmp_path):
    with pytest.raises(ScanError, match="does not exist"):
        scan(tmp_path / "missing")
    file = tmp_path / "file"
    file.write_text("x")
    with pytest.raises(ScanError, match="not a directory"):
        scan(file)


def test_paths_and_classification(tmp_path):
    assert normalize_repo_path(r"src\pkg\x.py") == "src/pkg/x.py"
    for name, expected in (("test_a.py", "test"), ("conftest.py", "test"), ("settings.toml", "config"), ("README.md", "documentation"), ("main.py", "python_source"), ("blob.bin", "other")):
        (tmp_path / name).write_text("")
    result = scan(tmp_path)
    assert {f.path: f.file_class for f in result.files} == {"test_a.py": "test", "conftest.py": "test", "settings.toml": "config", "README.md": "documentation", "main.py": "python_source", "blob.bin": "other"}


def test_unreadable_file_is_diagnostic(tmp_path, monkeypatch):
    (tmp_path / "bad.py").write_text("pass\n")
    real_open = open
    def failing_open(path, *args, **kwargs):
        if os.fspath(path).endswith("bad.py"):
            raise PermissionError("denied")
        return real_open(path, *args, **kwargs)
    monkeypatch.setattr("builtins.open", failing_open)
    result = scan(tmp_path)
    assert result.files[0].analysis_status == "unreadable"
    assert result.diagnostics[0].error_type == "UnreadableFile"


def test_unreadable_directory_continues(tmp_path, monkeypatch):
    (tmp_path / "bad").mkdir()
    (tmp_path / "good.py").write_text("pass")
    real_scandir = os.scandir
    def failing_scandir(path):
        if os.fspath(path).endswith("bad"):
            raise PermissionError("denied")
        return real_scandir(path)
    monkeypatch.setattr(os, "scandir", failing_scandir)
    result = scan(tmp_path)
    assert [f.path for f in result.files] == ["good.py"]
    assert result.diagnostics[0].error_type == "UnreadableDirectory"


def test_symlink_file_and_directory_are_skipped(tmp_path):
    target = tmp_path / "target.py"
    target.write_text("pass")
    folder = tmp_path / "folder"
    folder.mkdir()
    (folder / "inside.py").write_text("pass")
    try:
        (tmp_path / "link.py").symlink_to(target)
        (tmp_path / "linkdir").symlink_to(folder, target_is_directory=True)
    except OSError as exc:
        pytest.skip(f"symlink creation unavailable: {exc}")
    result = scan(tmp_path)
    assert [f.path for f in result.files] == ["folder/inside.py", "target.py"]
    assert {d.file for d in result.diagnostics if d.error_type == "SymlinkSkipped"} == {"link.py", "linkdir"}
