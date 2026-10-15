import os

import pytest

from projectlens.git.checkout import _build_git_env, _validate_ref, checkout_repository


def test_env_is_allowlisted_and_noninteractive(tmp_path, monkeypatch):
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", "secret-config")
    monkeypatch.setenv("GIT_CREDENTIAL", "secret")
    monkeypatch.setenv("SSH_AUTH_SOCK", "secret-socket")
    env = _build_git_env(tmp_path / "home")
    assert env["GIT_TERMINAL_PROMPT"] == "0"
    assert env["GIT_CONFIG_NOSYSTEM"] == "1"
    assert env["GIT_CONFIG_GLOBAL"] == os.devnull
    assert env["HOME"] == str(tmp_path / "home")
    assert env["XDG_CONFIG_HOME"] == str(tmp_path / "home" / "xdg")
    assert env["GIT_ASKPASS"]
    assert "GIT_CREDENTIAL" not in env
    assert "SSH_AUTH_SOCK" not in env


@pytest.mark.parametrize("ref", ["--upload-pack=evil", "-x", "a..b", "a b", "main\nother", "x@{y}"])
def test_branch_validation_blocks_option_injection(ref):
    with pytest.raises(ValueError):
        _validate_ref(ref)


def test_rejects_bad_commit_and_conflicting_selectors():
    with pytest.raises(ValueError):
        checkout_repository("https://github.com/owner/repo", commit="not-a-sha")
    with pytest.raises(ValueError):
        checkout_repository("https://github.com/owner/repo", ref="main", commit="a" * 40)
