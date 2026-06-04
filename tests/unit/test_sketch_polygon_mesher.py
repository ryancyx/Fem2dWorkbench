import pytest

from core.engineering.geometry import GeometryEdge, GeometryFace, GeometryModel, GeometryPoint
from core.meshing.sketch_polygon_mesher import generate_sketch_tri_mesh
from services.sketch_geometry_service import (
    add_sketch_edge,
    add_sketch_point,
    build_single_face_from_edges,
    create_empty_sketch_geometry,
    create_geometry_from_polygon_points,
)


def _element_area(mesh, element):
    n1, n2, n3 = [mesh.get_node_by_id(node_id) for node_id in element.node_ids]

    return 0.5 * (
        (n2.x - n1.x) * (n3.y - n1.y)
        - (n3.x - n1.x) * (n2.y - n1.y)
    )


def _assert_all_element_areas_are_positive(mesh):
    for element in mesh.elements:
        assert _element_area(mesh, element) > 0.0


def test_triangle_sketch_generates_single_cst_element():
    geometry = create_geometry_from_polygon_points(
        [
            (0.0, 0.0),
            (2.0, 0.0),
            (1.0, 1.0),
        ]
    )

    mesh = generate_sketch_tri_mesh(geometry)

    assert len(mesh.nodes) == 3
    assert len(mesh.elements) == 1
    assert all(element.element_type == "CST" for element in mesh.elements)
    assert all(element.source_face_id == "f1" for element in mesh.elements)
    _assert_all_element_areas_are_positive(mesh)


def test_quad_sketch_generates_two_cst_elements():
    geometry = create_geometry_from_polygon_points(
        [
            (0.0, 0.0),
            (2.0, 0.0),
            (2.0, 1.0),
            (0.0, 1.0),
        ]
    )

    mesh = generate_sketch_tri_mesh(geometry)

    assert len(mesh.nodes) == 4
    assert len(mesh.elements) == 2
    assert all(len(element.node_ids) == 3 for element in mesh.elements)
    _assert_all_element_areas_are_positive(mesh)


def test_pentagon_sketch_generates_three_cst_elements():
    geometry = create_geometry_from_polygon_points(
        [
            (0.0, 0.0),
            (2.0, 0.0),
            (2.5, 1.0),
            (1.0, 2.0),
            (-0.5, 1.0),
        ]
    )

    mesh = generate_sketch_tri_mesh(geometry)

    assert len(mesh.nodes) == 5
    assert len(mesh.elements) == 3
    _assert_all_element_areas_are_positive(mesh)


def test_concave_simple_polygon_can_be_triangulated():
    geometry = create_geometry_from_polygon_points(
        [
            (0.0, 0.0),
            (2.0, 0.0),
            (2.0, 1.0),
            (1.0, 0.5),
            (0.0, 1.0),
        ]
    )

    mesh = generate_sketch_tri_mesh(geometry)

    assert len(mesh.nodes) == 5
    assert len(mesh.elements) == 3
    _assert_all_element_areas_are_positive(mesh)


def test_clockwise_polygon_is_reordered_to_positive_area_elements():
    geometry = create_geometry_from_polygon_points(
        [
            (0.0, 0.0),
            (0.0, 1.0),
            (2.0, 1.0),
            (2.0, 0.0),
        ]
    )

    mesh = generate_sketch_tri_mesh(geometry)

    assert len(mesh.nodes) == 4
    assert len(mesh.elements) == 2
    _assert_all_element_areas_are_positive(mesh)


def test_mesh_nodes_keep_polygon_coordinates():
    geometry = create_geometry_from_polygon_points(
        [
            (0.0, 0.0),
            (2.0, 0.0),
            (2.0, 1.0),
            (0.0, 1.0),
        ]
    )

    mesh = generate_sketch_tri_mesh(geometry)

    mesh_coordinates = {(node.x, node.y) for node in mesh.nodes}

    assert mesh_coordinates == {
        (0.0, 0.0),
        (2.0, 0.0),
        (2.0, 1.0),
        (0.0, 1.0),
    }


