"""Small environment-backed settings for the optional AI feature."""
from __future__ import annotations

import os
import math
import re
from dataclasses import dataclass
from typing import Mapping
from urllib.parse import urlsplit

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
    if size < 1024 or output < 1 or not math.isfinite(timeout) or timeout <= 0:
        raise ValueError("AI context bytes, output tokens, and timeout must be positive and within supported bounds.")
    return AISettings(enabled, size, output, timeout)


DEFAULT_MODELS = {"anthropic": "claude-haiku-4-5-20251001", "openai": "gpt-4.1-mini"}
MODEL_PATTERN = r"[A-Za-z0-9][A-Za-z0-9._:/+@-]{0,199}"
MAX_KEY_LENGTH = 4096


class AIConfigurationError(ValueError):
    """Invalid configuration; messages never contain supplied values."""


@dataclass(frozen=True, repr=False)
class AIProviderSettings:
    # No generated repr: even a malicious model/base URL may contain the key.
    provider: str
    model: str
    base_url: str | None
    api_key: str | None


def resolve_provider_settings(headers: Mapping[str, str],
                              environ: Mapping[str, str] | None = None) -> AIProviderSettings | None:
    """Request headers are an isolated configuration, never merged with env secrets."""
    values = os.environ if environ is None else environ
    names = ("provider", "model", "base-url", "key")
    supplied = {name: headers.get(f"x-ai-{name}") for name in names}
    if any(value is not None for value in supplied.values()):
        provider, model, base_url, key = (supplied[name] for name in names)
    else:
        provider, model, base_url, key = (values.get(f"PROJECTLENS_AI_{name}")
                                          for name in ("PROVIDER", "MODEL", "BASE_URL", "API_KEY"))
        if not any(value is not None for value in (provider, model, base_url, key)):
            return None
    if provider not in {"anthropic", "openai", "openai-compatible"}:
        raise AIConfigurationError("A supported AI provider must be specified.")
    if model is None:
        model = DEFAULT_MODELS.get(provider)
    if model is None or re.fullmatch(MODEL_PATTERN, model, flags=re.ASCII) is None:
        raise AIConfigurationError("AI model must be 1–200 supported ASCII characters; compatible providers require a model.")
    if base_url is not None and provider != "openai-compatible":
        raise AIConfigurationError("AI base URL is only supported for openai-compatible.")
    if provider == "openai-compatible":
        validate_base_url(base_url)
        base_url = base_url.rstrip("/")
    if key is not None and (not 1 <= len(key) <= MAX_KEY_LENGTH
                            or any(ord(ch) < 33 or ord(ch) > 126 for ch in key)):
        raise AIConfigurationError("AI key must be 1–4096 visible ASCII characters without whitespace.")
    # Prevent credentials smuggled into fields returned in /ai/test or an outbound URL.
    if key and (key in model or (base_url and key in base_url)):
        raise AIConfigurationError("AI credentials must only be supplied in the key field.")
    return AIProviderSettings(provider, model, base_url, key)


def validate_base_url(value: str | None) -> None:
    try:
        if (not value or len(value) > 2048 or "\\" in value
                or any(ord(ch) <= 32 or ord(ch) >= 127 for ch in value)):
            raise ValueError
        parsed = urlsplit(value)
        if (parsed.scheme not in {"http", "https"} or not parsed.hostname
                or parsed.username is not None or parsed.password is not None
                or "@" in parsed.netloc or parsed.query or parsed.fragment
                or "?" in value or "#" in value or "%" in parsed.netloc):
            raise ValueError
        # Accessing .port also validates malformed/out-of-range ports.
        if parsed.port is not None and not 1 <= parsed.port <= 65535:
            raise ValueError
        host = parsed.hostname
        if ":" not in host and re.fullmatch(r"[A-Za-z0-9](?:[A-Za-z0-9.-]*[A-Za-z0-9])?", host) is None:
            raise ValueError
    except ValueError:
        raise AIConfigurationError("AI base URL must be an HTTP(S) URL with a host, without userinfo, query or fragment.") from None
