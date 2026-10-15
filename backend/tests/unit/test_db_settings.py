import pytest

from projectlens.app.db import settings as settings_module
from projectlens.app.db.settings import get_settings, parse_dotenv


def test_parse_dotenv_ignores_comments_and_strips_quotes():
    text = "# comment\n\nA=1\nB = 'two words'\nC=\"x\"\nnot a pair\n"
    assert parse_dotenv(text) == {"A": "1", "B": "two words", "C": "x"}


def test_explicit_mapping_is_used_as_is(monkeypatch, tmp_path):
    (tmp_path / ".env").write_text("DATABASE_URL=sqlite:///from_file\n")
    monkeypatch.chdir(tmp_path)
    with pytest.raises(RuntimeError, match="DATABASE_URL is required"):
        get_settings({})
    assert get_settings({"DATABASE_URL": "sqlite:///x"}).database_url == "sqlite:///x"


def test_dotenv_fallback_and_environment_precedence(monkeypatch, tmp_path):
    (tmp_path / ".env").write_text("DATABASE_URL=sqlite:///from_file\n")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(settings_module, "_dotenv_candidates", lambda: [tmp_path / ".env"])
    monkeypatch.delenv("DATABASE_URL", raising=False)
    assert get_settings().database_url == "sqlite:///from_file"
    monkeypatch.setenv("DATABASE_URL", "sqlite:///from_env")
    assert get_settings().database_url == "sqlite:///from_env"
