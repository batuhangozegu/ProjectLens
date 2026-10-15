"""Minimal environment-only database settings."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Mapping


@dataclass(frozen=True)
class Settings:
    database_url: str


def get_settings(environ: Mapping[str, str] | None = None) -> Settings:
    """Read DATABASE_URL from the supplied environment (or process environment)."""
    values = os.environ if environ is None else environ
    url = values.get("DATABASE_URL", "").strip()
    if not url:
        raise RuntimeError("DATABASE_URL is required; set it in the environment")
    return Settings(database_url=url)
