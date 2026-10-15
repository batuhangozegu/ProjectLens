"""Portable normalization for repository-relative task evidence paths."""

from __future__ import annotations

import re
import unicodedata


def normalize_task_path(path: str) -> str:
    """Normalize a file or directory-prefix path and reject unsafe forms."""
    if not isinstance(path, str):
        raise ValueError("path must be a string")
    value = path.replace("\\", "/")
    while value.startswith("./"):
        value = value[2:]
    value = re.sub(r"/+", "/", value)
    if not value or value.startswith("/") or re.match(r"^[A-Za-z]:", value):
        raise ValueError("path must be a non-empty relative repository path")
    if any(part == ".." for part in value.split("/")):
        raise ValueError("path must not contain '..' segments")
    if any(unicodedata.category(char) == "Cc" for char in value):
        raise ValueError("path must not contain control characters")
    if len(value) > 500:
        raise ValueError("path must be at most 500 characters")
    if not value.rstrip("/"):
        raise ValueError("path must identify a file or directory")
    return value.rstrip("/") + "/" if value.endswith("/") else value


def normalize_file_path(path: str) -> str:
    value = normalize_task_path(path)
    if value.endswith("/"):
        raise ValueError("path must identify a file, not a directory prefix")
    return value
