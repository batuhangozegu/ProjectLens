import json
import shutil
from pathlib import Path

import pytest

from projectlens.analysis.models import AnalysisOptions, AnalysisResult
from projectlens.analysis.pipeline import analyze
from projectlens.analysis.scanner import ScanError


FIXTURE = Path(__file__).parents[1] / "fixtures" / "sample_repo"
FRAMEWORK_FIXTURE = Path(__file__).parents[1] / "fixtures" / "frameworks_repo"


def test_fixture_pipeline_has_expected_records_graph_metrics_and_diagnostics():
    result = analyze(AnalysisOptions(str(FIXTURE)))
    assert [item.path for item in result.files] == [
        "README.md", "broken.py", "flat.py", "flat_consumer.py", "pyproject.toml",
        "src/isolated.py", "src/pkg/__init__.py", "src/pkg/left.py", "src/pkg/right.py",
        "tests/test_sample.py",
    ]
    assert [(edge.source, edge.target) for edge in result.dependency_edges] == [
        ("flat_consumer.py", "flat.py"),
        ("src/pkg/left.py", "src/pkg/right.py"),
        ("src/pkg/right.py", "src/pkg/left.py"),
    ]
    assert result.cycles == (("src/pkg/left.py", "src/pkg/right.py"),)
    assert result.external_imports == (
        {"source_file": "src/pkg/left.py", "line": 4, "module": "requests", "kind": "third_party"},
    )
    assert result.unresolved_imports == ()
    # `health`, `risk` and `findings` are pinned below.
    assert {key: value for key, value in result.metrics.items() if key not in {"health", "risk", "findings"}} == {
        "total_file_count": 10,
        "python_file_count": 8,
        "physical_loc": {"total": 25, "known_file_count": 10, "unavailable_file_count": 0, "unavailable_files": []},
        "python_loc": {"total": 21, "known_file_count": 8, "unavailable_file_count": 0, "unavailable_files": []},
        "largest_files": [
            {"path": "src/pkg/left.py", "physical_loc": 7},
            {"path": "src/pkg/right.py", "physical_loc": 4},
            {"path": "broken.py", "physical_loc": 3},
            {"path": "README.md", "physical_loc": 2},
            {"path": "pyproject.toml", "physical_loc": 2},
            {"path": "src/isolated.py", "physical_loc": 2},
            {"path": "tests/test_sample.py", "physical_loc": 2},
            {"path": "flat.py", "physical_loc": 1},
            {"path": "flat_consumer.py", "physical_loc": 1},
            {"path": "src/pkg/__init__.py", "physical_loc": 1},
        ],
        "comment_markers": {
            "total": 2,
            "by_kind": {"TODO": 1, "FIXME": 1},
            "by_file": {
                "broken.py": {"TODO": 0, "FIXME": 1, "total": 1, "available": False},
                "flat.py": {"TODO": 0, "FIXME": 0, "total": 0, "available": True},
                "flat_consumer.py": {"TODO": 0, "FIXME": 0, "total": 0, "available": True},
                "src/isolated.py": {"TODO": 0, "FIXME": 0, "total": 0, "available": True},
                "src/pkg/__init__.py": {"TODO": 0, "FIXME": 0, "total": 0, "available": True},
                "src/pkg/left.py": {"TODO": 1, "FIXME": 0, "total": 1, "available": True},
                "src/pkg/right.py": {"TODO": 0, "FIXME": 0, "total": 0, "available": True},
                "tests/test_sample.py": {"TODO": 0, "FIXME": 0, "total": 0, "available": True},
            },
            "unavailable_files": ["broken.py"],
        },
        "dependencies": {"edge_count": 3, "external_import_count": 1, "unresolved_import_count": 0, "cycle_group_count": 1},
        "framework_detection": {"basis": "manifest declarations; code usage not inspected"},
        "test_matching": {"sources_total": 6, "sources_with_matching_test": 0, "sources_without": 6, "by_rule": {"import": 0, "name": 0}, "basis": "name/import heuristics; not coverage"},
    }
    assert result.metrics["risk"]["formula_version"] == "1"
    assert result.metrics["risk"]["churn_available"] is False
    assert set(result.metrics["risk"]["counts_by_level"]) == {"high", "medium", "low", "minimal"}
    broken = next(item for item in result.files if item.path == "broken.py")
    assert broken.analysis_status == "parse_failed"
    assert [(d.stage, d.file, d.error_type) for d in result.diagnostics] == [("parse", "broken.py", "SyntaxError"), ("parse", "broken.py", "TokenizeError")]
    assert result.partial is True
    assert result.metrics["health"]["formula_version"] == "1"
    assert result.metrics["health"]["score"] == 25.0
    assert "__pycache__/" not in "\n".join(item.path for item in result.files)


