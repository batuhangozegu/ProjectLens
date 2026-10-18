import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from projectlens.cli import main


FIXTURE = Path(__file__).parents[1] / "fixtures" / "sample_repo"
FRAMEWORK_FIXTURE = Path(__file__).parents[1] / "fixtures" / "frameworks_repo"


def copy_fixture(tmp_path: Path, name: str = "repo") -> Path:
    destination = tmp_path / name
    shutil.copytree(FIXTURE, destination)
    return destination


def test_fixture_summary_reports_metrics_cycles_and_partial_result(tmp_path, capsys):
    root = copy_fixture(tmp_path)
    assert main(["analyze", str(root), "--max-diagnostics", "1"]) == 3
    output = capsys.readouterr().out
    assert "*** PARTIAL RESULT" in output
    assert "Files: 10 (Python: 8)" in output
    assert "Physical LOC: 25" in output
    assert "Python LOC: 21" in output
    assert "TODO/FIXME: 2 (TODO: 1, FIXME: 1)" in output
    assert "3 local edges, 1 external, 0 unresolved" in output
    assert "Frameworks declared: 0" in output
    assert "Test matches: 0 of 6 source files have a matching test file (name/import heuristic, not coverage)" in output
    assert "Health: 25.0 (poor, confidence: medium)" in output
    assert "Health component unavailable (todo_density)" in output
    assert "src/pkg/left.py, src/pkg/right.py" in output
    assert "Diagnostics: 2" in output
    assert "more diagnostic(s) not shown" in output


def test_cli_reports_framework_evidence_and_test_matches(tmp_path, capsys):
    root = tmp_path / "frameworks_repo"
    shutil.copytree(FRAMEWORK_FIXTURE, root)
    assert main(["analyze", str(root)]) == 0
    output = capsys.readouterr().out
    assert "Frameworks declared: 4" in output
    assert "Flutter (dart) — pubspec.yaml" in output
    assert "FastAPI (python) — pyproject.toml" in output
    assert "Test matches: 2 of 3 source files have a matching test file (name/import heuristic, not coverage)" in output


@pytest.mark.parametrize("kind", ["missing", "file", "output_parent", "output_directory"])
def test_fatal_errors_return_one_without_traceback(tmp_path, capsys, kind):
    root = copy_fixture(tmp_path)
    if kind == "missing":
        root = tmp_path / "absent"
        argv = ["analyze", str(root)]
    elif kind == "file":
        file_path = tmp_path / "not_dir"
        file_path.write_text("x", encoding="utf-8")
        argv = ["analyze", str(file_path)]
    elif kind == "output_parent":
        argv = ["analyze", str(root), "--output", str(tmp_path / "absent" / "result.json")]
    else:
        output_dir = tmp_path / "output-dir"
        output_dir.mkdir()
        argv = ["analyze", str(root), "--output", str(output_dir)]
    assert main(argv) == 1
    captured = capsys.readouterr()
    assert "error:" in captured.err
    assert "Traceback" not in captured.err


def test_fatal_analysis_does_not_create_requested_output(tmp_path, capsys):
    output = tmp_path / "must-not-exist.json"
    assert main(["analyze", str(tmp_path / "missing"), "--output", str(output)]) == 1
    assert not output.exists()
    assert "Traceback" not in capsys.readouterr().err


def test_partial_analysis_writes_json_and_returns_three(tmp_path, capsys):
    root = tmp_path / "partial"
    root.mkdir()
    (root / "bad.py").write_text("def broken(:\n", encoding="utf-8")
    output = tmp_path / "partial.json"
    assert main(["analyze", str(root), "--output", str(output)]) == 3
    assert json.loads(output.read_text(encoding="utf-8"))["partial"] is True
    assert "PARTIAL RESULT" in capsys.readouterr().out


def test_json_is_byte_identical_across_copied_roots(tmp_path):
    first_root = copy_fixture(tmp_path, "one")
    second_root = copy_fixture(tmp_path, "two")
    first_output, second_output = tmp_path / "one.json", tmp_path / "two.json"
    assert main(["analyze", str(first_root), "--output", str(first_output)]) == 3
    assert main(["analyze", str(second_root), "--output", str(second_output)]) == 3
    assert first_output.read_bytes() == second_output.read_bytes()
    assert str(first_root).encode() not in first_output.read_bytes()
    assert str(second_root).encode() not in second_output.read_bytes()


def test_output_inside_root_is_never_an_input_and_repeat_is_identical(tmp_path, capsys):
    root = copy_fixture(tmp_path)
    output = root / "analysis.json"
    assert main(["analyze", str(root), "--output", str(output)]) == 3
    first = output.read_bytes()
    assert main(["analyze", str(root), "--output", str(output)]) == 3
    second = output.read_bytes()
    result = json.loads(second)
    assert first == second
    assert "analysis.json" not in [item["path"] for item in result["files"]]
    assert any(item["file"] == "analysis.json" and item["error_type"] == "Excluded" for item in result["diagnostics"])


def test_existing_projectlens_result_json_is_excluded(tmp_path):
    root = tmp_path / "repo"
    root.mkdir()
    (root / "app.py").write_text("VALUE = 1\n", encoding="utf-8")
    prior = root / "old-report.json"
    prior.write_text('{"projectlens_format":"projectlens-analysis"}', encoding="utf-8")
    output = tmp_path / "result.json"
    assert main(["analyze", str(root), "--output", str(output)]) == 0
    result = json.loads(output.read_text(encoding="utf-8"))
    assert "old-report.json" not in [item["path"] for item in result["files"]]
    assert any(item["file"] == "old-report.json" and item["error_type"] == "Excluded" for item in result["diagnostics"])


def test_non_ascii_root_does_not_crash_console(tmp_path, capsys):
    root = tmp_path / "café-ğüş"
    root.mkdir()
    (root / "main.py").write_text("pass\n", encoding="utf-8")
    assert main(["analyze", str(root)]) == 0
    assert "Root:" in capsys.readouterr().out


def test_cli_git_history_flags_and_risk_summary(tmp_path, capsys):
    root = tmp_path / "plain"
    root.mkdir()
    (root / "module.py").write_text("VALUE = 1\n", encoding="utf-8")
    assert main(["analyze", str(root), "--git-history", "--history-days", "30"]) == 0
    output = capsys.readouterr().out
    assert "Git history: unavailable (not_a_git_repository)" in output
    assert "Risk: 0 high, 0 medium, 1 low" in output


def test_invalid_history_days_is_argparse_exit_two(tmp_path, capsys):
    with pytest.raises(SystemExit) as error:
        main(["analyze", str(tmp_path), "--history-days", "0"])
    assert error.value.code == 2
    assert "1 to 3650" in capsys.readouterr().err


def test_python_module_subprocess(tmp_path):
    root = copy_fixture(tmp_path)
    env = os.environ.copy()
    source_root = str(Path(__file__).parents[2] / "src")
    env["PYTHONPATH"] = source_root + os.pathsep + env.get("PYTHONPATH", "")
    process = subprocess.run(
        [sys.executable, "-m", "projectlens", "analyze", str(root)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=env,
        check=False,
    )
    assert process.returncode == 3
    assert "ProjectLens analysis" in process.stdout
    assert "PARTIAL RESULT" in process.stdout
    assert process.stderr == ""
