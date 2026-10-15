"""Validation for public HTTPS GitHub repository URLs."""

from __future__ import annotations

import re
from urllib.parse import urlsplit


class InvalidRepositoryUrl(ValueError):
    """The supplied URL is not an allowed public GitHub repository URL."""


_OWNER = re.compile(r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,37}[A-Za-z0-9])?\Z", re.ASCII)
_REPO = re.compile(r"[A-Za-z0-9._-]{1,100}\Z", re.ASCII)


def validate_repository_url(value: str) -> tuple[str, str, str]:
    """Return ``(canonical_url, owner, repo)`` for an HTTPS GitHub URL.

    Only ASCII owner/repository names are accepted. The returned clone URL has
    no trailing slash or ``.git`` suffix, so equivalent inputs normalize alike.
    """
    if not isinstance(value, str) or not value or len(value) > 2048:
        raise InvalidRepositoryUrl("repository URL must be a non-empty string of at most 2048 characters")
    if any(ord(char) < 0x20 or ord(char) == 0x7F or char.isspace() for char in value):
        raise InvalidRepositoryUrl("whitespace and control characters are not allowed")
    if not value.isascii():
        raise InvalidRepositoryUrl("repository URL must contain ASCII characters only")
    try:
        parsed = urlsplit(value)
        # Accessing port/user/password can raise for malformed authorities.
        port = parsed.port
    except ValueError as exc:
        raise InvalidRepositoryUrl("malformed repository URL") from exc
    if parsed.scheme != "https" or parsed.netloc != "github.com" or parsed.hostname != "github.com" or port is not None:
        raise InvalidRepositoryUrl("only https://github.com/<owner>/<repo> URLs are allowed")
    if parsed.username is not None or parsed.password is not None:
        raise InvalidRepositoryUrl("credentials are not allowed in repository URLs")
    if parsed.query or parsed.fragment:
        raise InvalidRepositoryUrl("query strings and fragments are not allowed")
    path = parsed.path
    if path.endswith("/"):
        path = path[:-1]
    if path.endswith(".git"):
        path = path[:-4]
    parts = path.split("/")
    if len(parts) != 3 or parts[0] != "" or not parts[1] or not parts[2]:
        raise InvalidRepositoryUrl("URL must contain exactly an owner and repository path")
    owner, repo = parts[1:]
    if len(owner) > 39 or not _OWNER.fullmatch(owner):
        raise InvalidRepositoryUrl("invalid GitHub owner name")
    if len(repo) > 100 or repo.startswith("-") or not _REPO.fullmatch(repo) or repo in {".", ".."}:
        raise InvalidRepositoryUrl("invalid GitHub repository name")
    return f"https://github.com/{owner}/{repo}", owner, repo
