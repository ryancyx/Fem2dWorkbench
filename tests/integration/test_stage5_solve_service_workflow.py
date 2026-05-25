import numpy as np

from services.solve_service import solve_workbench_project
from tests.unit.test_solve_service import build_reference_project


def test_stage5_solve_service_full_workflow():
    nx = 4
    ny = 2
    project = build_reference_project()

    solution = solve_workbench_project(
        project=project,
        part_id="part_rectangle",
        step_id="step_static",
        nx=nx,
        ny=ny,
    )

    n_nodes = (nx + 1) * (ny + 1)
    n_elements = 2 * nx * ny
    solver_result = solution.solver_result
    left_node_ids = solution.compiled_bundle.geometry_edge_to_fem_node_ids["left"]
    right_node_ids = solution.compiled_bundle.geometry_edge_to_fem_node_ids["right"]

    assert len(solution.mesh.nodes) == n_nodes
    assert len(solution.mesh.elements) == n_elements
    assert set(solution.compiled_bundle.geometry_edge_to_fem_node_ids) == {
        "bottom",
        "right",
        "top",
        "left",
    }
    assert solver_result.global_stiffness.shape == (2 * n_nodes, 2 * n_nodes)
    assert len(solver_result.node_displacements) == n_nodes
    assert len(solver_result.element_results) == n_elements

    for node_id in left_node_ids:
        ux, uy = solver_result.node_displacements[node_id]
        assert abs(ux) < 1e-12
        assert abs(uy) < 1e-12

    assert any(
        np.hypot(*solver_result.node_displacements[node_id]) > 0.0
        for node_id in right_node_ids
    )
    assert np.all(np.isfinite(solver_result.displacement))
