import subprocess
from pathlib import Path

import pytest

from projectlens.git.checkout import CheckoutError, CheckoutTimeout, checkout_repository


pytestmark = pytest.mark.skipif(subprocess.call(["git", "--version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL) != 0, reason="git executable unavailable")


def git(*args, cwd):
    return subprocess.check_output(["git", *args], cwd=cwd, stderr=subprocess.PIPE).decode().strip()


def make_repo(root: Path) -> tuple[Path, str, str]:
    root.mkdir()
    git("init", "-q", "-b", "main", cwd=root)
    git("config", "user.name", "ProjectLens Test", cwd=root)
    git("config", "user.email", "test@example.invalid", cwd=root)
    (root / "hello.txt").write_text("first revision\n")
    git("add", "hello.txt", cwd=root)
    git("commit", "-q", "-m", "first", cwd=root)
    first = git("rev-parse", "HEAD", cwd=root)
    git("checkout", "-q", "-b", "feature/test", cwd=root)
    (root / "hello.txt").write_text("feature revision\n")
    git("commit", "-qam", "feature", cwd=root)
    feature = git("rev-parse", "HEAD", cwd=root)
    return root, first, feature


URL = "https://github.com/example/project"


def local_checkout(source: Path, target_base: Path, **kwargs):
    return checkout_repository(URL, base_dir=target_base, _clone_url_override=str(source), **kwargs)


def test_branch_checkout_has_expected_tree_and_no_git(tmp_path):
    source, _first, feature = make_repo(tmp_path / "source")
    with local_checkout(source, tmp_path / "out", ref="feature/test") as result:
        assert result.resolved_commit == feature
        assert result.branch == "feature/test"
        assert result.canonical_url == URL
        assert (result.path / "hello.txt").read_text() == "feature revision\n"
        assert not (result.path / ".git").exists()


def test_exact_commit_checkout(tmp_path):
    source, first, _feature = make_repo(tmp_path / "source")
    with local_checkout(source, tmp_path / "out", commit=first) as result:
        assert result.resolved_commit == first
        assert result.branch is None
        assert (result.path / "hello.txt").read_text() == "first revision\n"


def test_wrong_commit_cleans_partial_checkout(tmp_path):
    source, _first, _feature = make_repo(tmp_path / "source")
    base = tmp_path / "out"
    with pytest.raises(CheckoutError):
        local_checkout(source, base, commit="f" * 40)
    assert list(base.iterdir()) == []


def test_timeout_cleans_checkout(tmp_path):
    base = tmp_path / "out"

    def slow_runner(args, env, timeout, output_limit):
        raise CheckoutTimeout("fake timeout")

    with pytest.raises(CheckoutTimeout):
        checkout_repository(URL, base_dir=base, _clone_url_override=str(tmp_path), _runner=slow_runner)
    assert list(base.iterdir()) == []


def test_size_limit_cleans_checkout(tmp_path):
    source, _first, _feature = make_repo(tmp_path / "source")
    base = tmp_path / "out"
    with pytest.raises(CheckoutError, match="size limit"):
        local_checkout(source, base, ref="main", max_bytes=2)
    assert list(base.iterdir()) == []


def test_source_checkout_hook_is_not_executed(tmp_path):
    source, _first, _feature = make_repo(tmp_path / "source")
    hooks = source / ".git" / "hooks"
    marker = tmp_path / "hook-ran"
    hook = hooks / "post-checkout"
    hook.write_text(f"#!/bin/sh\nprintf ran > '{marker}'\n")
    hook.chmod(0o700)
    with local_checkout(source, tmp_path / "out", ref="main"):
        pass
    assert not marker.exists()


def test_submodule_is_not_fetched(tmp_path):
    module, _first, _feature = make_repo(tmp_path / "module")
    source, _first, _feature = make_repo(tmp_path / "source")
    git("checkout", "-q", "main", cwd=source)
    git("-c", "protocol.file.allow=always", "submodule", "add", "-q", str(module), "vendor/module", cwd=source)
    git("commit", "-qam", "add submodule", cwd=source)
    with local_checkout(source, tmp_path / "out", ref="main") as result:
        module_path = result.path / "vendor" / "module"
        assert not module_path.exists() or not list(module_path.iterdir())


def test_symlink_is_not_materialized_as_a_filesystem_link(tmp_path):
    source, _first, _feature = make_repo(tmp_path / "source")
    git("checkout", "-q", "main", cwd=source)
    (source / "target.txt").write_text("target\n")
    try:
        (source / "link.txt").symlink_to("target.txt")
    except (OSError, NotImplementedError):
        pytest.skip("symlink creation unavailable")
    git("add", "target.txt", "link.txt", cwd=source)
    git("commit", "-q", "-m", "symlink", cwd=source)
    with local_checkout(source, tmp_path / "out", ref="main") as result:
        assert not (result.path / "link.txt").is_symlink()


def test_cleanup_removes_checkout(tmp_path):
    source, _first, _feature = make_repo(tmp_path / "source")
    result = local_checkout(source, tmp_path / "out", ref="main")
    checkout = result.path
    assert checkout.exists()
    result.cleanup()
    assert not checkout.exists()
