import pytest

from core.compiler.project_to_fem import compile_project_to_fem
from core.engineering.analysis_step import AnalysisStep
from core.engineering.assembly import PartInstance
from core.engineering.boundary_condition_definition import BoundaryConditionDefinition
from core.engineering.engineering_project import EngineeringProject
from core.engineering.geometry import GeometryModel
from core.engineering.load_definition import LoadDefinition
from core.engineering.material_definition import MaterialDefinition
from core.engineering.part import Part
from core.engineering.section import SectionDefinition
from core.meshing.rectangular_mesher import generate_rectangular_tri_mesh


def build_stage4_reference_project_and_mesh(nx: int = 4, ny: int = 2):
    geometry = GeometryModel.create_rectangle(width=2.0, height=1.0)
    project = EngineeringProject(name="stage4_compile_demo")
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
    mesh = generate_rectangular_tri_mesh(geometry, nx=nx, ny=ny)
    return project, mesh


def test_compile_project_to_fem_basic_counts():
    project, mesh = build_stage4_reference_project_and_mesh()

    bundle = compile_project_to_fem(project, mesh, step_id="step_static")

    assert len(bundle.fem_model.nodes) == len(mesh.nodes)
    assert len(bundle.fem_model.elements) == len(mesh.elements)
    assert len(bundle.fem_model.materials) == 1


def test_compile_project_to_fem_section_material_mapping():
    project, mesh = build_stage4_reference_project_and_mesh()

    bundle = compile_project_to_fem(project, mesh, step_id="step_static")
    material = bundle.fem_model.materials[0]

    assert bundle.section_to_solver_material_id["sec_plate"] == 1
    assert material.young_modulus == 210e9
    assert material.poisson_ratio == 0.3
    assert material.thickness == 0.01


def test_compile_project_to_fem_boundary_condition_mapping():
    nx = 4
    ny = 2
    project, mesh = build_stage4_reference_project_and_mesh(nx=nx, ny=ny)

    bundle = compile_project_to_fem(project, mesh, step_id="step_static")
    left_node_ids = set(bundle.geometry_edge_to_fem_node_ids["left"])

    assert len(left_node_ids) == ny + 1
    assert len(bundle.fem_model.constraints) == len(left_node_ids)
    assert all(constraint.node_id in left_node_ids for constraint in bundle.fem_model.constraints)
    assert all(constraint.ux_fixed and constraint.uy_fixed for constraint in bundle.fem_model.constraints)


def test_compile_project_to_fem_edge_load_mapping():
    project, mesh = build_stage4_reference_project_and_mesh()

    bundle = compile_project_to_fem(project, mesh, step_id="step_static")
    right_node_ids = set(bundle.geometry_edge_to_fem_node_ids["right"])
    total_fy = sum(load.fy for load in bundle.fem_model.loads)

    assert bundle.fem_model.loads
    assert all(load.node_id in right_node_ids for load in bundle.fem_model.loads)
    assert total_fy == pytest.approx(-10.0)


def test_compile_project_to_fem_mapping_tables():
    project, mesh = build_stage4_reference_project_and_mesh()

    bundle = compile_project_to_fem(project, mesh, step_id="step_static")

    assert set(bundle.geometry_edge_to_fem_node_ids) == {"bottom", "right", "top", "left"}
    assert len(bundle.mesh_node_to_fem_node_id) == len(mesh.nodes)
    assert len(bundle.mesh_element_to_fem_element_id) == len(mesh.elements)


def test_compile_project_to_fem_invalid_step_raises():
    project, mesh = build_stage4_reference_project_and_mesh()

    with pytest.raises(ValueError):
        compile_project_to_fem(project, mesh, step_id="missing_step")
