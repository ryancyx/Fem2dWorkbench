from __future__ import annotations

from core.engineering.mesh_model import MeshElement, MeshModel, MeshNode
from services.result_query_service import format_result_query_text, query_result_at_point
from services.result_service import ElementResultRow, NodeDisplacementRow


def _build_rows():
    mesh = MeshModel(
        nodes=[
            MeshNode(id=1, x=0.0, y=0.0),
            MeshNode(id=2, x=2.0, y=0.0),
            MeshNode(id=3, x=2.0, y=1.0),
            MeshNode(id=4, x=0.0, y=1.0),
        ],
        elements=[
            MeshElement(id=1, node_ids=[1, 2, 3]),
            MeshElement(id=2, node_ids=[1, 3, 4]),
        ],
    )
    node_rows = [
        NodeDisplacementRow(node_id=1, x=0.0, y=0.0, ux=0.0, uy=0.0, u_magnitude=0.0),
        NodeDisplacementRow(node_id=2, x=2.0, y=0.0, ux=1.0e-3, uy=0.0, u_magnitude=1.0e-3),
        NodeDisplacementRow(node_id=3, x=2.0, y=1.0, ux=1.1e-3, uy=-2.0e-3, u_magnitude=2.2825424421026653e-3),
        NodeDisplacementRow(node_id=4, x=0.0, y=1.0, ux=0.0, uy=-1.8e-3, u_magnitude=1.8e-3),
    ]
    element_rows = [
        ElementResultRow(
            element_id=1,
            node_ids=[1, 2, 3],
            strain_x=0.0,
            strain_y=0.0,
            strain_xy=0.0,
            stress_x=10.0,
            stress_y=20.0,
            stress_xy=5.0,
            von_mises=18.0,
        ),
        ElementResultRow(
            element_id=2,
            node_ids=[1, 3, 4],
            strain_x=0.0,
            strain_y=0.0,
            strain_xy=0.0,
            stress_x=12.0,
            stress_y=15.0,
            stress_xy=4.0,
            von_mises=17.0,
        ),
    ]
    return mesh, node_rows, element_rows


def test_query_result_at_point_inside_triangle():
    mesh, node_rows, element_rows = _build_rows()

    result = query_result_at_point(mesh, node_rows, element_rows, 1.5, 0.25)

    assert result.inside_element is True
    assert result.containing_element_id == 1
    assert result.nearest_node_id == 2
    assert result.von_mises == 18.0


def test_query_result_at_point_outside_mesh_returns_nearest_node():
    mesh, node_rows, element_rows = _build_rows()

    result = query_result_at_point(mesh, node_rows, element_rows, 3.0, 2.0)

    assert result.inside_element is False
    assert result.containing_element_id is None
    assert result.nearest_node_id == 3
    text = format_result_query_text(result)
    assert "最近节点" in text
    assert "未命中三角形" in text
