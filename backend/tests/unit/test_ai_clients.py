import io
import json
import socket
from urllib.error import HTTPError, URLError
from urllib.request import Request

import pytest

from projectlens.ai import clients
from projectlens.ai.clients import AnthropicProvider, OpenAIProvider, OpenAICompatibleProvider
from projectlens.ai.provider import (AIAuthFailedError, AIInvalidResponseError, AIRequest,
                                    AITimeoutError, AIUnavailableError)

KEY = "sk-private-test-credential"
REQUEST = AIRequest("Fixed system", "Bounded context", 16, 2.5)


@pytest.fixture(autouse=True)
def capture_all_logs(caplog):
    caplog.set_level("DEBUG")


def chat_response(text="OK"):
    return {"choices": [{"message": {"content": text}}],
            "usage": {"prompt_tokens": 3, "completion_tokens": 1}, "model": "upstream-model"}


@pytest.mark.parametrize("provider,url,token_field", [
    (AnthropicProvider(KEY, "claude-test"), "https://api.anthropic.com/v1/messages", "max_tokens"),
    (OpenAIProvider(KEY, "gpt-test"), "https://api.openai.com/v1/chat/completions", "max_completion_tokens"),
    (OpenAICompatibleProvider("http://localhost:11434", "llama3.2"),
     "http://localhost:11434/v1/chat/completions", "max_tokens"),
    (OpenAICompatibleProvider("http://localhost:1234/v1/", "local-model", KEY),
     "http://localhost:1234/v1/chat/completions", "max_tokens"),
    (OpenAICompatibleProvider("https://example.org/custom/api", "local-model"),
     "https://example.org/custom/api/chat/completions", "max_tokens"),
])
def test_provider_request_shape(provider, url, token_field, monkeypatch, caplog):
    def open_request(request, *, timeout):
        assert request.full_url == url
        assert request.method == "POST"
        assert timeout == REQUEST.timeout_s
        headers = {name.lower(): value for name, value in request.header_items()}
        assert headers["content-type"] == "application/json"
        payload = json.loads(request.data)
        assert KEY not in request.data.decode()
        assert payload["model"] == provider.model
        assert payload[token_field] == REQUEST.max_output_tokens
        if provider.name == "anthropic":
            assert headers["x-api-key"] == KEY
            assert headers["anthropic-version"] == "2023-06-01"
            assert "authorization" not in headers
            assert payload["system"] == REQUEST.system
            assert payload["messages"] == [{"role": "user", "content": REQUEST.user}]
            result = {"content": [{"type": "text", "text": "OK"}],
                      "usage": {"input_tokens": 3, "output_tokens": 1}}
        else:
            assert payload["stream"] is False
            assert payload["messages"] == [{"role": "system", "content": REQUEST.system},
                                           {"role": "user", "content": REQUEST.user}]
            if provider._api_key:
                assert headers["authorization"] == f"Bearer {KEY}"
            else:
                assert "authorization" not in headers
            result = chat_response()
        return io.BytesIO(json.dumps(result).encode())

    monkeypatch.setattr(clients, "urlopen", open_request)
    response = provider.complete(REQUEST)
    assert (response.text, response.input_tokens, response.output_tokens, response.model) == ("OK", 3, 1, provider.model)
    assert KEY not in repr(provider)
    assert KEY not in caplog.text


@pytest.mark.parametrize("status,error", [(401, AIAuthFailedError), (403, AIAuthFailedError),
                                         (408, AITimeoutError), (504, AITimeoutError),
                                         (429, AIUnavailableError), (500, AIUnavailableError),
                                         (503, AIUnavailableError), (400, AIInvalidResponseError),
                                         (302, AIInvalidResponseError)])
