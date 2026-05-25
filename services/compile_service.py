from __future__ import annotations

from core.compiler.compiled_bundle import CompiledFemBundle
from core.compiler.project_to_fem import compile_project_to_fem
from core.engineering.engineering_project import EngineeringProject
from core.engineering.mesh_model import MeshModel


def compile_workbench_project(
    project: EngineeringProject,
    mesh: MeshModel,
    step_id: str,
) -> CompiledFemBundle:
    return compile_project_to_fem(project=project, mesh=mesh, step_id=step_id)
