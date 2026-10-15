"""Hardened Git subprocess and isolated checkout lifecycle."""

from __future__ import annotations

import os
import re
import shutil
import stat
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Mapping, Sequence

from .url import validate_repository_url


class CheckoutError(RuntimeError):
    """A repository could not be checked out safely."""


class CheckoutTimeout(CheckoutError):
    """A Git command exceeded its configured time limit."""


@dataclass
class CheckoutResult:
    """An isolated checkout. Call :meth:`cleanup` when analysis is complete."""

    path: Path
    resolved_commit: str
    branch: str | None
    canonical_url: str

    def cleanup(self) -> None:
        _remove_tree(self.path, ignore_errors=True)

    def __enter__(self) -> "CheckoutResult":
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        self.cleanup()


def _remove_tree(path: Path, *, ignore_errors: bool = False) -> None:
    """Remove a tree, clearing read-only bits (Git object files are read-only on Windows)."""

    def _clear_and_retry(func: Callable[..., object], target: str, *_exc: object) -> None:
        try:
            os.chmod(target, stat.S_IWRITE)
            func(target)
        except OSError:
            if not ignore_errors:
                raise

    if sys.version_info >= (3, 12):
        shutil.rmtree(path, onexc=_clear_and_retry)
    else:
        shutil.rmtree(path, onerror=_clear_and_retry)


_Runner = Callable[[Sequence[str], Mapping[str, str], float, int], None]
_COMMIT = re.compile(r"[0-9a-fA-F]{40}\Z", re.ASCII)
_FULL_COMMIT = re.compile(r"[0-9a-f]{40}\Z", re.ASCII)
_OUTPUT_LIMIT = 1024 * 1024


def _build_git_env(home_dir: Path) -> dict[str, str]:
    """Build an allowlisted environment; no caller credential/config vars pass through."""
    home_dir.mkdir(parents=True, exist_ok=True)
    env = {
        "PATH": os.environ.get("PATH", os.defpath),
        "HOME": str(home_dir),
        "XDG_CONFIG_HOME": str(home_dir / "xdg"),
        "GIT_TERMINAL_PROMPT": "0",
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_CONFIG_GLOBAL": os.devnull,
        "GIT_LFS_SKIP_SMUDGE": "1",
        "LC_ALL": "C",
    }
    # Git requires an executable askpass program; this one returns an empty value
    # and cannot obtain credentials from an interactive user.
    if os.name == "nt":
        askpass = home_dir / "askpass.cmd"
        askpass.write_text("@echo off\r\nexit /b 1\r\n", encoding="ascii")
        env["GIT_ASKPASS"] = str(askpass)
        for key in ("SystemRoot", "WINDIR", "ComSpec"):
            if key in os.environ:
                env[key] = os.environ[key]
    else:
        askpass = home_dir / "askpass"
        askpass.write_text("#!/bin/sh\nexit 1\n", encoding="ascii")
        askpass.chmod(0o700)
        env["GIT_ASKPASS"] = str(askpass)
    return env


def _execute_git(args: Sequence[str], env: Mapping[str, str], timeout: float, max_output_bytes: int) -> None:
    """Run Git without a shell and spool output to bounded temporary files."""
    with tempfile.TemporaryFile() as stdout_file, tempfile.TemporaryFile() as stderr_file:
        try:
            process = subprocess.Popen(
                list(args), shell=False, stdin=subprocess.DEVNULL,
                stdout=stdout_file, stderr=stderr_file, env=dict(env),
            )
            returncode = process.wait(timeout=timeout)
        except subprocess.TimeoutExpired as exc:
            process.kill()
            process.wait()
            raise CheckoutTimeout(f"Git command timed out after {timeout:g} seconds") from exc
        stdout_file.seek(0, os.SEEK_END)
        stdout_size = stdout_file.tell()
        stderr_file.seek(0, os.SEEK_END)
        stderr_size = stderr_file.tell()
        if stdout_size + stderr_size > max_output_bytes:
            raise CheckoutError("Git command output exceeded the configured limit")
        stderr_file.seek(0)
        detail = stderr_file.read(min(stderr_size, 4096)).decode("utf-8", "replace").strip()
        if returncode:
            raise CheckoutError(detail or f"Git command failed with exit status {returncode}")


def _capture_git(args: Sequence[str], env: Mapping[str, str], timeout: float, max_output_bytes: int) -> bytes:
    """Capture a small Git result while enforcing the same output and time bounds."""
    with tempfile.TemporaryFile() as output_file, tempfile.TemporaryFile() as error_file:
        process = subprocess.Popen(
            list(args), shell=False, stdin=subprocess.DEVNULL,
            stdout=output_file, stderr=error_file, env=dict(env),
        )
        try:
            returncode = process.wait(timeout=timeout)
        except subprocess.TimeoutExpired as exc:
            process.kill()
            process.wait()
            raise CheckoutTimeout(f"Git command timed out after {timeout:g} seconds") from exc
        output_file.seek(0, os.SEEK_END)
        output_size = output_file.tell()
        error_file.seek(0, os.SEEK_END)
        error_size = error_file.tell()
        if output_size + error_size > max_output_bytes:
            raise CheckoutError("Git command output exceeded the configured limit")
        if returncode:
            error_file.seek(0)
            detail = error_file.read(min(error_size, 4096)).decode("utf-8", "replace").strip()
            raise CheckoutError(detail or f"Git command failed with exit status {returncode}")
        output_file.seek(0)
        return output_file.read(max_output_bytes + 1)


