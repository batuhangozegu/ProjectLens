from projectlens.cli import main


def test_help_exits_successfully(capsys) -> None:
    try:
        main(["--help"])
    except SystemExit as error:
        assert error.code == 0
    else:
        raise AssertionError("--help should exit")
    assert "analyze" in capsys.readouterr().out


def test_analyze_reports_not_implemented(capsys) -> None:
    assert main(["analyze", ".", "--output", "result.json"]) == 1
    captured = capsys.readouterr()
    assert "not implemented yet" in captured.err
    assert captured.out == ""
