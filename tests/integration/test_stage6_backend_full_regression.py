import csv
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
from services.export_service import (
    export_element_results_csv,
    export_node_displacements_csv,
    export_result_summary_txt,
)
from services.result_service import (
    build_element_result_rows,
    build_node_displacement_rows,
    build_result_summary,
)
from services.session_service import WorkbenchSession
from services.solve_service import WorkbenchSolveResult, solve_workbench_project


def build_stage6_full_regression_project() -> EngineeringProject:
    """
    截至阶段 6 的完整后端回归测试工程。

    该工程覆盖：
    - 工程层字符串 ID
    - 矩形几何
    - 矩形结构化 CST 网格
    - 工程到 FEM 编译
    - 线性静力求解
    - 结果整理
    - CSV/TXT 导出
    """

    project = EngineeringProject(name="stage6_full_backend_regression_demo")

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


def build_stage6_solution(nx: int = 4, ny: int = 2) -> WorkbenchSolveResult:
    project = build_stage6_full_regression_project()

    return solve_workbench_project(
        project=project,
        part_id="part_rectangle",
        step_id="step_static",
        nx=nx,
        ny=ny,
    )


def read_csv_rows(file_path):
    with open(file_path, "r", encoding="utf-8", newline="") as file:
        return list(csv.DictReader(file))


def test_stage6_full_backend_pipeline_solution_tables_and_summary():
    nx = 4
    ny = 2
    solution = build_stage6_solution(nx=nx, ny=ny)

    assert isinstance(solution, WorkbenchSolveResult)

    mesh = solution.mesh
    bundle = solution.compiled_bundle
    solver_result = solution.solver_result

    n_nodes = (nx + 1) * (ny + 1)
    n_elements = 2 * nx * ny

    assert len(mesh.nodes) == n_nodes
    assert len(mesh.elements) == n_elements

    assert len(bundle.fem_model.nodes) == n_nodes
    assert len(bundle.fem_model.elements) == n_elements
    assert len(bundle.fem_model.materials) == 1

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

    assert solver_result.global_stiffness.shape == (2 * n_nodes, 2 * n_nodes)
    assert solver_result.global_load.shape == (2 * n_nodes,)
    assert solver_result.constrained_stiffness.shape == (2 * n_nodes, 2 * n_nodes)
    assert solver_result.constrained_load.shape == (2 * n_nodes,)
    assert solver_result.displacement.shape == (2 * n_nodes,)

    assert np.all(np.isfinite(solver_result.global_stiffness))
    assert np.all(np.isfinite(solver_result.global_load))
    assert np.all(np.isfinite(solver_result.constrained_stiffness))
    assert np.all(np.isfinite(solver_result.constrained_load))
    assert np.all(np.isfinite(solver_result.displacement))

    assert len(solver_result.node_displacements) == n_nodes
    assert len(solver_result.element_results) == n_elements

    node_rows = build_node_displacement_rows(solution)
    element_rows = build_element_result_rows(solution)
    summary = build_result_summary(solution)

    assert len(node_rows) == n_nodes
    assert len(element_rows) == n_elements

    assert summary.node_count == n_nodes
    assert summary.element_count == n_elements
    assert summary.max_displacement > 0.0
    assert summary.max_displacement_node_id is not None
    assert summary.max_von_mises >= 0.0
    assert summary.max_von_mises_element_id is not None
    assert summary.warning_count == len(solution.warnings)

    left_node_ids = bundle.geometry_edge_to_fem_node_ids["left"]
    right_node_ids = bundle.geometry_edge_to_fem_node_ids["right"]

    for node_id in left_node_ids:
        ux, uy = solver_result.node_displacements[node_id]

        assert math.isclose(ux, 0.0, abs_tol=1e-12)
        assert math.isclose(uy, 0.0, abs_tol=1e-12)

    right_displacement_norms = []
    for node_id in right_node_ids:
        ux, uy = solver_result.node_displacements[node_id]
        right_displacement_norms.append(math.hypot(ux, uy))

    assert max(right_displacement_norms) > 0.0

    total_fx = sum(load.fx for load in bundle.fem_model.loads)
    total_fy = sum(load.fy for load in bundle.fem_model.loads)

    assert math.isclose(total_fx, 0.0, abs_tol=1e-10)

    # right 边长度 height = 1.0, thickness = 0.01, qy = -1000
    # 等效总力 = qy * height * thickness = -10.0
    assert math.isclose(total_fy, -10.0, rel_tol=1e-10, abs_tol=1e-10)


def test_stage6_full_backend_pipeline_export_files_are_readable(tmp_path):
    solution = build_stage6_solution(nx=4, ny=2)

    output_dir = tmp_path / "stage6_exports"
    node_csv = output_dir / "node_displacements.csv"
    element_csv = output_dir / "element_results.csv"
    summary_txt = output_dir / "summary.txt"

    export_node_displacements_csv(solution, node_csv)
    export_element_results_csv(solution, element_csv)
    export_result_summary_txt(solution, summary_txt)

    assert node_csv.exists()
    assert element_csv.exists()
    assert summary_txt.exists()

    node_rows = read_csv_rows(node_csv)
    element_rows = read_csv_rows(element_csv)

    assert len(node_rows) == len(solution.mesh.nodes)
    assert len(element_rows) == len(solution.mesh.elements)

    assert {
        "node_id",
        "x",
        "y",
        "ux",
        "uy",
        "u_magnitude",
    }.issubset(node_rows[0].keys())

    assert {
        "element_id",
        "node_ids",
        "strain_x",
        "strain_y",
        "strain_xy",
        "stress_x",
        "stress_y",
        "stress_xy",
        "von_mises",
    }.issubset(element_rows[0].keys())

    max_node_displacement_from_csv = max(
        float(row["u_magnitude"])
        for row in node_rows
    )
    max_element_von_mises_from_csv = max(
        float(row["von_mises"])
        for row in element_rows
    )

    summary = build_result_summary(solution)

    assert math.isclose(
        max_node_displacement_from_csv,
        summary.max_displacement,
        rel_tol=1e-9,
        abs_tol=1e-18,
    )

    assert math.isclose(
        max_element_von_mises_from_csv,
        summary.max_von_mises,
        rel_tol=1e-9,
        abs_tol=1e-9,
    )

    summary_text = summary_txt.read_text(encoding="utf-8")

    assert "node_count" in summary_text
    assert "element_count" in summary_text
    assert "max_displacement" in summary_text
    assert "max_von_mises" in summary_text
    assert str(summary.node_count) in summary_text
    assert str(summary.element_count) in summary_text


def test_stage6_full_backend_pipeline_session_lifecycle():
    project = build_stage6_full_regression_project()
    solution = solve_workbench_project(
        project=project,
        part_id="part_rectangle",
        step_id="step_static",
        nx=4,
        ny=2,
    )

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

    session.set_solution(solution)

    assert session.has_project() is True
    assert session.has_solution() is True
    assert session.current_project is solution.project
    assert session.current_mesh is solution.mesh
    assert session.current_bundle is solution.compiled_bundle
    assert session.current_solver_result is solution.solver_result
    assert session.warnings == solution.warnings

    session.clear_results()

    assert session.has_project() is True
    assert session.has_solution() is False
    assert session.current_project is solution.project
    assert session.current_mesh is None
    assert session.current_bundle is None
    assert session.current_solver_result is None
    assert session.warnings == []