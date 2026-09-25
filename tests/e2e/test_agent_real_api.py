from __future__ import annotations

import os

import pytest

from agent.llm_providers import create_llm_client


RUN_REAL_API = os.environ.get("FEM2D_AGENT_RUN_REAL_API") == "1"
pytestmark = pytest.mark.skipif(
    not RUN_REAL_API,
    reason="Set FEM2D_AGENT_RUN_REAL_API=1 with provider credentials to run real API tests",
)


def test_configured_real_provider_structured_output_smoke() -> None:
    client = create_llm_client()
    schema = {
        "title": "ProviderSmoke",
        "type": "object",
        "additionalProperties": False,
        "required": ["status"],
        "properties": {"status": {"type": "string", "enum": ["ok"]}},
    }

    result = client.request(
        "Return JSON only through the requested structured-output schema.",
        "Return status ok.",
        schema,
    )

    assert result == {"status": "ok"}
