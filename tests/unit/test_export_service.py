import csv

from services.export_service import (
    export_element_results_csv,
    export_node_displacements_csv,
    export_result_summary_txt,
)
from services.solve_service import solve_workbench_project
from tests.unit.test_solve_service import build_reference_project


def _build_solution():
    return solve_workbench_project(
        project=build_reference_project(),
        part_id="part_rectangle",
        step_id="step_static",
        nx=4,
        ny=2,
    )


def test_export_node_displacements_csv(tmp_path):
    solution = _build_solution()
    file_path = tmp_path / "node_displacements.csv"

    export_node_displacements_csv(solution, file_path)

    assert file_path.exists()
    with file_path.open(newline="", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        rows = list(reader)

    assert len(rows) == len(solution.mesh.nodes)
    assert set(["node_id", "x", "y", "ux", "uy", "u_magnitude"]).issubset(reader.fieldnames)


def test_export_element_results_csv(tmp_path):
    solution = _build_solution()
    file_path = tmp_path / "element_results.csv"

    export_element_results_csv(solution, file_path)

    assert file_path.exists()
    with file_path.open(newline="", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        rows = list(reader)

    assert len(rows) == len(solution.mesh.elements)
    assert set(
        [
            "element_id",
            "node_ids",
            "strain_x",
            "strain_y",
            "strain_xy",
            "stress_x",
            "stress_y",
            "stress_xy",
            "von_mises",
        ]
    ).issubset(reader.fieldnames)


def test_export_result_summary_txt(tmp_path):
    solution = _build_solution()
    file_path = tmp_path / "summary.txt"

    export_result_summary_txt(solution, file_path)

    assert file_path.exists()
    text = file_path.read_text(encoding="utf-8")
    assert "node_count" in text
    assert "element_count" in text
    assert "max_displacement" in text
    assert "max_von_mises" in text
