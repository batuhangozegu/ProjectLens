"""Provider-neutral AI request/response contract; contains no network code."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class AIRequest:
    system: str
    user: str
    max_output_tokens: int
    timeout_s: float


@dataclass(frozen=True)
class AIResponse:
    text: str
    input_tokens: int
    output_tokens: int
    model: str


class AIProviderError(Exception):
    """Base for provider failures safe to map to stable API errors."""


class AITimeoutError(AIProviderError):
    pass


class AIUnavailableError(AIProviderError):
    pass


class AIInvalidResponseError(AIProviderError):
    pass


class AIAuthFailedError(AIProviderError):
    """The provider rejected credentials (or required credentials are missing)."""


class AIProvider(Protocol):
    def complete(self, request: AIRequest) -> AIResponse: ...


class FakeProvider:
    """Deterministic test/offline provider. Responses/errors may be queued."""

    def __init__(self, responses: list[AIResponse | Exception] | None = None):
        self.responses = list(responses or [AIResponse("A deterministic explanation.", 0, 0, "fake")])
        self.requests: list[AIRequest] = []

    def complete(self, request: AIRequest) -> AIResponse:
        self.requests.append(request)
        if not self.responses:
            raise AIUnavailableError("No fake response is queued.")
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response
