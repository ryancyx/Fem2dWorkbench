from __future__ import annotations

import pytest

from services.sketch_geometry_service import (
    add_sketch_edge,
    add_sketch_point,
    build_single_face_from_edges,
    can_build_single_closed_face,
    clear_sketch_geometry,
    create_empty_sketch_geometry,
    create_geometry_from_polygon_points,
    delete_sketch_point,
    get_sketch_edges,
    get_sketch_faces,
    get_sketch_points,
    move_sketch_point,
)


def test_create_empty_sketch_geometry():
    geometry = create_empty_sketch_geometry()

    assert geometry.points == []
    assert geometry.edges == []
    assert geometry.faces == []


def test_add_move_delete_sketch_point():
    geometry = create_empty_sketch_geometry()

    add_sketch_point(geometry, 0.0, 0.0)
    move_sketch_point(geometry, "p1", 1.0, 2.0)

    points = get_sketch_points(geometry)
    assert points == [{"id": "p1", "x": 1.0, "y": 2.0}]

    delete_sketch_point(geometry, "p1")
    assert get_sketch_points(geometry) == []


def test_add_sketch_edge_between_existing_points():
    geometry = create_empty_sketch_geometry()
    add_sketch_point(geometry, 0.0, 0.0)
    add_sketch_point(geometry, 1.0, 0.0)

    add_sketch_edge(geometry, "p1", "p2")

    assert get_sketch_edges(geometry) == [
        {"id": "e1", "start_point_id": "p1", "end_point_id": "p2"}
    ]


def test_add_sketch_edge_rejects_missing_point():
    geometry = create_empty_sketch_geometry()
    add_sketch_point(geometry, 0.0, 0.0)

    with pytest.raises(ValueError):
        add_sketch_edge(geometry, "p1", "missing")


def test_add_sketch_edge_rejects_duplicate_edge():
    geometry = create_empty_sketch_geometry()
    add_sketch_point(geometry, 0.0, 0.0)
    add_sketch_point(geometry, 1.0, 0.0)
    add_sketch_edge(geometry, "p1", "p2")

    with pytest.raises(ValueError):
        add_sketch_edge(geometry, "p2", "p1")


def test_triangle_can_build_face():
    geometry = create_geometry_from_polygon_points([(0.0, 0.0), (1.0, 0.0), (0.5, 1.0)])

    assert can_build_single_closed_face(geometry) is True
    assert len(get_sketch_faces(geometry)) == 1


def test_open_chain_cannot_build_face():
    geometry = create_empty_sketch_geometry()
    add_sketch_point(geometry, 0.0, 0.0)
    add_sketch_point(geometry, 1.0, 0.0)
    add_sketch_point(geometry, 1.0, 1.0)
    add_sketch_edge(geometry, "p1", "p2")
    add_sketch_edge(geometry, "p2", "p3")

    assert can_build_single_closed_face(geometry) is False
    with pytest.raises(ValueError):
        build_single_face_from_edges(geometry)


def test_create_geometry_from_polygon_points_builds_face():
    geometry = create_geometry_from_polygon_points(
        [(0.0, 0.0), (2.0, 0.0), (2.0, 1.0), (0.0, 1.0)]
    )

    assert len(get_sketch_points(geometry)) == 4
    assert len(get_sketch_edges(geometry)) == 4
    assert len(get_sketch_faces(geometry)) == 1


def test_delete_point_clears_related_edges_and_faces():
    geometry = create_geometry_from_polygon_points([(0.0, 0.0), (1.0, 0.0), (0.5, 1.0)])

    delete_sketch_point(geometry, "p1")

    assert len(get_sketch_points(geometry)) == 2
    assert all(
        edge["start_point_id"] != "p1" and edge["end_point_id"] != "p1"
        for edge in get_sketch_edges(geometry)
    )
    assert get_sketch_faces(geometry) == []


def test_clear_sketch_geometry():
    geometry = create_geometry_from_polygon_points([(0.0, 0.0), (1.0, 0.0), (0.5, 1.0)])

    clear_sketch_geometry(geometry)

    assert get_sketch_points(geometry) == []
    assert get_sketch_edges(geometry) == []
    assert get_sketch_faces(geometry) == []