def test_http_errors_are_sanitized(status, error, monkeypatch, caplog):
    body = io.BytesIO(KEY.encode())

    def fail(*args, **kwargs):
        raise HTTPError("https://example.org/" + KEY, status, KEY, {"secret": KEY}, body)

    monkeypatch.setattr(clients, "urlopen", fail)
    with pytest.raises(error) as caught:
        OpenAIProvider(KEY).complete(REQUEST)
    assert body.closed
    assert KEY not in str(caught.value)
    assert KEY not in repr(caught.value)
    assert caught.value.__suppress_context__
    assert KEY not in caplog.text


@pytest.mark.parametrize("failure,error", [(TimeoutError(KEY), AITimeoutError),
                                          (URLError(socket.timeout(KEY)), AITimeoutError),
                                          (URLError(KEY), AIUnavailableError),
                                          (OSError(KEY), AIUnavailableError)])
def test_network_error_mapping(failure, error, monkeypatch, caplog):
    def fail(*args, **kwargs):
        raise failure

    monkeypatch.setattr(clients, "urlopen", fail)
    with pytest.raises(error) as caught:
        OpenAIProvider(KEY).complete(REQUEST)
    assert KEY not in str(caught.value)
    assert KEY not in caplog.text


@pytest.mark.parametrize("data", [b"not json", b"[]", b"{}", b"\xff",
                                  json.dumps(chat_response("")).encode(),
                                  json.dumps(chat_response(KEY)).encode(),
                                  json.dumps(chat_response(KEY)).replace("sk-private", "\\u0073k-private").encode(),
                                  b'{"choices":[{"message":{"content":"\\ud800"}}]}',
                                  json.dumps(chat_response("x" * 16_385)).encode(),
                                  json.dumps({"choices": None}).encode(),
                                  json.dumps({**chat_response(), "usage": {"prompt_tokens": -1}}).encode(),
                                  json.dumps({**chat_response(), "usage": {"completion_tokens": True}}).encode(),
                                  b"x" * (clients.MAX_RESPONSE_BYTES + 1)],
                         ids=[f"case{i}" for i in range(13)])
def test_invalid_and_sensitive_responses(data, monkeypatch, caplog):
    monkeypatch.setattr(clients, "urlopen", lambda *args, **kwargs: io.BytesIO(data))
    with pytest.raises(AIInvalidResponseError) as caught:
        OpenAIProvider(KEY).complete(REQUEST)
    assert KEY not in str(caught.value)
    assert KEY not in caplog.text


def test_response_read_is_bounded(monkeypatch):
    class BoundedRead(io.BytesIO):
        def read(self, size=-1):
            assert size == clients.MAX_RESPONSE_BYTES + 1
            return super().read(size)

    monkeypatch.setattr(clients, "urlopen", lambda *args, **kwargs: BoundedRead(json.dumps(chat_response()).encode()))
    assert OpenAIProvider(KEY).complete(REQUEST).text == "OK"


@pytest.mark.parametrize("data", [{"content": []}, {"content": None}, {"content": [None]},
                                  {"content": [{"type": "text", "text": None}]}])
def test_anthropic_malformed_content(data, monkeypatch):
    monkeypatch.setattr(clients, "urlopen", lambda *args, **kwargs: io.BytesIO(json.dumps(data).encode()))
    with pytest.raises(AIInvalidResponseError):
        AnthropicProvider(KEY).complete(REQUEST)


@pytest.mark.parametrize("provider", [AnthropicProvider(None), OpenAIProvider(None)])
def test_required_key_missing_does_not_send(provider, monkeypatch):
    def unexpected(*args, **kwargs):
        pytest.fail("Missing credentials must not make a network request")

    monkeypatch.setattr(clients, "urlopen", unexpected)
    with pytest.raises(AIAuthFailedError):
        provider.complete(REQUEST)


def test_redirects_cannot_forward_credentials():
    request = Request("https://example.org", headers={"Authorization": f"Bearer {KEY}"})
    assert clients._NoRedirect().redirect_request(request, None, 302, "Found", {}, "https://other.org") is None
