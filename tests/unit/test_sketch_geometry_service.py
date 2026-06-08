from __future__ import annotations

from services.sketch_geometry_service import (
    add_sketch_edge,
    add_sketch_point,
    build_faces_from_edges,
    can_build_closed_faces,
    create_empty_sketch_geometry,
)


def test_build_faces_from_edges_supports_multiple_disjoint_closed_loops() -> None:
    geometry = create_empty_sketch_geometry()
    for x, y in (
        (0.0, 0.0),
        (1.0, 0.0),
        (1.0, 1.0),
        (0.0, 1.0),
        (2.0, 0.0),
        (3.0, 0.0),
        (3.0, 1.0),
        (2.0, 1.0),
    ):
        add_sketch_point(geometry, x, y)
    point_ids = [point.id for point in geometry.points]
    for start_id, end_id in (
        (point_ids[0], point_ids[1]),
        (point_ids[1], point_ids[2]),
        (point_ids[2], point_ids[3]),
        (point_ids[3], point_ids[0]),
        (point_ids[4], point_ids[5]),
        (point_ids[5], point_ids[6]),
        (point_ids[6], point_ids[7]),
        (point_ids[7], point_ids[4]),
    ):
        add_sketch_edge(geometry, start_id, end_id)

    assert can_build_closed_faces(geometry)
    build_faces_from_edges(geometry)
    assert [face.id for face in geometry.faces] == ["f1", "f2"]
