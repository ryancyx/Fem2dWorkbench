from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


class StructuredOutputError(ValueError):
    """Raised when an LLM response does not satisfy the requested structure."""


@runtime_checkable
class LLMClient(Protocol):
    """Provider-agnostic interface implemented by external LLM API adapters.

    Agent code depends only on this protocol. Stage 5 adapters implement it in
    a separate provider module; ordinary tests continue to supply fake clients.
    """

    def request(
        self,
        system_prompt: str,
        user_content: str,
        schema: dict[str, Any],
    ) -> dict[str, Any]:
        """Return schema-constrained structured output from an external LLM."""
        ...
