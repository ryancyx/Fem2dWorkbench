import pytest

from core.engineering.geometry import GeometryModel
from core.meshing.rectangular_mesher import generate_rectangular_tri_mesh


def _build_mesh(nx: int = 2, ny: int = 1):
    geometry = GeometryModel.create_rectangle(width=2.0, height=1.0)
    return generate_rectangular_tri_mesh(geometry, nx=nx, ny=ny)


def _node_coordinates(mesh, node_ids):
    return [(mesh.get_node_by_id(node_id).x, mesh.get_node_by_id(node_id).y) for node_id in node_ids]


def test_rectangular_mesh_node_and_element_count():
    mesh = _build_mesh(nx=2, ny=1)

    assert len(mesh.nodes) == 6
    assert len(mesh.elements) == 4


def test_rectangular_mesh_boundary_node_mapping():
    nx = 2
    ny = 1
    mesh = _build_mesh(nx=nx, ny=ny)

    assert set(mesh.geometry_edge_to_mesh_node_ids) == {"bottom", "right", "top", "left"}
    assert len(mesh.geometry_edge_to_mesh_node_ids["bottom"]) == nx + 1
    assert len(mesh.geometry_edge_to_mesh_node_ids["top"]) == nx + 1
    assert len(mesh.geometry_edge_to_mesh_node_ids["left"]) == ny + 1
    assert len(mesh.geometry_edge_to_mesh_node_ids["right"]) == ny + 1


def test_rectangular_mesh_boundary_node_order():
    mesh = _build_mesh(nx=2, ny=1)

    bottom = _node_coordinates(mesh, mesh.geometry_edge_to_mesh_node_ids["bottom"])
    top = _node_coordinates(mesh, mesh.geometry_edge_to_mesh_node_ids["top"])
    left = _node_coordinates(mesh, mesh.geometry_edge_to_mesh_node_ids["left"])
    right = _node_coordinates(mesh, mesh.geometry_edge_to_mesh_node_ids["right"])

    assert all(y == 0.0 for _, y in bottom)
    assert [x for x, _ in bottom] == sorted(x for x, _ in bottom)
    assert all(y == 1.0 for _, y in top)
    assert [x for x, _ in top] == sorted(x for x, _ in top)
    assert all(x == 0.0 for x, _ in left)
    assert [y for _, y in left] == sorted(y for _, y in left)
    assert all(x == 2.0 for x, _ in right)
    assert [y for _, y in right] == sorted(y for _, y in right)


def test_rectangular_mesh_all_elements_are_cst_triangles():
    mesh = _build_mesh(nx=2, ny=1)

    assert all(element.element_type == "CST" for element in mesh.elements)
    assert all(len(element.node_ids) == 3 for element in mesh.elements)


def test_rectangular_mesh_triangle_area_is_positive():
    mesh = _build_mesh(nx=2, ny=1)

    for element in mesh.elements:
        n1, n2, n3 = [mesh.get_node_by_id(node_id) for node_id in element.node_ids]
        area = 0.5 * (
            (n2.x - n1.x) * (n3.y - n1.y)
            - (n3.x - n1.x) * (n2.y - n1.y)
        )
        assert area > 0.0


def test_rectangular_mesh_edge_to_element_edges_exist():
    mesh = _build_mesh(nx=2, ny=1)

    assert set(mesh.geometry_edge_to_mesh_element_edges) == {"bottom", "right", "top", "left"}
    assert len(mesh.geometry_edge_to_mesh_element_edges["bottom"]) == 2
    assert len(mesh.geometry_edge_to_mesh_element_edges["top"]) == 2
    assert len(mesh.geometry_edge_to_mesh_element_edges["left"]) == 1
    assert len(mesh.geometry_edge_to_mesh_element_edges["right"]) == 1

    for element_edges in mesh.geometry_edge_to_mesh_element_edges.values():
        for element_id, local_a, local_b in element_edges:
            assert mesh.get_element_by_id(element_id) is not None
            assert local_a in {0, 1, 2}
            assert local_b in {0, 1, 2}
            assert local_a != local_b


def test_rectangular_mesh_invalid_division_raises():
    geometry = GeometryModel.create_rectangle(width=2.0, height=1.0)

    with pytest.raises(ValueError):
        generate_rectangular_tri_mesh(geometry, nx=0, ny=1)
    with pytest.raises(ValueError):
        generate_rectangular_tri_mesh(geometry, nx=2, ny=0)
