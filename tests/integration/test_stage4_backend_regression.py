import math

import numpy as np

from core.engineering.analysis_step import AnalysisStep
from core.engineering.boundary_condition_definition import BoundaryConditionDefinition
from core.engineering.engineering_project import EngineeringProject
from core.engineering.geometry import GeometryModel
from core.engineering.load_definition import LoadDefinition
from core.engineering.material_definition import MaterialDefinition
from core.engineering.part import Part
from core.engineering.section import SectionDefinition
from core.io.project_json import load_project_from_json, save_project_to_json
from core.meshing.rectangular_mesher import generate_rectangular_tri_mesh
from core.compiler.project_to_fem import compile_project_to_fem
from core.solver.solver_api import solve_static_linear


def build_stage4_regression_project() -> EngineeringProject:
    """
    阶段 4 截止后端回归算例。

    工程对象使用字符串 ID；
    网格层和 FEM 层仍由 mesher/compiler 生成整数 ID。

    几何：
        width = 2.0
        height = 1.0

    属性：
        E = 210e9
        nu = 0.3
        thickness = 0.01

    边界条件：
        left 边 ux/uy 固定

    载荷：
        right 边 qy = -1000.0

    理论等效总力：
        total_fy = qy * height * thickness
                 = -1000.0 * 1.0 * 0.01
                 = -10.0
    """
    project = EngineeringProject(name="stage4_backend_regression_demo")

    project.add_material(
        MaterialDefinition(
            id="mat_steel",
            name="steel",
            young_modulus=210e9,
            poisson_ratio=0.3,
            color="#8FB7D8",
        )
    )

    project.add_section(
        SectionDefinition(
            id="sec_plate",
            name="steel_plate_section",
            material_id="mat_steel",
            thickness=0.01,
            plane_mode="stress",
        )
    )

    geometry = GeometryModel.create_rectangle(
        width=2.0,
        height=1.0,
        origin_x=0.0,
        origin_y=0.0,
    )

    project.add_part(
        Part(
            id="part_rectangle",
            name="rectangle_plate",
            geometry=geometry,
            section_id="sec_plate",
        )
    )

    project.add_analysis_step(
        AnalysisStep(
            id="step_static",
            name="static_step",
            step_type="static_linear",
        )
    )

    project.add_boundary_condition(
        BoundaryConditionDefinition(
            id="bc_fix_left",
            name="fix_left_edge",
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
            name="right_edge_downward_uniform_load",
            step_id="step_static",
            target_type="geometry_edge",
            target_id="right",
            qx=0.0,
            qy=-1000.0,
            load_type="edge_uniform",
        )
    )

    project.validate_references()
    return project


def build_stage4_bundle(nx: int = 4, ny: int = 2):
    project = build_stage4_regression_project()
    part = project.get_part_by_id("part_rectangle")

    assert part is not None

    mesh = generate_rectangular_tri_mesh(
        geometry=part.geometry,
        nx=nx,
        ny=ny,
    )

    bundle = compile_project_to_fem(
        project=project,
        mesh=mesh,
        step_id="step_static",
    )

    return project, mesh, bundle


def test_stage4_backend_compile_mapping_load_and_constraint_regression():
    nx = 4
    ny = 2
    project, mesh, bundle = build_stage4_bundle(nx=nx, ny=ny)

    fem_model = bundle.fem_model

    assert bundle.step_id == "step_static"

    assert len(fem_model.nodes) == len(mesh.nodes)
    assert len(fem_model.elements) == len(mesh.elements)
    assert len(fem_model.materials) == 1

    assert len(bundle.mesh_node_to_fem_node_id) == len(mesh.nodes)
    assert len(bundle.mesh_element_to_fem_element_id) == len(mesh.elements)

    assert set(bundle.geometry_edge_to_fem_node_ids.keys()) == {
        "bottom",
        "right",
        "top",
        "left",
    }

    assert set(bundle.geometry_edge_to_fem_element_edges.keys()) == {
        "bottom",
        "right",
        "top",
        "left",
    }

    assert bundle.section_to_solver_material_id["sec_plate"] == 1

    material = fem_model.materials[0]
    assert material.id == 1
    assert material.name == "steel"
    assert math.isclose(material.young_modulus, 210e9)
    assert math.isclose(material.poisson_ratio, 0.3)
    assert math.isclose(material.thickness, 0.01)
    assert material.plane_mode == "stress"

    for node in fem_model.nodes:
        assert isinstance(node.id, int)

    for element in fem_model.elements:
        assert isinstance(element.id, int)
        assert all(isinstance(node_id, int) for node_id in element.node_ids)
        assert element.material_id == 1
        assert element.element_type == "CST"

    left_fem_node_ids = set(bundle.geometry_edge_to_fem_node_ids["left"])
    right_fem_node_ids = set(bundle.geometry_edge_to_fem_node_ids["right"])

    assert len(left_fem_node_ids) == ny + 1
    assert len(right_fem_node_ids) == ny + 1

    assert len(fem_model.constraints) == len(left_fem_node_ids)

    for constraint in fem_model.constraints:
        assert constraint.node_id in left_fem_node_ids
        assert constraint.ux_fixed is True
        assert constraint.uy_fixed is True
        assert math.isclose(constraint.ux_value, 0.0)
        assert math.isclose(constraint.uy_value, 0.0)

    assert len(fem_model.loads) > 0

    for load in fem_model.loads:
        assert load.node_id in right_fem_node_ids

    total_fx = sum(load.fx for load in fem_model.loads)
    total_fy = sum(load.fy for load in fem_model.loads)

    assert math.isclose(total_fx, 0.0, abs_tol=1e-10)
    assert math.isclose(total_fy, -10.0, rel_tol=1e-10, abs_tol=1e-10)


