from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from typing import Any, Callable, Mapping
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from agent.llm_client import LLMClient, StructuredOutputError


class LLMConfigurationError(ValueError):
    """Raised when an external provider is not fully configured."""


class LLMProviderError(RuntimeError):
    """Raised when an external provider request cannot produce structured output."""


@dataclass(frozen=True, slots=True)
class LLMProviderConfig:
    provider: str
    model: str
    api_key: str
    base_url: str
    timeout_seconds: float = 120.0

    def __post_init__(self) -> None:
        provider = str(self.provider).strip().lower()
        if provider not in {"openai", "deepseek"}:
            raise LLMConfigurationError("provider must be 'openai' or 'deepseek'")
        object.__setattr__(self, "provider", provider)
        for field_name in ("model", "api_key", "base_url"):
            value = str(getattr(self, field_name)).strip()
            if not value:
                raise LLMConfigurationError(f"{field_name} must be configured")
            object.__setattr__(self, field_name, value)
        timeout = float(self.timeout_seconds)
        if timeout <= 0.0:
            raise LLMConfigurationError("timeout_seconds must be positive")
        object.__setattr__(self, "timeout_seconds", timeout)

    @classmethod
    def from_env(cls, environ: Mapping[str, str] | None = None) -> "LLMProviderConfig":
        source = _runtime_environment() if environ is None else environ
        provider = str(source.get("FEM2D_AGENT_LLM_PROVIDER", "")).strip().lower()
        if provider not in {"openai", "deepseek"}:
            raise LLMConfigurationError(
                "Set FEM2D_AGENT_LLM_PROVIDER to 'openai' or 'deepseek'"
            )
        prefix = provider.upper()
        values = {
            "model": source.get("FEM2D_AGENT_LLM_MODEL") or source.get(f"{prefix}_MODEL"),
            "api_key": source.get("FEM2D_AGENT_LLM_API_KEY") or source.get(f"{prefix}_API_KEY"),
            "base_url": source.get("FEM2D_AGENT_LLM_BASE_URL") or source.get(f"{prefix}_BASE_URL"),
        }
        missing = [name for name, value in values.items() if not str(value or "").strip()]
        if missing:
            generic_names = ", ".join(
                f"FEM2D_AGENT_LLM_{name.upper()}" for name in missing
            )
            raise LLMConfigurationError(
                f"Missing {provider} provider configuration: {generic_names} "
                f"(or matching {prefix}_* variables)"
            )
        timeout_text = source.get("FEM2D_AGENT_LLM_TIMEOUT_SECONDS", "120")
        return cls(
            provider=provider,
            model=str(values["model"]),
            api_key=str(values["api_key"]),
            base_url=str(values["base_url"]),
            timeout_seconds=float(timeout_text),
        )


Transport = Callable[[str, dict[str, str], dict[str, Any], float], dict[str, Any]]


class _HTTPJSONClient:
    def __init__(
        self,
        config: LLMProviderConfig,
        transport: Transport | None = None,
    ) -> None:
        self.config = config
        self._transport = transport or self._post_json

    def _send(self, endpoint: str, payload: dict[str, Any]) -> dict[str, Any]:
        headers = {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json",
        }
        try:
            response = self._transport(
                self._endpoint(endpoint),
                headers,
                payload,
                self.config.timeout_seconds,
            )
        except LLMProviderError:
            raise
        except Exception as exc:
            raise LLMProviderError(
                f"{self.config.provider} API request failed: {type(exc).__name__}: {exc}"
            ) from exc
        if not isinstance(response, dict):
            raise LLMProviderError(f"{self.config.provider} API returned a non-object response")
        return response

    def _endpoint(self, suffix: str) -> str:
        return f"{self.config.base_url.rstrip('/')}/{suffix.lstrip('/')}"

    @staticmethod
    def _post_json(
        url: str,
        headers: dict[str, str],
        payload: dict[str, Any],
        timeout_seconds: float,
    ) -> dict[str, Any]:
        request = Request(
            url=url,
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers=headers,
            method="POST",
        )
        try:
            with urlopen(request, timeout=timeout_seconds) as response:
                body = response.read().decode("utf-8")
        except HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")[:1000]
            raise LLMProviderError(f"Provider HTTP {exc.code}: {detail}") from exc
        except URLError as exc:
            raise LLMProviderError(f"Provider network error: {exc.reason}") from exc
        try:
            decoded = json.loads(body)
        except json.JSONDecodeError as exc:
            raise LLMProviderError("Provider response was not valid JSON") from exc
        if not isinstance(decoded, dict):
            raise LLMProviderError("Provider response root must be a JSON object")
        return decoded

    @staticmethod
    def _decode_structured_text(text: Any, provider: str) -> dict[str, Any]:
        if not isinstance(text, str) or not text.strip():
            raise LLMProviderError(f"{provider} returned empty structured output")
        try:
            value = json.loads(text)
        except json.JSONDecodeError as exc:
            raise StructuredOutputError(
                f"{provider} returned invalid JSON structured output: {exc.msg}"
            ) from exc
        if not isinstance(value, dict):
            raise StructuredOutputError(f"{provider} structured output must be a JSON object")
        return value


