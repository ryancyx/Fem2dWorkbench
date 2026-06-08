from __future__ import annotations

import pytest

from services.sketch_geometry_service import (
    add_sketch_edge,
    add_sketch_point,
    build_faces_from_edges,
    create_empty_sketch_geometry,
)


def _point_ids(geometry) -> list[str]:
    return [point.id for point in geometry.points]


def test_stage18_polygonize_two_rectangles_with_shared_edge() -> None:
    geometry = create_empty_sketch_geometry()
    for x, y in ((0.0, 0.0), (1.0, 0.0), (2.0, 0.0), (0.0, 1.0), (1.0, 1.0), (2.0, 1.0)):
        add_sketch_point(geometry, x, y)
    p1, p2, p3, p4, p5, p6 = _point_ids(geometry)
    for start_id, end_id in (
        (p1, p2),
        (p2, p5),
        (p5, p4),
        (p4, p1),
        (p2, p3),
        (p3, p6),
        (p6, p5),
    ):
        add_sketch_edge(geometry, start_id, end_id)

    build_faces_from_edges(geometry)

    assert len(geometry.faces) == 2
    shared_edge_id = next(edge.id for edge in geometry.edges if {edge.start_point_id, edge.end_point_id} == {p2, p5})
    assert sum(shared_edge_id in face.edge_ids for face in geometry.faces) == 2


def test_stage18_polygonize_two_rectangles_sharing_one_point() -> None:
    geometry = create_empty_sketch_geometry()
    for x, y in (
        (0.0, 0.0),
        (1.0, 0.0),
        (1.0, 1.0),
        (0.0, 1.0),
        (2.0, 1.0),
        (2.0, 2.0),
        (1.0, 2.0),
    ):
        add_sketch_point(geometry, x, y)
    p1, p2, p3, p4, p5, p6, p7 = _point_ids(geometry)
    for start_id, end_id in (
        (p1, p2),
        (p2, p3),
        (p3, p4),
        (p4, p1),
        (p3, p5),
        (p5, p6),
        (p6, p7),
        (p7, p3),
    ):
        add_sketch_edge(geometry, start_id, end_id)

    build_faces_from_edges(geometry)

    assert len(geometry.faces) == 2
    assert all(len(face.edge_ids) == 4 for face in geometry.faces)


def test_stage18_polygonize_three_rectangles_in_a_row() -> None:
    geometry = create_empty_sketch_geometry()
    for x, y in (
        (0.0, 0.0), (1.0, 0.0), (2.0, 0.0), (3.0, 0.0),
        (0.0, 1.0), (1.0, 1.0), (2.0, 1.0), (3.0, 1.0),
    ):
        add_sketch_point(geometry, x, y)
    p1, p2, p3, p4, p5, p6, p7, p8 = _point_ids(geometry)
    for start_id, end_id in (
        (p1, p2), (p2, p3), (p3, p4),
        (p5, p6), (p6, p7), (p7, p8),
        (p1, p5), (p2, p6), (p3, p7), (p4, p8),
    ):
        add_sketch_edge(geometry, start_id, end_id)

    build_faces_from_edges(geometry)

    assert len(geometry.faces) == 3
    middle_shared = [
        edge.id
        for edge in geometry.edges
        if {edge.start_point_id, edge.end_point_id} in ({p2, p6}, {p3, p7})
    ]
    for edge_id in middle_shared:
        assert sum(edge_id in face.edge_ids for face in geometry.faces) == 2


def test_stage18_polygonize_t_shape_open_line_reports_dangles() -> None:
    geometry = create_empty_sketch_geometry()
    for x, y in ((0.0, 0.0), (1.0, 0.0), (2.0, 0.0), (1.0, 1.0)):
        add_sketch_point(geometry, x, y)
    p1, p2, p3, p4 = _point_ids(geometry)
    for start_id, end_id in ((p1, p2), (p2, p3), (p2, p4)):
        add_sketch_edge(geometry, start_id, end_id)

    with pytest.raises(ValueError, match="dangles|cuts|闭合面生成失败"):
        build_faces_from_edges(geometry)


def test_stage18_polygonize_non_noded_cross_reports_error() -> None:
    geometry = create_empty_sketch_geometry()
    for x, y in ((0.0, 0.0), (2.0, 2.0), (0.0, 2.0), (2.0, 0.0)):
        add_sketch_point(geometry, x, y)
    p1, p2, p3, p4 = _point_ids(geometry)
    for start_id, end_id in ((p1, p2), (p3, p4)):
        add_sketch_edge(geometry, start_id, end_id)

    with pytest.raises(ValueError, match="未节点化|交叉|重叠|non_noded"):
        build_faces_from_edges(geometry)