def test_scanner_excluded_directory_is_absent_from_file_records(tmp_path):
    copy = tmp_path / "sample"
    shutil.copytree(FIXTURE, copy)
    (copy / "__pycache__").mkdir()
    (copy / "__pycache__" / "hidden.py").write_text("raise RuntimeError()\n", encoding="utf-8")
    result = analyze(AnalysisOptions(str(copy)))
    assert not any("__pycache__" in item.path for item in result.files)
    assert any(item.error_type == "Excluded" and item.file == "__pycache__" for item in result.diagnostics)


def test_missing_root_is_fatal():
    with pytest.raises(ScanError, match="does not exist"):
        analyze(AnalysisOptions(str(FIXTURE / "missing")))


def test_partial_analysis_continues_after_parse_failure_and_unreadable_read(tmp_path, monkeypatch):
    root = tmp_path / "repo"
    root.mkdir()
    (root / "good.py").write_text("VALUE = 1\n", encoding="utf-8")
    (root / "bad.py").write_text("def broken(:\n", encoding="utf-8")
    (root / "encoding.py").write_bytes(b"# coding: utf-8\nvalue = '\xff'\n")
    (root / "late.py").write_text("VALUE = 3\n", encoding="utf-8")
    original = Path.read_bytes

    def selective_read(path):
        if path.name == "late.py":
            raise PermissionError("read denied")
        return original(path)

    monkeypatch.setattr(Path, "read_bytes", selective_read)
    result = analyze(AnalysisOptions(str(root)))
    statuses = {item.path: item.analysis_status for item in result.files}
    assert statuses == {"bad.py": "parse_failed", "encoding.py": "parse_failed", "good.py": "analyzed", "late.py": "unreadable"}
    assert any(item.file == "late.py" and item.error_type == "UnreadableFile" for item in result.diagnostics)
    assert any(item.file == "encoding.py" and item.error_type == "EncodingError" for item in result.diagnostics)
    assert result.metrics["total_file_count"] == result.metrics["python_file_count"] == 4
    assert result.metrics["physical_loc"]["total"] == 5
    assert result.metrics["comment_markers"]["unavailable_files"] == ["bad.py", "encoding.py", "late.py"]
    assert result.partial is True


def test_serialization_and_repeated_runs_are_byte_identical_across_roots(tmp_path):
    first = analyze(AnalysisOptions(str(FIXTURE)))
    second = analyze(AnalysisOptions(str(FIXTURE)))
    copied_root = tmp_path / "elsewhere" / "sample_repo"
    shutil.copytree(FIXTURE, copied_root)
    third = analyze(AnalysisOptions(str(copied_root)))
    assert first.to_json() == second.to_json() == third.to_json()
    assert AnalysisResult.from_json(first.to_json()).to_dict() == first.to_dict()
    assert json.loads(first.to_json())["schema_version"] == "4"


def test_pipeline_detects_each_manifest_and_matches_name_and_resolved_import(tmp_path):
    fixture = tmp_path / "frameworks_repo"
    shutil.copytree(FRAMEWORK_FIXTURE, fixture)
    result = analyze(AnalysisOptions(str(fixture)))
    assert [(item.name, item.evidence_file) for item in result.frameworks] == [
        ("Flutter", "pubspec.yaml"), ("Flutter Riverpod", "pubspec.yaml"),
        ("FastAPI", "pyproject.toml"), ("pytest", "pyproject.toml"),
    ]
    by_source = {item.source: item.tests for item in result.test_matches}
    assert by_source["src/module.py"] == ({"path": "tests/test_module.py", "rule": "import"},)
    assert by_source["lib/src/widget.dart"] == ({"path": "test/src/widget_test.dart", "rule": "name"},)
    assert result.metrics["test_matching"]["sources_with_matching_test"] == 2
    assert result.metrics["health"]["formula_version"] == "1"
    assert result.metrics["health"]["score"] is not None


def test_empty_repository_health_is_unavailable(tmp_path):
    result = analyze(AnalysisOptions(str(tmp_path)))
    assert result.metrics["health"]["score"] is None
    assert result.metrics["health"]["confidence"] == "none"


def test_manifest_read_failure_is_diagnostic_and_partial(tmp_path, monkeypatch):
    manifest = tmp_path / "requirements.txt"
    manifest.write_text("fastapi\n", encoding="utf-8")
    original = Path.read_bytes

    def selective_read(path):
        if path.name == "requirements.txt":
            raise PermissionError("read denied")
        return original(path)

    monkeypatch.setattr(Path, "read_bytes", selective_read)
    result = analyze(AnalysisOptions(str(tmp_path)))
    assert result.partial
    assert result.frameworks == ()
    assert any(item.stage == "frameworks" and item.file == "requirements.txt" and item.error_type == "UnreadableManifest" for item in result.diagnostics)