def _validate_ref(ref: str) -> None:
    if not isinstance(ref, str) or not ref or ref.startswith("-") or ".." in ref:
        raise ValueError("ref must be a valid branch name")
    if not ref.isascii() or any(ord(c) < 0x21 or ord(c) == 0x7F for c in ref):
        raise ValueError("ref cannot contain spaces, controls, or non-ASCII characters")
    if any(c in ref for c in "~^:?*[\\") or "@{" in ref:
        raise ValueError("ref contains characters forbidden in Git branch names")
    if ref.startswith("/") or ref.endswith(("/", ".")) or "//" in ref or ref == "@":
        raise ValueError("ref is not a valid Git branch name")
    if any(part.startswith(".") or part.endswith((".", ".lock")) for part in ref.split("/")):
        raise ValueError("ref is not a valid Git branch name")


def _git_args(*args: str, file_override: bool = False) -> list[str]:
    null = os.devnull
    options = [
        "-c", f"core.hooksPath={null}",
        "-c", "core.fsmonitor=false",
        "-c", "core.symlinks=false",
        "-c", "protocol.allow=never",
        "-c", "protocol.https.allow=always",
        "-c", f"protocol.file.allow={'always' if file_override else 'never'}",
        "-c", "submodule.recurse=false",
        "-c", "credential.helper=",
        "-c", "filter.lfs.smudge=",
        "-c", "filter.lfs.clean=",
        "-c", "filter.lfs.process=",
        "-c", "filter.lfs.required=false",
    ]
    return ["git", *options, *args]


def checkout_repository(
    url: str,
    ref: str | None = None,
    commit: str | None = None,
    *,
    base_dir: str | Path | None = None,
    timeout: float = 120.0,
    max_bytes: int = 512 * 1024 * 1024,
    _clone_url_override: str | None = None,
    _runner: _Runner | None = None,
) -> CheckoutResult:
    """Create a depth-one checkout of a public GitHub repository.

    ``_clone_url_override`` and ``_runner`` are private testing seams. Public
    callers must use the validated HTTPS URL and real Git subprocess.
    """
    canonical, _owner, _repo = validate_repository_url(url)
    if ref is not None and commit is not None:
        raise ValueError("ref and commit are mutually exclusive")
    if ref is not None:
        _validate_ref(ref)
    if commit is not None and (not isinstance(commit, str) or not _COMMIT.fullmatch(commit)):
        raise ValueError("commit must be a full 40-character hexadecimal SHA")
    if timeout <= 0 or max_bytes < 0:
        raise ValueError("timeout must be positive and max_bytes must be non-negative")
    clone_url = _clone_url_override if _clone_url_override is not None else canonical
    file_override = _clone_url_override is not None
    runner = _runner or _execute_git
    base = Path(base_dir) if base_dir is not None else Path(tempfile.gettempdir()) / "projectlens-checkouts"
    base.mkdir(parents=True, exist_ok=True)
    checkout_path = Path(tempfile.mkdtemp(prefix="projectlens-", dir=base))
    try:
        try:
            checkout_path.chmod(0o700)
        except OSError:
            pass
        with tempfile.TemporaryDirectory(prefix="projectlens-env-") as env_path:
            env = _build_git_env(Path(env_path))
            common = dict(file_override=file_override)
            if commit is None:
                args = _git_args("clone", "--depth", "1", "--no-tags", "--single-branch", *(["--branch", ref] if ref else []), "--", clone_url, str(checkout_path), **common)
                runner(args, env, timeout, _OUTPUT_LIMIT)
            else:
                runner(_git_args("init", "--quiet", str(checkout_path), **common), env, timeout, _OUTPUT_LIMIT)
                runner(_git_args("-C", str(checkout_path), "remote", "add", "origin", clone_url, **common), env, timeout, _OUTPUT_LIMIT)
                runner(_git_args("-C", str(checkout_path), "fetch", "--depth=1", "--no-tags", "origin", commit, **common), env, timeout, _OUTPUT_LIMIT)
                runner(_git_args("-C", str(checkout_path), "checkout", "--quiet", "--detach", "FETCH_HEAD", **common), env, timeout, _OUTPUT_LIMIT)
            sha_output = _capture_git(
                _git_args("-C", str(checkout_path), "rev-parse", "--verify", "HEAD", **common),
                env, timeout, _OUTPUT_LIMIT,
            ).decode("ascii", "strict").strip()
            if not _FULL_COMMIT.fullmatch(sha_output):
                raise CheckoutError("Git returned an invalid resolved commit")
            if commit is not None and not sha_output.startswith(commit.lower()):
                raise CheckoutError("checked out commit does not match the requested commit")
            if ref is not None:
                branch = ref
            elif commit is None:
                branch_result = _capture_git(
                    _git_args("-C", str(checkout_path), "branch", "--show-current", **common),
                    env, timeout, _OUTPUT_LIMIT,
                ).decode("utf-8", "replace").strip()
                branch = branch_result or None
            else:
                branch = None
        actual_size = sum(item.stat(follow_symlinks=False).st_size for item in checkout_path.rglob("*") if not item.is_symlink() and item.is_file())
        if actual_size > max_bytes:
            raise CheckoutError(f"checkout exceeded the {max_bytes}-byte size limit")
        # The analysis tree contains no Git metadata, hooks, config, or object store.
        _remove_tree(checkout_path / ".git")
        return CheckoutResult(checkout_path, sha_output, branch, canonical)
    except subprocess.TimeoutExpired as exc:
        _remove_tree(checkout_path, ignore_errors=True)
        raise CheckoutTimeout(f"Git command timed out after {timeout:g} seconds") from exc
    except BaseException:
        _remove_tree(checkout_path, ignore_errors=True)
        raise
