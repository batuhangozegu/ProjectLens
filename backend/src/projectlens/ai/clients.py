"""Small synchronous stdlib clients. Credentials live only in the request scope."""
from __future__ import annotations

import http.client
import json
import socket
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

from .provider import (AIAuthFailedError, AIInvalidResponseError, AIRequest,
                       AIResponse, AITimeoutError, AIUnavailableError)
from .settings import DEFAULT_MODELS, validate_base_url

MAX_RESPONSE_BYTES = 65_536


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        # urllib otherwise forwards authentication headers on redirects.
        return None


def urlopen(request, *, timeout):
    # A fresh opener also avoids a global opener with HTTP wire debugging enabled.
    return build_opener(_NoRedirect()).open(request, timeout=timeout)


class _HTTPProvider:
    def __init__(self, api_key: str | None, model: str):
        self._api_key = api_key
        self.model = model

    def _post(self, url: str, payload: dict, headers: dict, timeout: float) -> dict:
        headers = {"Content-Type": "application/json", "Accept": "application/json", **headers}
        try:
            request = Request(url, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST")
            with urlopen(request, timeout=timeout) as response:
                raw = response.read(MAX_RESPONSE_BYTES + 1)
            if len(raw) > MAX_RESPONSE_BYTES:
                raise AIInvalidResponseError("AI response exceeds the size limit.")
            # Never relay a provider's echo of authentication headers or key.
            if self._api_key and self._api_key in raw.decode("utf-8"):
                raise AIInvalidResponseError("AI response contains sensitive data.")
            data = json.loads(raw)
            if not isinstance(data, dict):
                raise AIInvalidResponseError("AI response must be an object.")
            if self._api_key and self._api_key in json.dumps(data, ensure_ascii=False):
                raise AIInvalidResponseError("AI response contains sensitive data.")
            return data
        except HTTPError as exc:
            status = exc.code
            exc.close()  # Never read or log upstream error bodies/reasons/headers.
            if status in {401, 403}:
                raise AIAuthFailedError("AI credentials were rejected.") from None
            if status in {408, 504}:
                raise AITimeoutError("AI request timed out.") from None
            if status == 429 or status >= 500:
                raise AIUnavailableError("AI provider is unavailable.") from None
            raise AIInvalidResponseError("AI provider rejected the request.") from None
        except URLError as exc:
            if isinstance(exc.reason, (TimeoutError, socket.timeout)):
                raise AITimeoutError("AI request timed out.") from None
            raise AIUnavailableError("AI provider is unavailable.") from None
        except (TimeoutError, socket.timeout):
            raise AITimeoutError("AI request timed out.") from None
        except (OSError, http.client.HTTPException):
            raise AIUnavailableError("AI provider is unavailable.") from None
        except (ValueError, UnicodeError, RecursionError):
            raise AIInvalidResponseError("AI response is invalid.") from None

    def _response(self, text, usage, input_key, output_key) -> AIResponse:
        if not isinstance(usage, dict):
            raise AIInvalidResponseError("AI usage is invalid.")
        try:
            text_bytes = len(text.encode("utf-8")) if isinstance(text, str) else 0
        except UnicodeError:
            raise AIInvalidResponseError("AI text is invalid.") from None
        input_tokens, output_tokens = usage.get(input_key, 0), usage.get(output_key, 0)
        if (not isinstance(text, str) or not text.strip() or text_bytes > 16_384
                or type(input_tokens) is not int or input_tokens < 0
                or type(output_tokens) is not int or output_tokens < 0
                or (self._api_key and self._api_key in text)):
            raise AIInvalidResponseError("AI response is invalid.")
        # Report the requested model, never untrusted upstream metadata.
        return AIResponse(text, input_tokens, output_tokens, self.model)


class AnthropicProvider(_HTTPProvider):
    name = "anthropic"

    def __init__(self, api_key: str | None, model: str = DEFAULT_MODELS["anthropic"]):
        super().__init__(api_key, model)

    def complete(self, request: AIRequest) -> AIResponse:
        if not self._api_key:
            raise AIAuthFailedError("AI credentials are required.")
        data = self._post("https://api.anthropic.com/v1/messages", {
            "model": self.model, "system": request.system,
            "messages": [{"role": "user", "content": request.user}],
            "max_tokens": request.max_output_tokens,
        }, {"x-api-key": self._api_key, "anthropic-version": "2023-06-01"}, request.timeout_s)
        content = data.get("content")
        if (not isinstance(content, list) or not content
                or any(not isinstance(block, dict) for block in content)):
            raise AIInvalidResponseError("AI content is invalid.")
        blocks = [block.get("text") for block in content if block.get("type") == "text"]
        if any(not isinstance(block, str) for block in blocks):
            raise AIInvalidResponseError("AI text is invalid.")
        return self._response("\n".join(blocks), data.get("usage", {}), "input_tokens", "output_tokens")


class OpenAIProvider(_HTTPProvider):
    name = "openai"
    base_url = "https://api.openai.com/v1"
    token_field = "max_completion_tokens"

    def __init__(self, api_key: str | None, model: str = DEFAULT_MODELS["openai"]):
        super().__init__(api_key, model)

    def complete(self, request: AIRequest) -> AIResponse:
        if not self._api_key and self.name == "openai":
            raise AIAuthFailedError("AI credentials are required.")
        headers = {"Authorization": f"Bearer {self._api_key}"} if self._api_key else {}
        data = self._post(f"{self.base_url}/chat/completions", {
            "model": self.model, "stream": False,
            "messages": [{"role": "system", "content": request.system},
                         {"role": "user", "content": request.user}],
            self.token_field: request.max_output_tokens,
        }, headers, request.timeout_s)
        try:
            text = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError):
            raise AIInvalidResponseError("AI content is invalid.") from None
        return self._response(text, data.get("usage", {}), "prompt_tokens", "completion_tokens")


class OpenAICompatibleProvider(OpenAIProvider):
    name = "openai-compatible"
    token_field = "max_tokens"

    def __init__(self, base_url: str, model: str, api_key: str | None = None):
        validate_base_url(base_url)
        super().__init__(api_key, model)
        base = base_url.rstrip("/")
        # Accept a server root or a versioned/custom API prefix; append /v1 only to roots.
        self.base_url = base + "/v1" if not urlsplit(base).path else base
