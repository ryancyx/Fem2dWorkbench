from __future__ import annotations

import pytest

from core.engineering.geometry import GeometryFace
from services.sketch_geometry_service import (
    add_sketch_edge,
    add_sketch_point,
    build_faces_from_edges,
    create_empty_sketch_geometry,
)


def _add_rectangle(geometry, origin_x: float, origin_y: float, width: float, height: float) -> None:
    start_index = len(geometry.points)
    for x, y in (
        (origin_x, origin_y),
        (origin_x + width, origin_y),
        (origin_x + width, origin_y + height),
        (origin_x, origin_y + height),
    ):
        add_sketch_point(geometry, x, y)
    point_ids = [point.id for point in geometry.points[start_index:]]
    for start_id, end_id in (
        (point_ids[0], point_ids[1]),
        (point_ids[1], point_ids[2]),
        (point_ids[2], point_ids[3]),
        (point_ids[3], point_ids[0]),
    ):
        add_sketch_edge(geometry, start_id, end_id)


def test_stage18_build_faces_from_edges_two_disjoint_rectangles() -> None:
    geometry = create_empty_sketch_geometry()
    _add_rectangle(geometry, 0.0, 0.0, 2.0, 1.0)
    _add_rectangle(geometry, 3.0, 0.0, 1.5, 1.0)

    build_faces_from_edges(geometry)

    assert len(geometry.faces) == 2
    assert [face.id for face in geometry.faces] == ["f1", "f2"]
    assert all(len(face.edge_ids) == 4 for face in geometry.faces)


def test_stage18_build_faces_from_edges_open_chain_fails() -> None:
    geometry = create_empty_sketch_geometry()
    for x, y in ((0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0)):
        add_sketch_point(geometry, x, y)
    point_ids = [point.id for point in geometry.points]
    for start_id, end_id in (
        (point_ids[0], point_ids[1]),
        (point_ids[1], point_ids[2]),
        (point_ids[2], point_ids[3]),
    ):
        add_sketch_edge(geometry, start_id, end_id)

    with pytest.raises(ValueError, match="闭合面生成失败|dangles|cuts|未识别|未参与成面"):
        build_faces_from_edges(geometry)


def test_stage18_build_faces_from_edges_branch_fails() -> None:
    geometry = create_empty_sketch_geometry()
    for x, y in ((0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0), (2.0, 0.0)):
        add_sketch_point(geometry, x, y)
    point_ids = [point.id for point in geometry.points]
    for start_id, end_id in (
        (point_ids[0], point_ids[1]),
        (point_ids[1], point_ids[2]),
        (point_ids[2], point_ids[3]),
        (point_ids[3], point_ids[0]),
        (point_ids[1], point_ids[4]),
    ):
        add_sketch_edge(geometry, start_id, end_id)

    with pytest.raises(ValueError, match="闭合面生成失败|dangles|cuts|未参与成面|branch|degree"):
        build_faces_from_edges(geometry)


def test_stage18_build_faces_from_edges_preserves_section_id_on_same_edge_set() -> None:
    geometry = create_empty_sketch_geometry()
    _add_rectangle(geometry, 0.0, 0.0, 2.0, 1.0)
    build_faces_from_edges(geometry)
    geometry.faces = [GeometryFace(id="f1", edge_ids=list(geometry.faces[0].edge_ids), section_id="sec_steel")]

    build_faces_from_edges(geometry)

    assert len(geometry.faces) == 1
    assert geometry.faces[0].section_id == "sec_steel"
