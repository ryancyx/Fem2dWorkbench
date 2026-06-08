from __future__ import annotations

from services.sketch_geometry_service import (
    add_sketch_edge,
    add_sketch_point,
    create_empty_sketch_geometry,
    normalize_edges_by_embedded_points,
)


def _point_ids(geometry) -> list[str]:
    return [point.id for point in geometry.points]


def _edge_pairs(geometry) -> set[frozenset[str]]:
    return {
        frozenset((edge.start_point_id, edge.end_point_id))
        for edge in geometry.edges
    }


def test_stage18_normalize_single_embedded_point_splits_edge() -> None:
    geometry = create_empty_sketch_geometry()
    for x, y in ((0.0, 0.0), (10.0, 0.0), (5.0, 0.0)):
        add_sketch_point(geometry, x, y)
    p1, p2, p3 = _point_ids(geometry)
    add_sketch_edge(geometry, p1, p2)

    stats = normalize_edges_by_embedded_points(geometry)

    assert stats["split_edge_count"] == 1
    assert _edge_pairs(geometry) == {frozenset((p1, p3)), frozenset((p3, p2))}


def test_stage18_normalize_multiple_embedded_points_split_in_order() -> None:
    geometry = create_empty_sketch_geometry()
    for x, y in ((0.0, 0.0), (10.0, 0.0), (3.0, 0.0), (7.0, 0.0)):
        add_sketch_point(geometry, x, y)
    p1, p2, p3, p4 = _point_ids(geometry)
    add_sketch_edge(geometry, p1, p2)

    stats = normalize_edges_by_embedded_points(geometry)

    assert stats["split_edge_count"] == 1
    assert _edge_pairs(geometry) == {
        frozenset((p1, p3)),
        frozenset((p3, p4)),
        frozenset((p4, p2)),
    }


def test_stage18_normalize_endpoint_points_do_not_split() -> None:
    geometry = create_empty_sketch_geometry()
    for x, y in ((0.0, 0.0), (10.0, 0.0)):
        add_sketch_point(geometry, x, y)
    p1, p2 = _point_ids(geometry)
    add_sketch_edge(geometry, p1, p2)

    stats = normalize_edges_by_embedded_points(geometry)

    assert stats["split_edge_count"] == 0
    assert _edge_pairs(geometry) == {frozenset((p1, p2))}


def test_stage18_normalize_extension_point_does_not_split() -> None:
    geometry = create_empty_sketch_geometry()
    for x, y in ((0.0, 0.0), (10.0, 0.0), (15.0, 0.0)):
        add_sketch_point(geometry, x, y)
    p1, p2, _p3 = _point_ids(geometry)
    add_sketch_edge(geometry, p1, p2)

    stats = normalize_edges_by_embedded_points(geometry)

    assert stats["split_edge_count"] == 0
    assert _edge_pairs(geometry) == {frozenset((p1, p2))}


def test_stage18_normalize_non_collinear_point_does_not_split() -> None:
    geometry = create_empty_sketch_geometry()
    for x, y in ((0.0, 0.0), (10.0, 0.0), (5.0, 1.0)):
        add_sketch_point(geometry, x, y)
    p1, p2, _p3 = _point_ids(geometry)
    add_sketch_edge(geometry, p1, p2)

    stats = normalize_edges_by_embedded_points(geometry)

    assert stats["split_edge_count"] == 0
    assert _edge_pairs(geometry) == {frozenset((p1, p2))}


def test_stage18_normalize_reuses_existing_subsegment_instead_of_duplicating() -> None:
    geometry = create_empty_sketch_geometry()
    for x, y in ((0.0, 0.0), (10.0, 0.0), (5.0, 0.0)):
        add_sketch_point(geometry, x, y)
    p1, p2, p3 = _point_ids(geometry)
    add_sketch_edge(geometry, p1, p3)
    add_sketch_edge(geometry, p1, p2)

    stats = normalize_edges_by_embedded_points(geometry)

    assert stats["split_edge_count"] == 1
    assert stats["reused_segment_count"] >= 1
    assert _edge_pairs(geometry) == {frozenset((p1, p3)), frozenset((p3, p2))}
