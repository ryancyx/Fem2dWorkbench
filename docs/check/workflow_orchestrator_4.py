from __future__ import annotations

from collections.abc import Callable
from typing import Any

from agent.architect_agent import ArchitectAgent
from agent.bc_load_agent import BCLoadAgent
from agent.execution_result import ExecutionResult
from agent.geometry_agent import GeometryAgent
from agent.material_agent import MaterialAgent
from agent.reviewer_agent import ReviewerAgent
from agent.workflow_state import WorkflowStage, WorkflowState, WorkflowStatus
from core.engineering.engineering_project import EngineeringProject
from core.engineering.mesh_model import MeshModel
from core.meshing.quality_sketch_mesher import generate_quality_sketch_tri_mesh
from core.solver.solver_api import solve_static_linear
from services.compile_service import compile_workbench_project
from services.result_service import (
    build_displacement_contour_data,
    build_element_result_rows,
    build_node_displacement_rows,
    build_result_summary,
    build_stress_contour_data,
)
from services.solve_service import WorkbenchSolveResult


MeshGenerator = Callable[..., MeshModel]
Compiler = Callable[..., Any]
Solver = Callable[[Any], Any]
ResultBuilder = Callable[[WorkbenchSolveResult, str], dict[str, Any]]


class WorkflowOrchestrator:
    def __init__(
        self,
        project: EngineeringProject,
        architect_agent: ArchitectAgent,
        geometry_agent: GeometryAgent,
        material_agent: MaterialAgent,
        bc_load_agent: BCLoadAgent,
        *,
        reviewer_agent: ReviewerAgent | None = None,
        mesh_generator: MeshGenerator = generate_quality_sketch_tri_mesh,
        compiler: Compiler = compile_workbench_project,
        solver: Solver = solve_static_linear,
        result_builder: ResultBuilder | None = None,
        result_callback: Callable[[dict[str, Any]], None] | None = None,
        max_retries: int = 2,
    ) -> None:
        self.architect_agent = architect_agent
        self.geometry_agent = geometry_agent
        self.material_agent = material_agent
        self.bc_load_agent = bc_load_agent
        self.reviewer_agent = reviewer_agent
        self.mesh_generator = mesh_generator
        self.compiler = compiler
        self.solver = solver
        self.result_builder = result_builder or self._build_result_data
        self.result_callback = result_callback
        self._approval_granted = False
        self.state = WorkflowState(
            user_input="",
            project=project,
            current_stage=WorkflowStage.ARCHITECT,
            status=WorkflowStatus.IDLE,
            max_retries=max_retries,
        )

    def start(self, user_input: str) -> WorkflowState:
        if not str(user_input).strip():
            raise ValueError("user_input must not be empty")
        previous_plan = self.state.simulation_plan
        revising_existing_plan = (
            self.state.status == WorkflowStatus.WAITING_USER_INPUT
            and previous_plan is not None
        )
        self.state.user_input = str(user_input)
        self.state.status = WorkflowStatus.RUNNING
        self.state.current_stage = WorkflowStage.ARCHITECT
        self.state.execution_result = None
        self.state.review_result = None
        self.state.waiting_for_approval = False
        try:
            if revising_existing_plan:
                new_plan = self.architect_agent.revise_plan(
                    user_input, previous_plan, self.state.project
                )
            else:
                new_plan = self.architect_agent.create_plan(
                    user_input, self.state.project
                )
        except Exception as exc:
            self.state.execution_result = ExecutionResult.failed(WorkflowStage.ARCHITECT.value, exc)
            self.state.current_stage = WorkflowStage.ARCHITECT
            self.state.status = WorkflowStatus.WAITING_USER_INPUT
            return self.state
        if previous_plan is not None and new_plan.geometry != previous_plan.geometry:
            self.bc_load_agent.clear_managed_definitions(self.state.project)
        self.state.simulation_plan = new_plan
        self.state.retry_count = 0
        self.state.current_mesh = None
        self.state.result_data = None
        self.state.current_stage = WorkflowStage.GEOMETRY
        return self.execute_plan()

    def execute_plan(self) -> WorkflowState:
        while self.state.status == WorkflowStatus.RUNNING:
            if self.state.current_stage == WorkflowStage.APPROVAL:
                break
            if self.state.current_stage == WorkflowStage.REVIEW and self.reviewer_agent is None:
                break
            self.execute_current_stage()
        return self.state

    def execute_current_stage(self) -> WorkflowState:
        plan = self.state.simulation_plan
        if plan is None:
            self._stop_with_failure(WorkflowStage.ARCHITECT, ValueError("No SimulationPlan exists"))
            return self.state
        stage = self.state.current_stage
        try:
            if stage == WorkflowStage.GEOMETRY:
                self.geometry_agent.create(plan, self.state.project)
                self.state.current_stage = WorkflowStage.MATERIAL
            elif stage == WorkflowStage.MATERIAL:
                self.material_agent.apply(plan, self.state.project)
                self.state.current_stage = WorkflowStage.BC_LOAD
            elif stage == WorkflowStage.BC_LOAD:
                self.bc_load_agent.apply(plan, self.state.project)
                self.state.current_stage = WorkflowStage.MESH
            elif stage == WorkflowStage.MESH:
                part = self._active_part()
                self.state.current_mesh = self.mesh_generator(
                    part.geometry,
                    target_size=plan.mesh_size,
                    max_area=None,
                    min_angle=25.0,
                )
                self.state.current_stage = WorkflowStage.SOLVE
            elif stage == WorkflowStage.SOLVE:
                self._execute_solve(plan.requested_result)
                self.state.current_stage = WorkflowStage.RESULT
            elif stage == WorkflowStage.REVIEW:
                if self.reviewer_agent is None:
                    return self.state
                execution_result = self.state.execution_result
                if execution_result is None:
                    raise ValueError("Cannot review without an ExecutionResult")
                review_result = self.reviewer_agent.review(
                    plan,
                    self.state.project,
                    execution_result,
                )
                self.state.review_result = review_result
                if review_result.has_problem:
                    self.state.transition(
                        WorkflowStage.APPROVAL,
                        WorkflowStatus.WAITING_APPROVAL,
                    )
                else:
                    self.state.transition(
                        WorkflowStage.REVIEW,
                        WorkflowStatus.WAITING_USER_INPUT,
                    )
            elif stage == WorkflowStage.RESULT:
                self.state.status = WorkflowStatus.COMPLETED
                if self.result_callback and self.state.result_data is not None:
                    self.result_callback(self.state.result_data)
            else:
                raise ValueError(f"Stage {stage.value} cannot be executed in Stage 3")
        except Exception as exc:
            if stage in {
                WorkflowStage.GEOMETRY,
                WorkflowStage.MATERIAL,
                WorkflowStage.BC_LOAD,
                WorkflowStage.MESH,
                WorkflowStage.SOLVE,
            }:
                self.state.execution_result = ExecutionResult.failed(
                    stage.value,
                    exc,
                    solve_result=self._execution_diagnostics(),
                )
                self.state.current_stage = WorkflowStage.REVIEW
                self.state.status = WorkflowStatus.RUNNING
            elif stage == WorkflowStage.REVIEW:
                self.state.current_stage = WorkflowStage.REVIEW
                self.state.status = WorkflowStatus.FAILED
                self.state.waiting_for_approval = False
            else:
                self._stop_with_failure(stage, exc)
        return self.state

    def handle_approval(
        self,
        confirm: bool,
        proposal_index: int | None = None,
    ) -> WorkflowState:
        if (
            self.state.status != WorkflowStatus.WAITING_APPROVAL
            or self.state.current_stage != WorkflowStage.APPROVAL
            or not self.state.waiting_for_approval
        ):
            raise ValueError("Workflow is not waiting for Human Approval")
        review_result = self.state.review_result
        plan = self.state.simulation_plan
        if review_result is None or plan is None:
            raise ValueError("Approval requires a SimulationPlan and ReviewResult")
        if not confirm:
            self.state.transition(
                WorkflowStage.ARCHITECT,
                WorkflowStatus.WAITING_USER_INPUT,
            )
            return self.state
        if self.state.retry_count >= self.state.max_retries:
            self.state.transition(WorkflowStage.APPROVAL, WorkflowStatus.FAILED)
            return self.state
        proposals = review_result.proposals
        if proposal_index is None:
            if len(proposals) != 1:
                raise ValueError("proposal_index is required unless exactly one proposal exists")
            proposal_index = 0
        if proposal_index < 0 or proposal_index >= len(proposals):
            raise IndexError("proposal_index is out of range")
        repaired_plan = plan.apply_repair(proposals[proposal_index])
        geometry_changed = repaired_plan.geometry != plan.geometry
        if geometry_changed:
            self.bc_load_agent.clear_managed_definitions(self.state.project)
            self.state.project.validate_references()
        self.state.simulation_plan = repaired_plan
        self._approval_granted = True
        try:
            return self.retry()
        finally:
            self._approval_granted = False

    def retry(self) -> WorkflowState:
        if not self._approval_granted:
            raise ValueError("retry requires a confirmed Human Approval")
        if self.state.simulation_plan is None:
            raise ValueError("Cannot retry without a SimulationPlan")
        if self.state.retry_count >= self.state.max_retries:
            self.state.transition(self.state.current_stage, WorkflowStatus.FAILED)
            return self.state
        self.state.retry_count += 1
        self.state.current_mesh = None
        self.state.result_data = None
        self.state.execution_result = None
        self.state.transition(WorkflowStage.GEOMETRY, WorkflowStatus.RUNNING)
        return self.execute_plan()

    def _execute_solve(self, requested_result: str) -> None:
        mesh = self.state.current_mesh
        if mesh is None:
            raise ValueError("Cannot solve before a mesh has been generated")
        step_id = self._step_id()
        compiled_bundle = self.compiler(
            project=self.state.project,
            mesh=mesh,
            step_id=step_id,
        )
        solver_result = self.solver(compiled_bundle.fem_model)
        solution = WorkbenchSolveResult(
            project=self.state.project,
            mesh=mesh,
            compiled_bundle=compiled_bundle,
            solver_result=solver_result,
            warnings=list(getattr(compiled_bundle, "warnings", [])),
        )
        self.state.execution_result = ExecutionResult.succeeded("SOLVE", solution)
        self.state.result_data = self.result_builder(solution, requested_result)

    def _active_part(self):
        part_id = str(self.state.project.metadata.get("active_part_id", ""))
        part = self.state.project.get_part_by_id(part_id) if part_id else None
        if part is None and len(self.state.project.parts) == 1:
            part = self.state.project.parts[0]
        if part is None:
            raise ValueError("The project has no unambiguous active part")
        return part

    def _step_id(self) -> str:
        if not self.state.project.analysis_steps:
            raise ValueError("The project has no analysis step")
        return self.state.project.analysis_steps[0].id

    def _stop_with_failure(self, stage: WorkflowStage, error: BaseException) -> None:
        self.state.execution_result = ExecutionResult.failed(stage.value, error)
        self.state.current_stage = stage
        self.state.status = WorkflowStatus.FAILED

    def _execution_diagnostics(self) -> dict[str, Any]:
        mesh = self.state.current_mesh
        return {
            "mesh": {
                "exists": mesh is not None,
                "nodeCount": len(mesh.nodes) if mesh is not None else 0,
                "elementCount": len(mesh.elements) if mesh is not None else 0,
            }
        }

    @staticmethod
    def _build_result_data(
        solution: WorkbenchSolveResult,
        requested_result: str,
    ) -> dict[str, Any]:
        return {
            "requestedResult": requested_result,
            "summary": build_result_summary(solution).to_dict(),
            "nodeRows": [row.to_dict() for row in build_node_displacement_rows(solution)],
            "elementRows": [row.to_dict() for row in build_element_result_rows(solution)],
            "displacementContour": build_displacement_contour_data(solution),
            "stressContour": build_stress_contour_data(solution),
        }

    def executePlan(self) -> WorkflowState:
        return self.execute_plan()

    def executeCurrentStage(self) -> WorkflowState:
        return self.execute_current_stage()

    def handleApproval(
        self,
        confirm: bool,
        proposalIndex: int | None = None,
    ) -> WorkflowState:
        return self.handle_approval(confirm, proposalIndex)
