import csv

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
from services.solve_service import solve_workbench_project
from tests.unit.test_solve_service import build_reference_project


def test_stage6_result_export_workflow(tmp_path):
    nx = 4
    ny = 2
    solution = solve_workbench_project(
        project=build_reference_project(),
        part_id="part_rectangle",
        step_id="step_static",
        nx=nx,
        ny=ny,
    )

    node_rows = build_node_displacement_rows(solution)
    element_rows = build_element_result_rows(solution)
    summary = build_result_summary(solution)

    node_count = (nx + 1) * (ny + 1)
    element_count = 2 * nx * ny
    assert solution.solver_result is not None
    assert len(node_rows) == node_count
    assert len(element_rows) == element_count
    assert summary.node_count == node_count
    assert summary.element_count == element_count
    assert summary.max_displacement > 0.0
    assert summary.max_von_mises >= 0.0

    node_csv = tmp_path / "node_displacements.csv"
    element_csv = tmp_path / "element_results.csv"
    summary_txt = tmp_path / "summary.txt"
    export_node_displacements_csv(solution, node_csv)
    export_element_results_csv(solution, element_csv)
    export_result_summary_txt(solution, summary_txt)

    assert node_csv.exists()
    assert element_csv.exists()
    assert summary_txt.exists()

    with node_csv.open(newline="", encoding="utf-8") as file:
        node_reader = csv.DictReader(file)
        node_csv_rows = list(node_reader)
    with element_csv.open(newline="", encoding="utf-8") as file:
        element_reader = csv.DictReader(file)
        element_csv_rows = list(element_reader)

    assert len(node_csv_rows) == node_count
    assert len(element_csv_rows) == element_count
