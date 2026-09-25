from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from agent.execution_result import ExecutionResult
from agent.review_models import ReviewResult
from agent.simulation_plan import SimulationPlan
from core.engineering.engineering_project import EngineeringProject
from core.engineering.mesh_model import MeshModel


class WorkflowStatus(StrEnum):
    IDLE = "IDLE"
    RUNNING = "RUNNING"
    WAITING_USER_INPUT = "WAITING_USER_INPUT"
    WAITING_APPROVAL = "WAITING_APPROVAL"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class WorkflowStage(StrEnum):
    ARCHITECT = "ARCHITECT"
    GEOMETRY = "GEOMETRY"
    MATERIAL = "MATERIAL"
    BC_LOAD = "BC_LOAD"
    MESH = "MESH"
    SOLVE = "SOLVE"
    REVIEW = "REVIEW"
    APPROVAL = "APPROVAL"
    RESULT = "RESULT"


@dataclass(slots=True)
class WorkflowState:
    user_input: str
    project: EngineeringProject
    simulation_plan: SimulationPlan | None = None
    current_stage: WorkflowStage = WorkflowStage.ARCHITECT
    status: WorkflowStatus = WorkflowStatus.IDLE
    execution_result: ExecutionResult | None = None
    review_result: ReviewResult | None = None
    current_mesh: MeshModel | None = None
    result_data: dict[str, Any] | None = None
    retry_count: int = 0
    max_retries: int = 2
    waiting_for_approval: bool = False

    def __post_init__(self) -> None:
        self.user_input = str(self.user_input)
        if not isinstance(self.project, EngineeringProject):
            raise ValueError("WorkflowState.project must be an EngineeringProject")
        self.current_stage = WorkflowStage(self.current_stage)
        self.status = WorkflowStatus(self.status)
        self.retry_count = int(self.retry_count)
        self.max_retries = int(self.max_retries)
        self.waiting_for_approval = bool(self.waiting_for_approval)
        if self.retry_count < 0:
            raise ValueError("retry_count must not be negative")
        if self.max_retries < 0:
            raise ValueError("max_retries must not be negative")
        if self.retry_count > self.max_retries:
            raise ValueError("retry_count must not exceed max_retries")
        if self.status == WorkflowStatus.WAITING_APPROVAL and not self.waiting_for_approval:
            raise ValueError("WAITING_APPROVAL requires waiting_for_approval=true")

    def transition(self, stage: WorkflowStage, status: WorkflowStatus | None = None) -> None:
        self.current_stage = WorkflowStage(stage)
        if status is not None:
            self.status = WorkflowStatus(status)
        self.waiting_for_approval = self.status == WorkflowStatus.WAITING_APPROVAL

    def to_dict(self) -> dict[str, Any]:
        return {
            "userInput": self.user_input,
            "simulationPlan": self.simulation_plan.to_dict() if self.simulation_plan else None,
            "project": self.project.to_dict(),
            "currentStage": self.current_stage.value,
            "status": self.status.value,
            "executionResult": (
                self.execution_result.to_dict(
                    include_solve_result=isinstance(self.execution_result.solve_result, dict)
                )
                if self.execution_result
                else None
            ),
            "reviewResult": self.review_result.to_dict() if self.review_result else None,
            "currentMesh": self.current_mesh.to_dict() if self.current_mesh else None,
            "resultData": self.result_data,
            "retryCount": self.retry_count,
            "maxRetries": self.max_retries,
            "waitingForApproval": self.waiting_for_approval,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "WorkflowState":
        if not isinstance(data, dict):
            raise ValueError("WorkflowState data must be a dictionary")
        plan_data = data.get("simulationPlan")
        execution_data = data.get("executionResult")
        review_data = data.get("reviewResult")
        mesh_data = data.get("currentMesh")
        return cls(
            user_input=str(data.get("userInput", "")),
            simulation_plan=SimulationPlan.from_dict(plan_data) if plan_data else None,
            project=EngineeringProject.from_dict(data["project"]),
            current_stage=WorkflowStage(data.get("currentStage", WorkflowStage.ARCHITECT)),
            status=WorkflowStatus(data.get("status", WorkflowStatus.IDLE)),
            execution_result=ExecutionResult.from_dict(execution_data) if execution_data else None,
            review_result=ReviewResult.from_dict(review_data) if review_data else None,
            current_mesh=MeshModel.from_dict(mesh_data) if mesh_data else None,
            result_data=data.get("resultData"),
            retry_count=int(data.get("retryCount", 0)),
            max_retries=int(data.get("maxRetries", 2)),
            waiting_for_approval=bool(data.get("waitingForApproval", False)),
        )
