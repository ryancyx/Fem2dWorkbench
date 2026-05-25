from __future__ import annotations

from dataclasses import dataclass, field

from core.compiler.compiled_bundle import CompiledFemBundle
from core.engineering.engineering_project import EngineeringProject
from core.engineering.mesh_model import MeshModel
from core.solver.solver import SolverResult
from services.solve_service import WorkbenchSolveResult


@dataclass(slots=True)
class WorkbenchSession:
    current_project: EngineeringProject | None = None
    current_mesh: MeshModel | None = None
    current_bundle: CompiledFemBundle | None = None
    current_solver_result: SolverResult | None = None
    warnings: list[str] = field(default_factory=list)

    def set_project(self, project: EngineeringProject) -> None:
        self.current_project = project
        self.clear_results()

    def set_solution(self, solution: WorkbenchSolveResult) -> None:
        self.current_project = solution.project
        self.current_mesh = solution.mesh
        self.current_bundle = solution.compiled_bundle
        self.current_solver_result = solution.solver_result
        self.warnings = list(solution.warnings)

    def clear_results(self) -> None:
        self.current_mesh = None
        self.current_bundle = None
        self.current_solver_result = None
        self.warnings = []

    def has_project(self) -> bool:
        return self.current_project is not None

    def has_solution(self) -> bool:
        return (
            self.current_mesh is not None
            and self.current_bundle is not None
            and self.current_solver_result is not None
        )