def test_geometry_edge_to_mesh_node_mapping_is_created():
    geometry = create_geometry_from_polygon_points(
        [
            (0.0, 0.0),
            (2.0, 0.0),
            (2.0, 1.0),
            (0.0, 1.0),
        ]
    )

    mesh = generate_sketch_tri_mesh(geometry)

    assert set(mesh.geometry_edge_to_mesh_node_ids) == {"e1", "e2", "e3", "e4"}

    for node_ids in mesh.geometry_edge_to_mesh_node_ids.values():
        assert len(node_ids) == 2
        assert all(mesh.get_node_by_id(node_id) is not None for node_id in node_ids)


def test_geometry_edge_to_mesh_element_edge_mapping_is_created():
    geometry = create_geometry_from_polygon_points(
        [
            (0.0, 0.0),
            (2.0, 0.0),
            (2.0, 1.0),
            (0.0, 1.0),
        ]
    )

    mesh = generate_sketch_tri_mesh(geometry)

    assert set(mesh.geometry_edge_to_mesh_element_edges) == {"e1", "e2", "e3", "e4"}

    for element_edges in mesh.geometry_edge_to_mesh_element_edges.values():
        assert len(element_edges) >= 1
        for element_id, local_a, local_b in element_edges:
            assert mesh.get_element_by_id(element_id) is not None
            assert local_a in {0, 1, 2}
            assert local_b in {0, 1, 2}
            assert local_a != local_b


def test_sketch_without_face_cannot_generate_mesh():
    geometry = create_empty_sketch_geometry()
    add_sketch_point(geometry, 0.0, 0.0)
    add_sketch_point(geometry, 1.0, 0.0)
    add_sketch_point(geometry, 0.0, 1.0)
    add_sketch_edge(geometry, "p1", "p2")
    add_sketch_edge(geometry, "p2", "p3")

    with pytest.raises(ValueError):
        generate_sketch_tri_mesh(geometry)


def test_open_face_edges_cannot_generate_mesh():
    geometry = GeometryModel(
        points=[
            GeometryPoint(id="p1", x=0.0, y=0.0),
            GeometryPoint(id="p2", x=1.0, y=0.0),
            GeometryPoint(id="p3", x=0.0, y=1.0),
        ],
        edges=[
            GeometryEdge(id="e1", start_point_id="p1", end_point_id="p2"),
            GeometryEdge(id="e2", start_point_id="p2", end_point_id="p3"),
        ],
        faces=[
            GeometryFace(id="f1", edge_ids=["e1", "e2"]),
        ],
    )

    with pytest.raises(ValueError):
        generate_sketch_tri_mesh(geometry)


def test_multiple_faces_are_rejected():
    geometry = create_geometry_from_polygon_points(
        [
            (0.0, 0.0),
            (2.0, 0.0),
            (1.0, 1.0),
        ]
    )
    geometry.faces.append(GeometryFace(id="f2", edge_ids=["e1", "e2", "e3"]))

    with pytest.raises(ValueError):
        generate_sketch_tri_mesh(geometry)


def test_manual_triangle_from_sketch_service_can_generate_mesh():
    geometry = create_empty_sketch_geometry()

    add_sketch_point(geometry, 0.0, 0.0)
    add_sketch_point(geometry, 2.0, 0.0)
    add_sketch_point(geometry, 1.0, 1.0)

    add_sketch_edge(geometry, "p1", "p2")
    add_sketch_edge(geometry, "p2", "p3")
    add_sketch_edge(geometry, "p3", "p1")

    build_single_face_from_edges(geometry)

    mesh = generate_sketch_tri_mesh(geometry)

    assert len(mesh.nodes) == 3
    assert len(mesh.elements) == 1
    _assert_all_element_areas_are_positive(mesh)