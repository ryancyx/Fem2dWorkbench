from __future__ import annotations

from dataclasses import dataclass, field

from core.compiler.compiled_bundle import CompiledFemBundle
from core.engineering.engineering_project import EngineeringProject
from core.engineering.mesh_model import MeshModel
from core.solver.solver import SolverResult
from core.solver.solver_api import solve_static_linear
from services.compile_service import compile_workbench_project
from services.mesh_service import generate_mesh_for_part


@dataclass(slots=True)
class WorkbenchSolveResult:
    project: EngineeringProject
    mesh: MeshModel
    compiled_bundle: CompiledFemBundle
    solver_result: SolverResult
    warnings: list[str] = field(default_factory=list)


def solve_workbench_project(
    project: EngineeringProject,
    part_id: str,
    step_id: str,
    nx: int,
    ny: int,
) -> WorkbenchSolveResult:
    mesh = generate_mesh_for_part(project=project, part_id=part_id, nx=nx, ny=ny)
    compiled_bundle = compile_workbench_project(project=project, mesh=mesh, step_id=step_id)
    solver_result = solve_static_linear(compiled_bundle.fem_model)

    return WorkbenchSolveResult(
        project=project,
        mesh=mesh,
        compiled_bundle=compiled_bundle,
        solver_result=solver_result,
        warnings=list(compiled_bundle.warnings),
    )
