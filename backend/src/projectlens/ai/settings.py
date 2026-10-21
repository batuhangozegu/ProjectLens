"""Small environment-backed settings for the optional AI feature."""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Mapping

from .context import DEFAULT_MAX_BYTES


@dataclass(frozen=True)
class AISettings:
    enabled: bool = False
    max_context_bytes: int = DEFAULT_MAX_BYTES
    max_output_tokens: int = 512
    timeout_s: float = 20.0


def get_ai_settings(environ: Mapping[str, str] | None = None) -> AISettings:
    values = os.environ if environ is None else environ
    enabled = values.get("AI_ENABLED", "false").strip().lower() in {"1", "true", "yes", "on"}
    try:
        size = int(values.get("AI_MAX_CONTEXT_BYTES", str(DEFAULT_MAX_BYTES)))
        output = int(values.get("AI_MAX_OUTPUT_TOKENS", "512"))
        timeout = float(values.get("AI_TIMEOUT_S", "20"))
    except ValueError as exc:
        raise ValueError("AI settings must be valid numeric values.") from exc
    if size < 1024 or output < 1 or timeout <= 0:
        raise ValueError("AI context bytes, output tokens, and timeout must be positive and within supported bounds.")
    return AISettings(enabled, size, output, timeout)
