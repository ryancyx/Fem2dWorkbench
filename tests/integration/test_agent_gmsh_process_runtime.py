from __future__ import annotations

import pytest

from core.engineering.geometry import GeometryModel
from ui.backend.agent_mesh_runtime import generate_agent_mesh_isolated


def test_agent_gmsh_runs_in_isolated_process_main_thread() -> None:
    pytest.importorskip("gmsh", reason="Agent mesh process integration requires gmsh")

    mesh = generate_agent_mesh_isolated(
        GeometryModel.create_rectangle(2.0, 1.0),
        target_size=0.35,
    )

    assert mesh.nodes
    assert mesh.elements
    assert {"bottom", "right", "top", "left"}.issubset(
        mesh.geometry_edge_to_mesh_node_ids
    )
