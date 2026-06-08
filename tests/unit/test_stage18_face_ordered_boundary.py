from __future__ import annotations

from services.sketch_geometry_service import (
    add_sketch_edge,
    add_sketch_point,
    build_faces_from_edges,
    create_empty_sketch_geometry,
    get_sketch_faces,
)


def test_stage18_face_ordered_boundary_shared_edge_rectangles() -> None:
    geometry = create_empty_sketch_geometry()
    for x, y in ((0.0, 0.0), (1.0, 0.0), (2.0, 0.0), (0.0, 1.0), (1.0, 1.0), (2.0, 1.0)):
        add_sketch_point(geometry, x, y)

    point_ids = [point.id for point in geometry.points]
    p1, p2, p3, p4, p5, p6 = point_ids
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
    faces = get_sketch_faces(geometry)
    by_id = {face["id"]: face for face in faces}

    assert len(faces) == 2
    assert all(face["point_ids"] for face in faces)
    assert len(by_id["f1"]["point_ids"]) == 4
    assert len(by_id["f2"]["point_ids"]) == 4
    assert by_id["f1"]["point_ids"] != by_id["f2"]["point_ids"]
    assert {p2, p5}.issubset(set(by_id["f1"]["point_ids"]))
    assert {p2, p5}.issubset(set(by_id["f2"]["point_ids"]))