class OpenAILLMClient(_HTTPJSONClient, LLMClient):
    """OpenAI Responses API adapter using JSON Schema response formatting."""

    def request(
        self,
        system_prompt: str,
        user_content: str,
        schema: dict[str, Any],
    ) -> dict[str, Any]:
        schema_name = _schema_name(schema)
        payload = {
            "model": self.config.model,
            "instructions": system_prompt,
            "input": user_content,
            "text": {
                "format": {
                    "type": "json_schema",
                    "name": schema_name,
                    "schema": schema,
                    "strict": False,
                }
            },
        }
        response = self._send("responses", payload)
        if response.get("error"):
            raise LLMProviderError(f"OpenAI API error: {response['error']}")
        text = response.get("output_text")
        if not isinstance(text, str):
            text = _responses_output_text(response)
        return self._decode_structured_text(text, "OpenAI")


class DeepSeekLLMClient(_HTTPJSONClient, LLMClient):
    """DeepSeek Chat Completions adapter using JSON Output plus local validation."""

    def request(
        self,
        system_prompt: str,
        user_content: str,
        schema: dict[str, Any],
    ) -> dict[str, Any]:
        schema_instruction = json.dumps(schema, ensure_ascii=False, separators=(",", ":"))
        payload = {
            "model": self.config.model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        f"{system_prompt}\nReturn exactly one JSON object matching this JSON Schema; "
                        f"do not use Markdown fences:\n{schema_instruction}"
                    ),
                },
                {"role": "user", "content": user_content},
            ],
            "response_format": {"type": "json_object"},
            "max_tokens": 4096,
        }
        response = self._send("chat/completions", payload)
        if response.get("error"):
            raise LLMProviderError(f"DeepSeek API error: {response['error']}")
        try:
            text = response["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise LLMProviderError("DeepSeek response did not contain message content") from exc
        return self._decode_structured_text(text, "DeepSeek")


def create_llm_client(
    config: LLMProviderConfig | None = None,
    *,
    transport: Transport | None = None,
) -> LLMClient:
    resolved = config or LLMProviderConfig.from_env()
    if resolved.provider == "openai":
        return OpenAILLMClient(resolved, transport=transport)
    return DeepSeekLLMClient(resolved, transport=transport)


def llm_environment_diagnostics(
    environ: Mapping[str, str] | None = None,
) -> dict[str, str]:
    """Return only non-secret runtime configuration diagnostics."""
    source = _runtime_environment() if environ is None else environ
    api_key = str(source.get("FEM2D_AGENT_LLM_API_KEY", "")).strip()
    return {
        "provider": str(source.get("FEM2D_AGENT_LLM_PROVIDER", "")).strip(),
        "model": str(source.get("FEM2D_AGENT_LLM_MODEL", "")).strip(),
        "base_url": str(source.get("FEM2D_AGENT_LLM_BASE_URL", "")).strip(),
        "api_key": "configured" if api_key else "missing",
    }


def _runtime_environment() -> dict[str, str]:
    """Read environment at call time, with Windows User variables as fallback.

    GUI processes launched by an already-running desktop shell or IDE can inherit an
    older process environment even after User variables were persisted.  The registry
    fallback reads the same Windows User Environment without changing it.
    """
    source = dict(os.environ)
    if os.name != "nt":
        return source
    names = (
        "FEM2D_AGENT_LLM_PROVIDER",
        "FEM2D_AGENT_LLM_MODEL",
        "FEM2D_AGENT_LLM_API_KEY",
        "FEM2D_AGENT_LLM_BASE_URL",
        "FEM2D_AGENT_LLM_TIMEOUT_SECONDS",
    )
    missing = [name for name in names if not str(source.get(name, "")).strip()]
    if not missing:
        return source
    try:
        import winreg

        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as key:
            for name in missing:
                try:
                    value, _value_type = winreg.QueryValueEx(key, name)
                except FileNotFoundError:
                    continue
                if str(value).strip():
                    source[name] = str(value)
    except (OSError, ImportError):
        pass
    return source


def _schema_name(schema: dict[str, Any]) -> str:
    raw = str(schema.get("title", "structured_output"))
    normalized = re.sub(r"[^A-Za-z0-9_-]+", "_", raw).strip("_")
    return normalized[:64] or "structured_output"


def _responses_output_text(response: dict[str, Any]) -> str:
    for output in response.get("output", []):
        if not isinstance(output, dict):
            continue
        for content in output.get("content", []):
            if not isinstance(content, dict):
                continue
            if content.get("type") == "refusal":
                raise LLMProviderError(f"OpenAI refused the request: {content.get('refusal', '')}")
            if content.get("type") == "output_text" and isinstance(content.get("text"), str):
                return content["text"]
    raise LLMProviderError("OpenAI response did not contain output_text")
