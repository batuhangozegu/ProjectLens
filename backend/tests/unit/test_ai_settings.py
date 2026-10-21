import pytest

from projectlens.ai.settings import AISettings, get_ai_settings


def test_ai_settings_default_disabled_and_env_values():
    assert get_ai_settings({}) == AISettings()
    configured = get_ai_settings({"AI_ENABLED": "true", "AI_MAX_CONTEXT_BYTES": "2048",
                                  "AI_MAX_OUTPUT_TOKENS": "99", "AI_TIMEOUT_S": "3.5"})
    assert (configured.enabled, configured.max_context_bytes, configured.max_output_tokens,
            configured.timeout_s) == (True, 2048, 99, 3.5)


@pytest.mark.parametrize("values", [{"AI_MAX_CONTEXT_BYTES": "12"},
                                     {"AI_MAX_OUTPUT_TOKENS": "0"},
                                     {"AI_TIMEOUT_S": "nope"}])
def test_invalid_ai_settings_rejected(values):
    with pytest.raises(ValueError):
        get_ai_settings(values)
