import math

from services.result_service import (
    build_element_result_rows,
    build_node_displacement_rows,
    build_result_summary,
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


def test_build_node_displacement_rows():
    solution = _build_solution()

    rows = build_node_displacement_rows(solution)

    assert len(rows) == len(solution.mesh.nodes)
    for row in rows:
        assert row.node_id is not None
        assert row.x is not None
        assert row.y is not None
        assert row.ux is not None
        assert row.uy is not None
        assert row.u_magnitude == math.hypot(row.ux, row.uy)


def test_build_element_result_rows():
    solution = _build_solution()

    rows = build_element_result_rows(solution)

    assert len(rows) == len(solution.mesh.elements)
    for row in rows:
        assert row.element_id is not None
        assert row.node_ids
        assert row.strain_x is not None
        assert row.strain_y is not None
        assert row.strain_xy is not None
        assert row.stress_x is not None
        assert row.stress_y is not None
        assert row.stress_xy is not None
        assert row.von_mises >= 0.0


def test_build_result_summary():
    solution = _build_solution()

    summary = build_result_summary(solution)

    assert summary.node_count == len(solution.mesh.nodes)
    assert summary.element_count == len(solution.mesh.elements)
    assert summary.max_displacement >= 0.0
    assert summary.max_displacement_node_id is not None
    assert summary.max_von_mises >= 0.0
    assert summary.max_von_mises_element_id is not None
    assert summary.warning_count == len(solution.warnings)
