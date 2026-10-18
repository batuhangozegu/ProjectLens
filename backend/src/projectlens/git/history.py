"""Bounded, deterministic Git history facts for local analysis."""

from __future__ import annotations

import hashlib
import re
import tempfile
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence

from .checkout import CheckoutError, CheckoutTimeout, _OUTPUT_LIMIT, _build_git_env, _capture_git, _git_args

MAX_HISTORY_COMMITS = 20_000
HISTORY_OUTPUT_LIMIT = 8 * 1024 * 1024
GIT_TIMEOUT_SECONDS = 10.0
_SHA = re.compile(rb"[0-9a-f]{40}\Z")


def _header_index(tokens: list[bytes], index: int) -> int | None:
    """Recognize a record from its SHA/timestamp/author triple."""
    if index >= len(tokens):
        return None
    token = tokens[index]
    if token.startswith(b"\r\n"):
        index += 1
        token = token[2:]
    elif token.startswith(b"\n"):
        index += 1
        token = token[1:]
    if not _SHA.fullmatch(token) or index + 2 >= len(tokens):
        return None
    try:
        int(tokens[index + 1])
    except ValueError:
        return None
    return index


class GitHistoryUnavailable(Exception):
    """History could not be read; ``reason`` is safe for metrics/diagnostics."""

    def __init__(self, reason: str):
        self.reason = reason
        super().__init__(reason)


