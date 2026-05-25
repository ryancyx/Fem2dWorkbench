import math

import numpy as np
import pytest

from core.engineering.analysis_step import AnalysisStep
from core.engineering.boundary_condition_definition import BoundaryConditionDefinition
from core.engineering.engineering_project import EngineeringProject
from core.engineering.geometry import GeometryModel
from core.engineering.load_definition import LoadDefinition
from core.engineering.material_definition import MaterialDefinition
from core.engineering.part import Part
from core.engineering.section import SectionDefinition
from core.io.project_json import load_project_from_json, save_project_to_json
from services.solve_service import WorkbenchSolveResult, solve_workbench_project
from services.session_service import WorkbenchSession


def build_stage5_regression_project() -> EngineeringProject:
    """
    阶段 5 截止后端回归算例。

    目标：
    - 工程层使用字符串 ID；
    - 通过 solve_workbench_project() 一键完成：
      part 查找 -> 网格生成 -> FEM 编译 -> 求解；
    - 不直接调用 mesher/compiler/solver，验证 service 层封装可用。

    几何：
        width = 2.0
        height = 1.0

    网格：
        测试中使用 nx = 4, ny = 2

    材料：
        E = 210e9
        nu = 0.3

    属性：
        thickness = 0.01
        plane_mode = "stress"

    边界：
        left 边 ux/uy 固定

    载荷：
        right 边 qy = -1000.0

    理论总等效力：
        total_fy = qy * height * thickness
                 = -1000.0 * 1.0 * 0.01
                 = -10.0
    """
    project = EngineeringProject(name="stage5_backend_regression_demo")

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


def test_stage5_backend_json_to_solve_service_regression(tmp_path):
    """
    阶段 5 截止完整服务层回归测试：

    EngineeringProject
        -> JSON 保存/读取
        -> solve_workbench_project()
        -> WorkbenchSolveResult

    这里刻意不直接调用：
    - generate_rectangular_tri_mesh()
    - compile_project_to_fem()
    - solve_static_linear()

    因为阶段 5 要验证 services 层已经把这些流程封装好。
    """
    project = build_stage5_regression_project()

    file_path = tmp_path / "stage5_backend_regression_demo.f2dw.json"
    save_project_to_json(project, file_path)

    restored_project = load_project_from_json(file_path)
    restored_project.validate_references()

    assert restored_project.to_dict() == project.to_dict()

    nx = 4
    ny = 2

    solution = solve_workbench_project(
        project=restored_project,
        part_id="part_rectangle",
        step_id="step_static",
        nx=nx,
        ny=ny,
    )

    assert isinstance(solution, WorkbenchSolveResult)
    assert solution.project is restored_project
    assert solution.mesh is not None
    assert solution.compiled_bundle is not None
    assert solution.solver_result is not None
    assert isinstance(solution.warnings, list)

    mesh = solution.mesh
    bundle = solution.compiled_bundle
    fem_model = bundle.fem_model
    solver_result = solution.solver_result

    n_nodes = (nx + 1) * (ny + 1)
    n_elements = 2 * nx * ny

    assert len(mesh.nodes) == n_nodes
    assert len(mesh.elements) == n_elements

    assert len(fem_model.nodes) == n_nodes
    assert len(fem_model.elements) == n_elements
    assert len(fem_model.materials) == 1

    assert bundle.step_id == "step_static"

    assert len(bundle.mesh_node_to_fem_node_id) == n_nodes
    assert len(bundle.mesh_element_to_fem_element_id) == n_elements

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

    left_node_ids = set(bundle.geometry_edge_to_fem_node_ids["left"])
    right_node_ids = set(bundle.geometry_edge_to_fem_node_ids["right"])

    assert len(left_node_ids) == ny + 1
    assert len(right_node_ids) == ny + 1

    assert len(fem_model.constraints) == len(left_node_ids)

    for constraint in fem_model.constraints:
        assert constraint.node_id in left_node_ids
        assert constraint.ux_fixed is True
        assert constraint.uy_fixed is True
        assert math.isclose(constraint.ux_value, 0.0)
        assert math.isclose(constraint.uy_value, 0.0)

    assert len(fem_model.loads) > 0

    for load in fem_model.loads:
        assert load.node_id in right_node_ids

    total_fx = sum(load.fx for load in fem_model.loads)
    total_fy = sum(load.fy for load in fem_model.loads)

    assert math.isclose(total_fx, 0.0, abs_tol=1e-10)
    assert math.isclose(total_fy, -10.0, rel_tol=1e-10, abs_tol=1e-10)

    assert solver_result.global_stiffness.shape == (2 * n_nodes, 2 * n_nodes)
    assert solver_result.global_load.shape == (2 * n_nodes,)
    assert solver_result.constrained_stiffness.shape == (2 * n_nodes, 2 * n_nodes)
    assert solver_result.constrained_load.shape == (2 * n_nodes,)
    assert solver_result.displacement.shape == (2 * n_nodes,)

    assert len(solver_result.node_displacements) == n_nodes
    assert len(solver_result.element_results) == n_elements

    assert np.all(np.isfinite(solver_result.global_stiffness))
    assert np.all(np.isfinite(solver_result.global_load))
    assert np.all(np.isfinite(solver_result.constrained_stiffness))
    assert np.all(np.isfinite(solver_result.constrained_load))
    assert np.all(np.isfinite(solver_result.displacement))

    for node_id in left_node_ids:
        ux, uy = solver_result.node_displacements[node_id]

        assert math.isclose(ux, 0.0, abs_tol=1e-12)
        assert math.isclose(uy, 0.0, abs_tol=1e-12)

    right_displacement_norms = []
    for node_id in right_node_ids:
        ux, uy = solver_result.node_displacements[node_id]
        right_displacement_norms.append(math.hypot(ux, uy))

    assert max(right_displacement_norms) > 0.0


