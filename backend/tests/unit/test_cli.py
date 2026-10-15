from projectlens.cli import main


def test_help_exits_successfully(capsys) -> None:
    try:
        main(["--help"])
    except SystemExit as error:
        assert error.code == 0
    else:
        raise AssertionError("--help should exit")
    assert "analyze" in capsys.readouterr().out


def test_analyze_prints_summary_and_exports_json(tmp_path, capsys) -> None:
    root = tmp_path / "repo"
    root.mkdir()
    (root / "main.py").write_text("# TODO: later\nvalue = 1\n", encoding="utf-8")
    output = tmp_path / "result.json"
    assert main(["analyze", str(root), "--output", str(output)]) == 0
    captured = capsys.readouterr()
    assert "Root:" in captured.out
    assert "Files: 1 (Python: 1)" in captured.out
    assert "Physical LOC: 2" in captured.out
    assert "TODO/FIXME: 1 (TODO: 1, FIXME: 0)" in captured.out
    assert '"projectlens_format":"projectlens-analysis"' in output.read_text(encoding="utf-8")
    assert captured.err == ""


def test_usage_type_error_remains_argparse_exit_two(capsys) -> None:
    try:
        main(["analyze", ".", "--top", "-1"])
    except SystemExit as error:
        assert error.code == 2
    else:
        raise AssertionError("invalid argument should exit")
    assert "error:" in capsys.readouterr().err
