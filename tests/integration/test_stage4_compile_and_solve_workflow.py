import numpy as np

from core.compiler.project_to_fem import compile_project_to_fem
from core.solver.solver_api import solve_static_linear
from tests.unit.test_compile_project_to_fem import build_stage4_reference_project_and_mesh


def test_stage4_compile_and_solve_static_rectangle_case():
    project, mesh = build_stage4_reference_project_and_mesh(nx=4, ny=2)

    bundle = compile_project_to_fem(project, mesh, step_id="step_static")
    result = solve_static_linear(bundle.fem_model)

    n_nodes = len(mesh.nodes)
    right_node_ids = bundle.geometry_edge_to_fem_node_ids["right"]

    assert np.all(np.isfinite(result.displacement))
    assert len(result.node_displacements) == len(mesh.nodes)
    assert len(result.element_results) == len(mesh.elements)
    assert result.global_stiffness.shape == (2 * n_nodes, 2 * n_nodes)
    assert any(
        abs(result.node_displacements[node_id][0]) > 0.0
        or abs(result.node_displacements[node_id][1]) > 0.0
        for node_id in right_node_ids
    )
