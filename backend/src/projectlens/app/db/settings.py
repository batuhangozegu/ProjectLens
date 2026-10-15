"""Database settings: process environment first, optional local ``.env`` fallback."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping


@dataclass(frozen=True)
class Settings:
    database_url: str


def parse_dotenv(text: str) -> dict[str, str]:
    """Parse simple ``KEY=VALUE`` lines; ``#`` comments and surrounding quotes are ignored."""
    values: dict[str, str] = {}
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "'\"":
            value = value[1:-1]
        values[key.strip()] = value
    return values


def _dotenv_candidates() -> list[Path]:
    # cwd first, then backend/ next to this source tree (editable installs).
    return [Path.cwd() / ".env", Path(__file__).resolve().parents[4] / ".env"]


def _database_url_from_dotenv() -> str:
    for path in _dotenv_candidates():
        try:
            values = parse_dotenv(path.read_text(encoding="utf-8"))
        except OSError:
            continue
        if values.get("DATABASE_URL", "").strip():
            return values["DATABASE_URL"].strip()
    return ""


def get_settings(environ: Mapping[str, str] | None = None) -> Settings:
    """Read DATABASE_URL from the supplied environment, else the process environment.

    When no mapping is supplied and the process environment has no value, a local
    ``.env`` file (never committed) is consulted. An explicit mapping is used as-is.
    """
    if environ is not None:
        url = environ.get("DATABASE_URL", "").strip()
    else:
        url = os.environ.get("DATABASE_URL", "").strip() or _database_url_from_dotenv()
    if not url:
        raise RuntimeError("DATABASE_URL is required; set it in the environment or backend/.env")
    return Settings(database_url=url)
