from __future__ import annotations

from agent.architect_agent import ArchitectAgent
from agent.bc_load_agent import BCLoadAgent
from agent.geometry_agent import GeometryAgent
from agent.llm_client import LLMClient
from agent.llm_providers import LLMProviderConfig, create_llm_client
from agent.material_agent import MaterialAgent
from agent.reviewer_agent import ReviewerAgent
from agent.workflow_orchestrator import WorkflowOrchestrator
from core.engineering.engineering_project import EngineeringProject


def create_agent_workflow(
    project: EngineeringProject,
    *,
    config: LLMProviderConfig | None = None,
    llm_client: LLMClient | None = None,
    max_retries: int = 2,
) -> WorkflowOrchestrator:
    """Build the shared real GUI/E2E Agent workflow dependency graph."""
    client = llm_client or create_llm_client(config)
    return WorkflowOrchestrator(
        project=project,
        architect_agent=ArchitectAgent(client),
        geometry_agent=GeometryAgent(client),
        material_agent=MaterialAgent(client),
        bc_load_agent=BCLoadAgent(client),
        reviewer_agent=ReviewerAgent(client),
        max_retries=max_retries,
    )
