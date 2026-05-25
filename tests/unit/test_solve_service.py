import numpy as np
import pytest

from core.engineering.analysis_step import AnalysisStep
from core.engineering.assembly import PartInstance
from core.engineering.boundary_condition_definition import BoundaryConditionDefinition
from core.engineering.engineering_project import EngineeringProject
from core.engineering.geometry import GeometryModel
from core.engineering.load_definition import LoadDefinition
from core.engineering.material_definition import MaterialDefinition
from core.engineering.part import Part
from core.engineering.section import SectionDefinition
from services.compile_service import compile_workbench_project
from services.mesh_service import generate_mesh_for_part
from services.session_service import WorkbenchSession
from services.solve_service import WorkbenchSolveResult, solve_workbench_project


def build_reference_project() -> EngineeringProject:
    geometry = GeometryModel.create_rectangle(width=2.0, height=1.0)
    project = EngineeringProject(name="stage5_service_demo")

    project.add_material(
        MaterialDefinition(
            id="mat_steel",
            name="steel",
            young_modulus=210e9,
            poisson_ratio=0.3,
        )
    )
    project.add_section(
        SectionDefinition(
            id="sec_plate",
            name="Plate section",
            material_id="mat_steel",
            thickness=0.01,
            plane_mode="stress",
        )
    )
    project.add_part(
        Part(
            id="part_rectangle",
            name="Rectangle",
            geometry=geometry,
            section_id="sec_plate",
        )
    )
    project.assembly.instances.append(
        PartInstance(
            id="inst_rectangle",
            name="Rectangle instance",
            part_id="part_rectangle",
        )
    )
    project.add_analysis_step(
        AnalysisStep(
            id="step_static",
            name="Static step",
            step_type="static_linear",
        )
    )
    project.add_boundary_condition(
        BoundaryConditionDefinition(
            id="bc_fix_left",
            name="Fix left edge",
            step_id="step_static",
            target_type="geometry_edge",
            target_id="left",
            ux_fixed=True,
            uy_fixed=True,
        )
    )
    project.add_load(
        LoadDefinition(
            id="load_right_down",
            name="Right edge downward load",
            step_id="step_static",
            target_type="geometry_edge",
            target_id="right",
            load_type="edge_uniform",
            qy=-1000.0,
        )
    )

    return project


def test_generate_mesh_for_part_returns_mesh():
    project = build_reference_project()

    mesh = generate_mesh_for_part(project, "part_rectangle", nx=4, ny=2)

    assert len(mesh.nodes) == 15
    assert len(mesh.elements) == 16


def test_generate_mesh_for_missing_part_raises():
    project = build_reference_project()

    with pytest.raises(ValueError, match="missing_part"):
        generate_mesh_for_part(project, "missing_part", nx=4, ny=2)


def test_compile_workbench_project_returns_bundle():
    project = build_reference_project()
    mesh = generate_mesh_for_part(project, "part_rectangle", nx=4, ny=2)

    bundle = compile_workbench_project(project, mesh, step_id="step_static")

    assert bundle.fem_model is not None
    assert len(bundle.fem_model.nodes) == len(mesh.nodes)
    assert len(bundle.fem_model.elements) == len(mesh.elements)


def test_solve_workbench_project_returns_solution():
    project = build_reference_project()

    solution = solve_workbench_project(
        project=project,
        part_id="part_rectangle",
        step_id="step_static",
        nx=4,
        ny=2,
    )

    assert isinstance(solution, WorkbenchSolveResult)
    assert solution.mesh is not None
    assert solution.compiled_bundle is not None
    assert solution.solver_result is not None
    assert np.all(np.isfinite(solution.solver_result.displacement))
    assert len(solution.solver_result.node_displacements) == len(solution.mesh.nodes)
    assert len(solution.solver_result.element_results) == len(solution.mesh.elements)


def test_workbench_session_state_lifecycle():
    project = build_reference_project()
    session = WorkbenchSession()

    assert not session.has_project()
    assert not session.has_solution()

    session.set_project(project)
    assert session.has_project()
    assert not session.has_solution()

    solution = solve_workbench_project(
        project=project,
        part_id="part_rectangle",
        step_id="step_static",
        nx=4,
        ny=2,
    )
    session.set_solution(solution)
    assert session.has_solution()

    session.clear_results()
    assert session.has_project()
    assert not session.has_solution()