def read_git_history(root: Path, files: Sequence[str], window_days: int) -> dict[str, Any]:
    """Read bounded file churn. Raw author emails are hashed and never returned."""
    if type(window_days) is not int or not 1 <= window_days <= 3650:
        raise ValueError("window_days must be between 1 and 3650")
    try:
        with tempfile.TemporaryDirectory(prefix="projectlens-git-history-") as env_dir:
            env = _build_git_env(Path(env_dir))
            root_text = str(root.resolve())
            try:
                top = _capture_git(_git_args("-C", root_text, "rev-parse", "--show-toplevel"), env, GIT_TIMEOUT_SECONDS, _OUTPUT_LIMIT).decode("utf-8", "strict").strip()
            except CheckoutTimeout as exc:
                raise GitHistoryUnavailable("git_unavailable") from exc
            except CheckoutError as exc:
                reason = "output_limit" if "output exceeded" in str(exc) else "not_a_git_repository"
                raise GitHistoryUnavailable(reason) from exc
            try:
                shallow = _capture_git(_git_args("-C", root_text, "rev-parse", "--is-shallow-repository"), env, GIT_TIMEOUT_SECONDS, _OUTPUT_LIMIT).decode("ascii", "strict").strip()
                if shallow == "true":
                    raise GitHistoryUnavailable("shallow_history")
                head = _capture_git(_git_args("-C", root_text, "rev-parse", "--verify", "HEAD"), env, GIT_TIMEOUT_SECONDS, _OUTPUT_LIMIT).decode("ascii", "strict").strip()
                if not _SHA.fullmatch(head.encode("ascii")):
                    raise GitHistoryUnavailable("no_commits")
                head_ts_text = _capture_git(_git_args("-C", root_text, "show", "-s", "--format=%ct", "HEAD"), env, GIT_TIMEOUT_SECONDS, _OUTPUT_LIMIT).decode("ascii", "strict").strip()
                head_ts = int(head_ts_text)
            except CheckoutTimeout:
                raise
            except GitHistoryUnavailable:
                raise
            except CheckoutError as exc:
                if "output exceeded" in str(exc):
                    raise GitHistoryUnavailable("output_limit") from exc
                if "HEAD" in str(exc) or "revision" in str(exc).lower():
                    raise GitHistoryUnavailable("no_commits") from exc
                raise GitHistoryUnavailable("git_unavailable") from exc

            root_path = Path(top).resolve()
            try:
                relative_root = root.resolve().relative_to(root_path).as_posix()
            except ValueError:
                raise GitHistoryUnavailable("not_a_git_repository")
            cutoff = head_ts - window_days * 86400
            # Ask Git for one second of look-behind so its date parser's strict
            # boundary cannot omit a commit exactly at our inclusive cutoff.
            cutoff_date = datetime.fromtimestamp(cutoff - 1, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            pathspec = relative_root if relative_root not in ("", ".") else "."
            args = ["-C", str(root_path), "--literal-pathspecs", "-c", "core.quotepath=false", "log", "--no-merges", "--no-renames", "--relative", "-z", "--format=%H%x00%ct%x00%ae", f"--since-as-filter={cutoff_date}", "--name-only", "--", pathspec]
            try:
                raw = _capture_git(_git_args(*args), env, GIT_TIMEOUT_SECONDS, HISTORY_OUTPUT_LIMIT)
            except CheckoutTimeout as exc:
                raise GitHistoryUnavailable("git_unavailable") from exc
            except CheckoutError as exc:
                raise GitHistoryUnavailable("output_limit" if "output exceeded" in str(exc) else "git_unavailable") from exc

    except FileNotFoundError as exc:
        raise GitHistoryUnavailable("git_unavailable") from exc
    except OSError as exc:
        raise GitHistoryUnavailable("git_unavailable") from exc

    # Git's -z mode keeps pathnames NUL-delimited. Header fields are also NUL
    # separated; a newline prefixes each subsequent commit header.
    tokens = raw.split(b"\0")
    per_file_commits: dict[str, set[str]] = defaultdict(set)
    per_file_authors: dict[str, set[str]] = defaultdict(set)
    per_file_last: dict[str, int] = {}
    existing = set(files)
    commit_count = 0
    index = 0
    truncated = False
    while index < len(tokens):
        header_index = _header_index(tokens, index)
        if header_index is None:
            index += 1
            continue
        sha_token = tokens[header_index]
        try:
            timestamp = int(tokens[header_index + 1])
        except ValueError:
            index += 1
            continue
        email = tokens[header_index + 2].strip()
        in_window = cutoff <= timestamp <= head_ts
        if in_window:
            commit_count += 1
        if commit_count > MAX_HISTORY_COMMITS:
            truncated = True
            commit_count -= 1
            break
        author_key = hashlib.sha256(email.lower()).hexdigest()
        index = header_index + 3
        while index < len(tokens):
            item = tokens[index]
            if _header_index(tokens, index) is not None:
                break
            if item:
                try:
                    # Git terminates the formatted commit header with a newline
                    # before the first NUL-delimited pathname.
                    pathname = item[2:] if item.startswith(b"\r\n") else item[1:] if item.startswith(b"\n") else item
                    path = pathname.decode("utf-8", "surrogateescape").replace("\\", "/")
                    if relative_root not in ("", "."):
                        prefix = relative_root.rstrip("/") + "/"
                        if not path.startswith(prefix):
                            index += 1
                            continue
                        path = path[len(prefix):]
                    if in_window and path in existing:
                        per_file_commits[path].add(sha_token.decode("ascii"))
                        per_file_authors[path].add(author_key)
                        per_file_last[path] = max(timestamp, per_file_last.get(path, timestamp))
                except UnicodeError:
                    pass
            index += 1
        # Leave the next header for the outer loop.
    head_date = datetime.fromtimestamp(head_ts, timezone.utc).date().isoformat()
    top = sorted(per_file_commits, key=lambda path: (-len(per_file_commits[path]), path))[:20]
    return {
        "formula_version": "1", "available": True, "reason": None,
        "window_days": window_days, "head_commit": head, "head_commit_date": head_date,
        "commits_in_window": commit_count, "files_with_churn": len(per_file_commits),
        "truncated": truncated,
        "note": "commit limit reached; file counts cover the first 20000 in-window commits" if truncated else None,
        "top_churn": [{"path": path, "commits": len(per_file_commits[path]), "authors": len(per_file_authors[path]), "last_commit_date": datetime.fromtimestamp(per_file_last[path], timezone.utc).date().isoformat()} for path in top],
        "_churn_by_path": {path: len(changes) for path, changes in sorted(per_file_commits.items())},
        "basis": "commit counts from git log within the window; not a measure of defect probability",
    }


def unavailable_history(window_days: int, reason: str) -> dict[str, Any]:
    return {
        "formula_version": "1", "available": False, "reason": reason,
        "window_days": window_days, "head_commit": None, "head_commit_date": None,
        "commits_in_window": 0, "files_with_churn": 0, "truncated": False,
        "note": None,
        "top_churn": [],
        "basis": "commit counts from git log within the window; not a measure of defect probability",
    }
