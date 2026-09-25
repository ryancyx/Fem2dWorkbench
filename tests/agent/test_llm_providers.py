from __future__ import annotations

import pytest

from agent.llm_client import LLMClient
from agent.llm_providers import (
    DeepSeekLLMClient,
    LLMConfigurationError,
    LLMProviderConfig,
    OpenAILLMClient,
    create_llm_client,
)


SCHEMA = {
    "title": "Tiny Result",
    "type": "object",
    "additionalProperties": False,
    "required": ["value"],
    "properties": {"value": {"type": "string"}},
}


def test_provider_config_loads_generic_environment_without_exposing_key() -> None:
    config = LLMProviderConfig.from_env(
        {
            "FEM2D_AGENT_LLM_PROVIDER": "openai",
            "FEM2D_AGENT_LLM_MODEL": "configured-model",
            "FEM2D_AGENT_LLM_API_KEY": "secret-value",
            "FEM2D_AGENT_LLM_BASE_URL": "https://example.invalid/v1",
            "FEM2D_AGENT_LLM_TIMEOUT_SECONDS": "30",
        }
    )

    assert config.provider == "openai"
    assert config.model == "configured-model"
    assert config.api_key == "secret-value"
    assert config.base_url == "https://example.invalid/v1"
    assert config.timeout_seconds == 30.0


@pytest.mark.parametrize("provider", ["openai", "deepseek"])
def test_missing_api_key_has_clear_configuration_error(provider: str) -> None:
    with pytest.raises(LLMConfigurationError, match="API_KEY"):
        LLMProviderConfig.from_env(
            {
                "FEM2D_AGENT_LLM_PROVIDER": provider,
                "FEM2D_AGENT_LLM_MODEL": "model",
                "FEM2D_AGENT_LLM_BASE_URL": "https://example.invalid/v1",
            }
        )


def test_openai_adapter_uses_responses_json_schema_without_agent_changes() -> None:
    captured = {}

    def transport(url, headers, payload, timeout):
        captured.update(url=url, headers=headers, payload=payload, timeout=timeout)
        return {
            "output": [
                {
                    "type": "message",
                    "content": [{"type": "output_text", "text": '{"value":"ok"}'}],
                }
            ]
        }

    client = create_llm_client(
        LLMProviderConfig("openai", "model-a", "test-key", "https://openai.invalid/v1"),
        transport=transport,
    )

    assert isinstance(client, LLMClient)
    assert client.request("system", "user", SCHEMA) == {"value": "ok"}
    assert captured["url"] == "https://openai.invalid/v1/responses"
    assert captured["headers"]["Authorization"] == "Bearer test-key"
    assert captured["payload"]["text"]["format"]["type"] == "json_schema"
    assert captured["payload"]["text"]["format"]["schema"] == SCHEMA
    assert captured["payload"]["model"] == "model-a"


def test_deepseek_adapter_uses_json_output_and_same_llm_protocol() -> None:
    captured = {}

    def transport(url, headers, payload, timeout):
        captured.update(url=url, headers=headers, payload=payload, timeout=timeout)
        return {"choices": [{"message": {"content": '{"value":"ok"}'}}]}

    client = create_llm_client(
        LLMProviderConfig(
            "deepseek",
            "model-b",
            "test-key",
            "https://deepseek.invalid/v1",
        ),
        transport=transport,
    )

    assert isinstance(client, LLMClient)
    assert client.request("system", "user", SCHEMA) == {"value": "ok"}
    assert captured["url"] == "https://deepseek.invalid/v1/chat/completions"
    assert captured["payload"]["response_format"] == {"type": "json_object"}
    assert "JSON Schema" in captured["payload"]["messages"][0]["content"]
    assert captured["payload"]["model"] == "model-b"


def test_provider_specific_environment_variables_are_supported() -> None:
    config = LLMProviderConfig.from_env(
        {
            "FEM2D_AGENT_LLM_PROVIDER": "deepseek",
            "DEEPSEEK_MODEL": "deepseek-model",
            "DEEPSEEK_API_KEY": "deepseek-key",
            "DEEPSEEK_BASE_URL": "https://deepseek.invalid/v1",
        }
    )

    assert config == LLMProviderConfig(
        provider="deepseek",
        model="deepseek-model",
        api_key="deepseek-key",
        base_url="https://deepseek.invalid/v1",
    )


def test_factory_switches_provider_without_changing_request_interface() -> None:
    openai = create_llm_client(
        LLMProviderConfig("openai", "a", "key", "https://a.invalid/v1"),
        transport=lambda *_args: {"output_text": '{"value":"openai"}'},
    )
    deepseek = create_llm_client(
        LLMProviderConfig("deepseek", "b", "key", "https://b.invalid/v1"),
        transport=lambda *_args: {
            "choices": [{"message": {"content": '{"value":"deepseek"}'}}]
        },
    )

    assert openai.request("system", "user", SCHEMA) == {"value": "openai"}
    assert deepseek.request("system", "user", SCHEMA) == {"value": "deepseek"}
    assert isinstance(openai, OpenAILLMClient)
    assert isinstance(deepseek, DeepSeekLLMClient)
