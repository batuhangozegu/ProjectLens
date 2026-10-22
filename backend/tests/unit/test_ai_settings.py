import pytest

from projectlens.ai.settings import (AIConfigurationError, AISettings, DEFAULT_MODELS,
                                     get_ai_settings, resolve_provider_settings)


def test_ai_settings_default_disabled_and_env_values():
    assert get_ai_settings({}) == AISettings()
    configured = get_ai_settings({"AI_ENABLED": "true", "AI_MAX_CONTEXT_BYTES": "2048",
                                  "AI_MAX_OUTPUT_TOKENS": "99", "AI_TIMEOUT_S": "3.5"})
    assert (configured.enabled, configured.max_context_bytes, configured.max_output_tokens,
            configured.timeout_s) == (True, 2048, 99, 3.5)


@pytest.mark.parametrize("values", [{"AI_MAX_CONTEXT_BYTES": "12"},
                                     {"AI_MAX_OUTPUT_TOKENS": "0"},
                                     {"AI_TIMEOUT_S": "nan"},
                                     {"AI_TIMEOUT_S": "inf"},
                                     {"AI_TIMEOUT_S": "nope"}])
def test_invalid_ai_settings_rejected(values):
    with pytest.raises(ValueError):
        get_ai_settings(values)


def test_provider_settings_env_and_request_isolation():
    env = {"PROJECTLENS_AI_PROVIDER": "openai", "PROJECTLENS_AI_API_KEY": "server-secret"}
    assert resolve_provider_settings({}, {}) is None
    config = resolve_provider_settings({}, env)
    assert (config.provider, config.model, config.api_key) == ("openai", DEFAULT_MODELS["openai"], "server-secret")
    request = {"x-ai-provider": "openai-compatible", "x-ai-model": "org/model:latest",
               "x-ai-base-url": "http://localhost:11434"}
    config = resolve_provider_settings(request, env)
    assert config.api_key is None
    assert "server-secret" not in repr(config)
    assert resolve_provider_settings({"x-ai-provider": "anthropic"}, {}).model == DEFAULT_MODELS["anthropic"]


@pytest.mark.parametrize("headers", [
    {"x-ai-provider": "unknown"}, {"x-ai-provider": "OPENAI"}, {"x-ai-key": "secret"},
    {"x-ai-provider": "openai", "x-ai-model": ""},
    {"x-ai-provider": "openai", "x-ai-model": "has space"},
    {"x-ai-provider": "openai", "x-ai-model": "x" * 201},
    {"x-ai-provider": "openai", "x-ai-model": "model\r\nx: y"},
    {"x-ai-provider": "openai", "x-ai-key": ""},
    {"x-ai-provider": "openai", "x-ai-key": "x" * 4097},
    {"x-ai-provider": "openai", "x-ai-key": "a\nb"},
    {"x-ai-provider": "openai", "x-ai-base-url": "https://example.org"},
    {"x-ai-provider": "openai", "x-ai-model": "secret-model", "x-ai-key": "secret"},
    {"x-ai-provider": "openai-compatible", "x-ai-model": "local-model"},
    {"x-ai-provider": "openai-compatible", "x-ai-base-url": "http://localhost:11434"},
])
def test_invalid_provider_settings(headers):
    with pytest.raises(AIConfigurationError):
        resolve_provider_settings(headers, {})


@pytest.mark.parametrize("url", ["file:///tmp/model", "ftp://localhost", "https:///missing",
                                "http://user:secret@localhost/v1", "http://user@localhost",
                                "http://localhost:99999", "http://localhost:bad", "http://[broken",
                                "http://localhost/v1?key=secret", "http://localhost/#secret",
                                "http://localhost\\@evil.test", "http://local host", "http://%61.test",
                                "http://localhost/\npath", "http://localhost/" + "x" * 2048])
def test_invalid_compatible_base_url(url):
    with pytest.raises(AIConfigurationError):
        resolve_provider_settings({"x-ai-provider": "openai-compatible", "x-ai-model": "local",
                                   "x-ai-base-url": url}, {})


@pytest.mark.parametrize("url", ["http://localhost:11434", "https://example.org/v1/",
                                "http://127.0.0.1:1234/v1", "http://[::1]:1234/v1"])
def test_valid_compatible_base_url(url):
    assert resolve_provider_settings({"x-ai-provider": "openai-compatible", "x-ai-model": "model:latest",
                                      "x-ai-base-url": url}, {}).base_url == url.rstrip("/")
