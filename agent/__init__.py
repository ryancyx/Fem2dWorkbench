"""LLM-driven workflow layer for Fem2dWorkbench.

The package is additive: engineering state and deterministic FEM operations remain
owned by the existing ``core`` and ``services`` packages.
"""

from agent.execution_result import ExecutionResult
from agent.bc_load_agent import BCLoadAgent
from agent.architect_agent import ArchitectAgent
from agent.geometry_agent import GeometryAgent
from agent.llm_client import LLMClient, StructuredOutputError
from agent.llm_providers import (
    DeepSeekLLMClient,
    LLMConfigurationError,
    LLMProviderConfig,
    LLMProviderError,
    OpenAILLMClient,
    create_llm_client,
    llm_environment_diagnostics,
)
from agent.workflow_factory import create_agent_workflow
from agent.material_agent import MaterialAgent
from agent.reviewer_agent import ReviewerAgent
from agent.review_models import RepairProposal, ReviewResult
from agent.simulation_plan import SimulationPlan
from agent.workflow_state import WorkflowStage, WorkflowState, WorkflowStatus
from agent.workflow_orchestrator import WorkflowOrchestrator

__all__ = [
    "ExecutionResult",
    "BCLoadAgent",
    "ArchitectAgent",
    "GeometryAgent",
    "LLMClient",
    "LLMConfigurationError",
    "LLMProviderConfig",
    "LLMProviderError",
    "OpenAILLMClient",
    "DeepSeekLLMClient",
    "create_llm_client",
    "llm_environment_diagnostics",
    "create_agent_workflow",
    "MaterialAgent",
    "ReviewerAgent",
    "RepairProposal",
    "ReviewResult",
    "SimulationPlan",
    "StructuredOutputError",
    "WorkflowStage",
    "WorkflowState",
    "WorkflowStatus",
    "WorkflowOrchestrator",
]