def test_git_history_is_opt_in_and_unavailable_reason_is_informational(tmp_path):
    root = tmp_path / "plain"
    root.mkdir()
    (root / "module.py").write_text("VALUE = 1\n", encoding="utf-8")
    ordinary = analyze(AnalysisOptions(str(root)))
    requested = analyze(AnalysisOptions(str(root), git_history=True))
    assert "git_history" not in ordinary.metrics
    assert "risk" in ordinary.metrics
    assert requested.metrics["git_history"]["available"] is False
    assert requested.metrics["git_history"]["reason"] == "not_a_git_repository"
    assert not requested.partial
    assert not any(item.stage == "git_history" for item in requested.diagnostics)


def test_git_history_true_analyzes_committed_tree(tmp_path):
    import os
    import shutil
    import subprocess

    executable = shutil.which("git")
    if executable is None:
        pytest.skip("git executable is unavailable")
    root = tmp_path / "repo"
    root.mkdir()
    (root / "module.py").write_text("VALUE = 1\n", encoding="utf-8")
    subprocess.run([executable, "init", "-q", str(root)], check=True)
    env = os.environ.copy()
    env.update({"GIT_AUTHOR_NAME": "Test", "GIT_AUTHOR_EMAIL": "test@example.test", "GIT_COMMITTER_NAME": "Test", "GIT_COMMITTER_EMAIL": "test@example.test", "GIT_AUTHOR_DATE": "2024-01-01T00:00:00+00:00", "GIT_COMMITTER_DATE": "2024-01-01T00:00:00+00:00"})
    subprocess.run([executable, "-C", str(root), "add", "module.py"], check=True, env=env)
    subprocess.run([executable, "-C", str(root), "commit", "-qm", "init"], check=True, env=env)
    first = analyze(AnalysisOptions(str(root), git_history=True, history_days=60))
    second = analyze(AnalysisOptions(str(root), git_history=True, history_days=60))
    assert first.metrics["git_history"]["available"] is True
    assert first.metrics["git_history"]["commits_in_window"] == 1
    assert first.to_json() == second.to_json()


def test_git_history_unexpected_failure_is_diagnostic_and_partial(tmp_path, monkeypatch):
    import projectlens.analysis.pipeline as pipeline
    from projectlens.git.history import GitHistoryUnavailable

    root = tmp_path / "repo"
    root.mkdir()
    (root / "module.py").write_text("VALUE = 1\n", encoding="utf-8")

    def fail(*_args, **_kwargs):
        raise GitHistoryUnavailable("output_limit")

    monkeypatch.setattr(pipeline, "read_git_history", fail)
    result = analyze(AnalysisOptions(str(root), git_history=True))
    assert result.partial
    assert result.metrics["git_history"]["reason"] == "output_limit"
    assert any(item.stage == "git_history" and item.error_type == "GitHistoryUnavailable" and item.message == "output_limit" for item in result.diagnostics)


def test_analyze_includes_size_and_coupling_findings(tmp_path):
    root = tmp_path / "findings"
    root.mkdir()
    (root / "large.py").write_text("def huge():\n" + "    pass\n" * 99, encoding="utf-8")
    (root / "large_class.py").write_text("class Huge:\n" + "    value = 1\n" * 449, encoding="utf-8")
    (root / "hub.py").write_text("VALUE = 1\n", encoding="utf-8")
    for index in range(10):
        (root / f"client{index}.py").write_text("import hub\n", encoding="utf-8")
    for index in range(15):
        (root / f"target{index}.py").write_text("VALUE = 1\n", encoding="utf-8")
    (root / "fan.py").write_text("".join(f"import target{i}\n" for i in range(15)), encoding="utf-8")
    result = analyze(AnalysisOptions(str(root)))
    findings = result.metrics["findings"]["top_findings"]
    assert any(item["kind"] == "large_function" and item["symbol"] == "huge" and item["value"] == 100 for item in findings)
    assert any(item["kind"] == "large_class" and item["symbol"] == "Huge" and item["value"] == 450 for item in findings)
    assert any(item["kind"] == "high_fan_in" and item["path"] == "hub.py" and item["value"] == 10 for item in findings)
    assert any(item["kind"] == "high_fan_out" and item["path"] == "fan.py" and item["value"] == 15 for item in findings)
