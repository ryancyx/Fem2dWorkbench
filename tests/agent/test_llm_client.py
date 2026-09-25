from __future__ import annotations

from typing import Any

from agent.llm_client import LLMClient


class FakeLLMClient:
    def __init__(self, response: dict[str, Any]) -> None:
        self.response = response
        self.requests: list[tuple[str, str, dict[str, Any]]] = []

    def request(
        self,
        system_prompt: str,
        user_content: str,
        schema: dict[str, Any],
    ) -> dict[str, Any]:
        self.requests.append((system_prompt, user_content, schema))
        return self.response


def test_fake_llm_client_satisfies_provider_agnostic_protocol() -> None:
    client = FakeLLMClient({"ok": True})

    response = client.request("system", "user", {"type": "object"})

    assert isinstance(client, LLMClient)
    assert response == {"ok": True}
    assert len(client.requests) == 1