def test_stage4_backend_json_mesh_compile_and_solve_regression(tmp_path):
    """
    阶段 4 截止完整后端链路测试：

    EngineeringProject
        -> JSON 保存/读取
        -> MeshModel
        -> CompiledFemBundle
        -> FEMModel
        -> solve_static_linear()

    这个测试不涉及 UI 和服务层。
    """
    project = build_stage4_regression_project()

    file_path = tmp_path / "stage4_backend_regression_demo.f2dw.json"
    save_project_to_json(project, file_path)

    restored_project = load_project_from_json(file_path)
    restored_project.validate_references()

    assert restored_project.to_dict() == project.to_dict()

    part = restored_project.get_part_by_id("part_rectangle")
    assert part is not None

    nx = 4
    ny = 2

    mesh = generate_rectangular_tri_mesh(
        geometry=part.geometry,
        nx=nx,
        ny=ny,
    )

    bundle = compile_project_to_fem(
        project=restored_project,
        mesh=mesh,
        step_id="step_static",
    )

    result = solve_static_linear(bundle.fem_model)

    n_nodes = len(mesh.nodes)
    n_elements = len(mesh.elements)

    assert result.global_stiffness.shape == (2 * n_nodes, 2 * n_nodes)
    assert result.global_load.shape == (2 * n_nodes,)
    assert result.constrained_stiffness.shape == (2 * n_nodes, 2 * n_nodes)
    assert result.constrained_load.shape == (2 * n_nodes,)
    assert result.displacement.shape == (2 * n_nodes,)

    assert len(result.node_displacements) == n_nodes
    assert len(result.element_results) == n_elements

    assert np.all(np.isfinite(result.global_stiffness))
    assert np.all(np.isfinite(result.global_load))
    assert np.all(np.isfinite(result.constrained_stiffness))
    assert np.all(np.isfinite(result.constrained_load))
    assert np.all(np.isfinite(result.displacement))

    left_fem_node_ids = bundle.geometry_edge_to_fem_node_ids["left"]
    right_fem_node_ids = bundle.geometry_edge_to_fem_node_ids["right"]

    for node_id in left_fem_node_ids:
        ux, uy = result.node_displacements[node_id]

        assert math.isclose(ux, 0.0, abs_tol=1e-12)
        assert math.isclose(uy, 0.0, abs_tol=1e-12)

    right_displacement_norms = []
    for node_id in right_fem_node_ids:
        ux, uy = result.node_displacements[node_id]
        right_displacement_norms.append(math.hypot(ux, uy))

    assert max(right_displacement_norms) > 0.0


def test_stage4_backend_rejects_missing_step_id():
    project = build_stage4_regression_project()
    part = project.get_part_by_id("part_rectangle")

    assert part is not None

    mesh = generate_rectangular_tri_mesh(
        geometry=part.geometry,
        nx=4,
        ny=2,
    )

    try:
        compile_project_to_fem(
            project=project,
            mesh=mesh,
            step_id="missing_step",
        )
    except ValueError as exc:
        assert "missing_step" in str(exc)
    else:
        raise AssertionError("compile_project_to_fem() should reject missing step_id")