def test_stage5_workbench_session_lifecycle_regression():
    """
    验证阶段 5 的轻量会话状态对象可用。

    WorkbenchSession 不负责保存文件、不负责 UI 通知、不负责重新求解；
    它只保存当前 project / mesh / bundle / solver_result。
    """
    project = build_stage5_regression_project()

    session = WorkbenchSession()

    assert session.has_project() is False
    assert session.has_solution() is False

    session.set_project(project)

    assert session.has_project() is True
    assert session.has_solution() is False
    assert session.current_project is project
    assert session.current_mesh is None
    assert session.current_bundle is None
    assert session.current_solver_result is None

    solution = solve_workbench_project(
        project=project,
        part_id="part_rectangle",
        step_id="step_static",
        nx=4,
        ny=2,
    )

    session.set_solution(solution)

    assert session.has_project() is True
    assert session.has_solution() is True
    assert session.current_project is project
    assert session.current_mesh is solution.mesh
    assert session.current_bundle is solution.compiled_bundle
    assert session.current_solver_result is solution.solver_result
    assert session.warnings == solution.warnings

    session.clear_results()

    assert session.has_project() is True
    assert session.has_solution() is False
    assert session.current_project is project
    assert session.current_mesh is None
    assert session.current_bundle is None
    assert session.current_solver_result is None
    assert session.warnings == []


def test_stage5_solve_service_rejects_missing_part_id():
    project = build_stage5_regression_project()

    with pytest.raises(ValueError) as exc_info:
        solve_workbench_project(
            project=project,
            part_id="missing_part",
            step_id="step_static",
            nx=4,
            ny=2,
        )

    assert "missing_part" in str(exc_info.value)


def test_stage5_solve_service_rejects_missing_step_id():
    project = build_stage5_regression_project()

    with pytest.raises(ValueError) as exc_info:
        solve_workbench_project(
            project=project,
            part_id="part_rectangle",
            step_id="missing_step",
            nx=4,
            ny=2,
        )

    assert "missing_step" in str(exc_info.value)


def test_stage5_solve_service_rejects_invalid_mesh_division():
    project = build_stage5_regression_project()

    with pytest.raises(ValueError):
        solve_workbench_project(
            project=project,
            part_id="part_rectangle",
            step_id="step_static",
            nx=0,
            ny=2,
        )

    with pytest.raises(ValueError):
        solve_workbench_project(
            project=project,
            part_id="part_rectangle",
            step_id="step_static",
            nx=4,
            ny=0,
        )