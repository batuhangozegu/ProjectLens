import os
import shutil
import subprocess
from pathlib import Path

import pytest

from projectlens.git.history import GitHistoryUnavailable, read_git_history


GIT = shutil.which("git")
pytestmark = pytest.mark.skipif(GIT is None, reason="git executable is unavailable")
BASE = "2024-01-01T00:00:00+00:00"


def git(repo, *args, env=None):
    environment = os.environ.copy()
    environment.update({"GIT_AUTHOR_NAME": "ProjectLens Test", "GIT_AUTHOR_EMAIL": "private@example.test", "GIT_COMMITTER_NAME": "ProjectLens Test", "GIT_COMMITTER_EMAIL": "private@example.test"})
    if env:
        environment.update(env)
    return subprocess.run([GIT, "-C", str(repo), *args], check=True, capture_output=True, env=environment)


def init(repo):
    repo.mkdir(parents=True, exist_ok=True)
    git(repo, "init", "-q")


def commit(repo, paths, date, *, author_email="private@example.test"):
    for relative, content in paths.items():
        target = repo / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        if content is None:
            target.unlink(missing_ok=True)
        else:
            target.write_text(content, encoding="utf-8")
    git(repo, "add", "-A")
    git(repo, "commit", "-qm", "fixture", env={"GIT_AUTHOR_DATE": date, "GIT_COMMITTER_DATE": date, "GIT_AUTHOR_EMAIL": author_email, "GIT_COMMITTER_EMAIL": author_email})


def test_fixed_head_window_names_authors_deletions_and_repeat(tmp_path):
    repo = tmp_path / "repo"
    init(repo)
    commit(repo, {"src/space name.py": "one\n", "src/café.dart": "one\n", "deleted.py": "gone\n"}, "2024-01-01T00:00:00+00:00")
    commit(repo, {"src/space name.py": "two\n", "src/café.dart": "two\n"}, "2024-01-10T00:00:00+00:00", author_email="another@example.test")
    git(repo, "rm", "deleted.py")
    git(repo, "commit", "-qm", "delete", env={"GIT_AUTHOR_DATE": "2024-01-15T00:00:00+00:00", "GIT_COMMITTER_DATE": "2024-01-15T00:00:00+00:00"})
    commit(repo, {"src/space name.py": "three\n"}, "2024-01-31T00:00:00+00:00")
    files = ["src/space name.py", "src/café.dart"]
    first = read_git_history(repo, files, 21)
    second = read_git_history(repo, files, 21)
    assert first == second
    assert first["commits_in_window"] == 3  # boundary is Jan 10, relative to Jan 31 HEAD
    assert first["files_with_churn"] == 2
    assert {item["path"] for item in first["top_churn"]} == set(files)
    by_path = {item["path"]: item for item in first["top_churn"]}
    assert by_path["src/space name.py"]["authors"] == 2 and by_path["src/space name.py"]["commits"] == 2
    assert by_path["src/café.dart"]["authors"] == 1 and by_path["src/café.dart"]["commits"] == 1
    assert "private@example.test" not in repr(first)
    assert "another@example.test" not in repr(first)
    assert first["head_commit_date"] == "2024-01-31"


def test_subdirectory_scope_and_deleted_file_not_counted(tmp_path):
    repo = tmp_path / "repo"
    init(repo)
    commit(repo, {"other/outside.py": "x\n", "package/src.py": "x\n"}, BASE)
    commit(repo, {"other/outside.py": "y\n", "package/src.py": "y\n"}, "2024-01-02T00:00:00+00:00")
    result = read_git_history(repo / "package", ["src.py", "removed.py"], 180)
    assert [item["path"] for item in result["top_churn"]] == ["src.py"]
    assert result["top_churn"][0]["commits"] == 2


def test_merge_commits_are_excluded(tmp_path):
    repo = tmp_path / "repo"
    init(repo)
    commit(repo, {"base.py": "base\n"}, BASE)
    git(repo, "checkout", "-qb", "feature")
    commit(repo, {"feature.py": "feature\n"}, "2024-01-02T00:00:00+00:00")
    git(repo, "checkout", "-q", "-")
    commit(repo, {"main.py": "main\n"}, "2024-01-03T00:00:00+00:00")
    git(repo, "merge", "--no-ff", "-qm", "merge", "feature", env={"GIT_AUTHOR_DATE": "2024-01-04T00:00:00+00:00", "GIT_COMMITTER_DATE": "2024-01-04T00:00:00+00:00"})
    result = read_git_history(repo, ["base.py", "feature.py", "main.py"], 180)
    assert result["commits_in_window"] == 3


def test_not_repository_empty_and_shallow_reasons(tmp_path):
    with pytest.raises(GitHistoryUnavailable) as error:
        read_git_history(tmp_path, [], 180)
    assert error.value.reason == "not_a_git_repository"
    empty = tmp_path / "empty"
    init(empty)
    with pytest.raises(GitHistoryUnavailable) as error:
        read_git_history(empty, [], 180)
    assert error.value.reason == "no_commits"
    source = tmp_path / "source"
    init(source)
    commit(source, {"a.py": "x\n"}, BASE)
    shallow = tmp_path / "shallow"
    subprocess.run([GIT, "clone", "--depth", "1", "file://" + source.as_posix(), str(shallow)], check=True, capture_output=True)
    with pytest.raises(GitHistoryUnavailable) as error:
        read_git_history(shallow, ["a.py"], 180)
    assert error.value.reason == "shallow_history"


def test_commit_limit_truncates(monkeypatch, tmp_path):
    from projectlens.git import history
    repo = tmp_path / "repo"
    init(repo)
    commit(repo, {"a.py": "one\n"}, BASE)
    commit(repo, {"a.py": "two\n"}, "2024-01-02T00:00:00+00:00")
    monkeypatch.setattr(history, "MAX_HISTORY_COMMITS", 1)
    result = read_git_history(repo, ["a.py"], 180)
    assert result["available"] is True
    assert result["truncated"] is True
    assert result["commits_in_window"] == 1


def test_output_limit_has_machine_readable_reason(monkeypatch, tmp_path):
    from projectlens.git import history
    repo = tmp_path / "repo"
    init(repo)
    commit(repo, {"a.py": "one\n"}, BASE)
    monkeypatch.setattr(history, "HISTORY_OUTPUT_LIMIT", 1)
    with pytest.raises(GitHistoryUnavailable) as error:
        read_git_history(repo, ["a.py"], 180)
    assert error.value.reason == "output_limit"
