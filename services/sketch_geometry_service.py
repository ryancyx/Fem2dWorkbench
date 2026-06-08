from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass
import math
from typing import Iterable

from core.engineering.geometry import GeometryEdge, GeometryFace, GeometryModel, GeometryPoint

try:  # pragma: no cover - depends on local environment
    from shapely.geometry import LineString
    from shapely.ops import polygonize_full, unary_union
except ImportError:  # pragma: no cover - depends on local environment
    LineString = None
    polygonize_full = None
    unary_union = None


_EPS = 1.0e-8


@dataclass(frozen=True)
class _FaceLoop:
    edge_ids: list[str]
    point_ids: list[str]
    ordered_points: list[tuple[float, float]]
    sort_key: tuple[float, float, float, float]


def create_empty_sketch_geometry() -> GeometryModel:
    return GeometryModel(points=[], edges=[], faces=[])


def is_sketch_geometry(geometry: GeometryModel) -> bool:
    return hasattr(geometry, "points") and hasattr(geometry, "edges") and hasattr(geometry, "faces")


def get_sketch_points(geometry: GeometryModel) -> list[dict]:
    return [{"id": point.id, "x": point.x, "y": point.y} for point in geometry.points]


def get_sketch_edges(geometry: GeometryModel) -> list[dict]:
    return [
        {
            "id": edge.id,
            "start_point_id": edge.start_point_id,
            "end_point_id": edge.end_point_id,
        }
        for edge in geometry.edges
    ]


def get_sketch_faces(geometry: GeometryModel) -> list[dict]:
    return [
        {
            "id": face.id,
            "edge_ids": list(face.edge_ids),
            "point_ids": list(face.point_ids),
            "section_id": face.section_id,
        }
        for face in geometry.faces
    ]


def create_unique_point_id(geometry: GeometryModel, base_id: str = "p") -> str:
    return _create_unique_numbered_id((point.id for point in geometry.points), base_id)


def create_unique_edge_id(geometry: GeometryModel, base_id: str = "e") -> str:
    return _create_unique_numbered_id((edge.id for edge in geometry.edges), base_id)


def create_unique_face_id(geometry: GeometryModel, base_id: str = "f") -> str:
    return _create_unique_numbered_id((face.id for face in geometry.faces), base_id)


def add_sketch_point(geometry: GeometryModel, x: float, y: float) -> GeometryModel:
    geometry.points.append(
        GeometryPoint(
            id=create_unique_point_id(geometry),
            x=float(x),
            y=float(y),
        )
    )
    return geometry


def move_sketch_point(geometry: GeometryModel, point_id: str, x: float, y: float) -> GeometryModel:
    point = _require_point(geometry, point_id)
    point.x = float(x)
    point.y = float(y)
    return geometry


def delete_sketch_point(geometry: GeometryModel, point_id: str) -> GeometryModel:
    _require_point(geometry, point_id)
    geometry.points = [point for point in geometry.points if point.id != point_id]
    geometry.edges = [
        edge
        for edge in geometry.edges
        if edge.start_point_id != point_id and edge.end_point_id != point_id
    ]
    geometry.faces = []
    return geometry


def add_sketch_edge(geometry: GeometryModel, start_point_id: str, end_point_id: str) -> GeometryModel:
    _require_point(geometry, start_point_id)
    _require_point(geometry, end_point_id)
    if start_point_id == end_point_id:
        raise ValueError("Sketch edge endpoints must be different")
    if _edge_exists_between(geometry, start_point_id, end_point_id):
        raise ValueError(f"Sketch edge already exists between {start_point_id!r} and {end_point_id!r}")

    geometry.edges.append(
        GeometryEdge(
            id=create_unique_edge_id(geometry),
            start_point_id=start_point_id,
            end_point_id=end_point_id,
        )
    )
    geometry.faces = []
    return geometry


def delete_sketch_edge(geometry: GeometryModel, edge_id: str) -> GeometryModel:
    _require_edge(geometry, edge_id)
    geometry.edges = [edge for edge in geometry.edges if edge.id != edge_id]
    geometry.faces = []
    return geometry


def can_build_single_closed_face(geometry: GeometryModel) -> bool:
    try:
        return len(_extract_face_loops(geometry, require_all_edges=False)) == 1
    except ValueError:
        return False


def can_build_closed_faces(geometry: GeometryModel) -> bool:
    return len(geometry.points) >= 3 and len(geometry.edges) >= 3


def build_geometry_diagnostics_text(geometry: GeometryModel) -> str:
    diagnostics = _analyze_geometry_topology(geometry)
    lines = [
        f"point_count={diagnostics['point_count']}",
        f"edge_count={diagnostics['edge_count']}",
        f"connected_component_count={len(diagnostics['components'])}",
        f"candidate_face_count={diagnostics['candidate_face_count']}",
        f"dangles={diagnostics['dangle_count']}",
        f"cuts={diagnostics['cut_count']}",
        f"invalids={diagnostics['invalid_count']}",
    ]
    if diagnostics["duplicate_edge_groups"]:
        duplicate_rows = ["/".join(group["edge_ids"]) for group in diagnostics["duplicate_edge_groups"]]
        lines.append(f"duplicate_edges={'; '.join(duplicate_rows)}")
    if diagnostics["overlapping_edge_pairs"]:
        overlap_rows = [
            f"{row['edge_ids'][0]}/{row['edge_ids'][1]}@{row['kind']}"
            for row in diagnostics["overlapping_edge_pairs"]
        ]
        lines.append(f"overlap_or_nonnoded={'; '.join(overlap_rows)}")
    for component in diagnostics["components"]:
        lines.append(
            f"component {component['index']}: node_count={component['node_count']} "
            f"edge_count={component['edge_count']}"
        )
        if component["degree_rows"]:
            degree_rows = [
                f"{row['point_id']} degree={row['degree']} edges={'/'.join(row['edge_ids'])}"
                for row in component["degree_rows"]
            ]
            lines.append(f"  degrees: {'; '.join(degree_rows)}")
    return "\n".join(lines)


def build_single_face_from_edges(geometry: GeometryModel) -> GeometryModel:
    loop_rows = _extract_face_loops(geometry, require_all_edges=True)
    if len(loop_rows) != 1:
        raise ValueError("Sketch edges do not form a single closed face")
    geometry.faces = [
        GeometryFace(
            id="f1",
            edge_ids=list(loop_rows[0].edge_ids),
            point_ids=list(loop_rows[0].point_ids),
        )
    ]
    return geometry


def build_faces_from_edges(geometry: GeometryModel) -> GeometryModel:
    loop_rows = _extract_face_loops(geometry, require_all_edges=True)
    previous_section_id_by_edge_set = {
        frozenset(face.edge_ids): face.section_id
        for face in geometry.faces
        if face.section_id
    }
    geometry.faces = [
        GeometryFace(
            id=f"f{index}",
            edge_ids=list(loop_row.edge_ids),
            point_ids=list(loop_row.point_ids),
            section_id=previous_section_id_by_edge_set.get(frozenset(loop_row.edge_ids), ""),
        )
        for index, loop_row in enumerate(loop_rows, start=1)
    ]
    return geometry


def clear_sketch_geometry(geometry: GeometryModel) -> GeometryModel:
    geometry.points = []
    geometry.edges = []
    geometry.faces = []
    return geometry


def create_geometry_from_polygon_points(points: list[tuple[float, float]]) -> GeometryModel:
    if len(points) < 3:
        raise ValueError("Polygon sketch requires at least 3 points")

    geometry = create_empty_sketch_geometry()
    for x, y in points:
        add_sketch_point(geometry, x, y)

    point_ids = [point.id for point in geometry.points]
    for index, start_point_id in enumerate(point_ids):
        end_point_id = point_ids[(index + 1) % len(point_ids)]
        add_sketch_edge(geometry, start_point_id, end_point_id)

    build_single_face_from_edges(geometry)
    return geometry


def _extract_face_loops(geometry: GeometryModel, require_all_edges: bool) -> list[_FaceLoop]:
    point_by_id = {point.id: point for point in geometry.points}
    edge_by_id = {edge.id: edge for edge in geometry.edges}
    duplicate_edge_groups = _find_duplicate_edges(geometry)
    if duplicate_edge_groups:
        first_group = duplicate_edge_groups[0]
        raise ValueError(
            "闭合面生成失败：存在重复几何边。"
            f" point_pair={'-'.join(first_group['point_ids'])};"
            f" edge_ids={'/'.join(first_group['edge_ids'])}。"
        )

    topology_issues = _find_pairwise_edge_issues(geometry, point_by_id)
    if topology_issues:
        first_issue = topology_issues[0]
        raise ValueError(
            "闭合面生成失败：检测到未节点化交叉或重叠边。"
            f" edge_ids={first_issue['edge_ids'][0]}/{first_issue['edge_ids'][1]};"
            f" kind={first_issue['kind']};"
            f" detail={first_issue['detail']}。"
            " 如为共线接触，请先在交点处拆分边。"
        )

    if len(geometry.edges) < 3:
        raise ValueError("闭合面生成失败：至少需要 3 条边。")

    if LineString is not None and unary_union is not None and polygonize_full is not None:
        loop_rows, diagnostics = _extract_face_loops_with_shapely(geometry, point_by_id, edge_by_id)
    else:
        loop_rows, diagnostics = _extract_face_loops_fallback(geometry, point_by_id, edge_by_id)

    if not loop_rows:
        raise ValueError(_format_polygonize_failure(diagnostics, "未识别到任何闭合面"))

    if require_all_edges and (diagnostics["dangle_count"] or diagnostics["cut_count"] or diagnostics["invalid_count"]):
        raise ValueError(_format_polygonize_failure(diagnostics, "线网中仍有未参与成面的边"))

    loop_rows.sort(key=lambda row: row.sort_key)
    return loop_rows


def _extract_face_loops_with_shapely(
    geometry: GeometryModel,
    point_by_id: dict[str, GeometryPoint],
    edge_by_id: dict[str, GeometryEdge],
) -> tuple[list[_FaceLoop], dict[str, object]]:
    lines = []
    for edge in geometry.edges:
        start = point_by_id[edge.start_point_id]
        end = point_by_id[edge.end_point_id]
        lines.append(LineString([(start.x, start.y), (end.x, end.y)]))

    merged = unary_union(lines)
    polygons, dangles, cuts, invalids = polygonize_full(merged)

    loop_rows: list[_FaceLoop] = []
    for polygon in polygons.geoms:
        coords = list(polygon.exterior.coords)
        point_ids, edge_ids = _map_polygon_segments_to_geometry(coords, geometry, point_by_id, edge_by_id)
        ordered_points = [_point_xy(point_by_id[point_id]) for point_id in point_ids]
        loop_rows.append(
            _FaceLoop(
                edge_ids=edge_ids,
                point_ids=point_ids,
                ordered_points=ordered_points,
                sort_key=_component_sort_key(ordered_points),
            )
        )

    diagnostics = {
        "candidate_face_count": len(loop_rows),
        "dangle_count": len(list(dangles.geoms)),
        "cut_count": len(list(cuts.geoms)),
        "invalid_count": len(list(invalids.geoms)),
        "missing_segment_count": 0,
    }
    return loop_rows, diagnostics


def _extract_face_loops_fallback(
    geometry: GeometryModel,
    point_by_id: dict[str, GeometryPoint],
    edge_by_id: dict[str, GeometryEdge],
) -> tuple[list[_FaceLoop], dict[str, object]]:
    adjacency = _build_sorted_adjacency(geometry, point_by_id)
    edge_id_by_endpoint_pair = {
        frozenset((edge.start_point_id, edge.end_point_id)): edge.id for edge in geometry.edges
    }

    visited_half_edges: set[tuple[str, str]] = set()
    bounded_faces: list[_FaceLoop] = []
    for edge in geometry.edges:
        for start_point_id, end_point_id in (
            (edge.start_point_id, edge.end_point_id),
            (edge.end_point_id, edge.start_point_id),
        ):
            if (start_point_id, end_point_id) in visited_half_edges:
                continue
            try:
                point_ids, edge_ids = _trace_face_cycle(
                    start_point_id=start_point_id,
                    end_point_id=end_point_id,
                    adjacency=adjacency,
                    point_by_id=point_by_id,
                    edge_id_by_endpoint_pair=edge_id_by_endpoint_pair,
                )
            except ValueError:
                continue
            for directed_edge in zip(point_ids, point_ids[1:] + [point_ids[0]]):
                visited_half_edges.add(directed_edge)
            ordered_points = [_point_xy(point_by_id[point_id]) for point_id in point_ids]
            signed_area = _signed_area_xy(ordered_points)
            if abs(signed_area) <= _EPS:
                continue
            if signed_area < 0.0:
                continue
            bounded_faces.append(
                _FaceLoop(
                    edge_ids=edge_ids,
                    point_ids=point_ids,
                    ordered_points=ordered_points,
                    sort_key=_component_sort_key(ordered_points),
                )
            )

    unique_faces: list[_FaceLoop] = []
    seen_face_keys: set[tuple[str, ...]] = set()
    for face in bounded_faces:
        face_key = _canonical_cycle_key(face.point_ids)
        if face_key in seen_face_keys:
            continue
        seen_face_keys.add(face_key)
        unique_faces.append(face)

    usage_count_by_edge_id: dict[str, int] = defaultdict(int)
    for face in unique_faces:
        for edge_id in face.edge_ids:
            usage_count_by_edge_id[edge_id] += 1

    dangle_count = 0
    cut_count = 0
    for edge in geometry.edges:
        if usage_count_by_edge_id.get(edge.id, 0):
            continue
        start_degree = len(adjacency[edge.start_point_id])
        end_degree = len(adjacency[edge.end_point_id])
        if start_degree == 1 or end_degree == 1:
            dangle_count += 1
        else:
            cut_count += 1

    diagnostics = {
        "candidate_face_count": len(unique_faces),
        "dangle_count": dangle_count,
        "cut_count": cut_count,
        "invalid_count": 0,
        "missing_segment_count": 0,
    }
    return unique_faces, diagnostics


def _analyze_geometry_topology(geometry: GeometryModel) -> dict[str, object]:
    point_by_id = {point.id: point for point in geometry.points}
    adjacency: dict[str, list[tuple[str, str]]] = defaultdict(list)
    point_to_edge_ids: dict[str, list[str]] = defaultdict(list)
    participating_points: set[str] = set()

    for edge in geometry.edges:
        if edge.start_point_id not in point_by_id or edge.end_point_id not in point_by_id:
            raise ValueError(f"Sketch edge {edge.id!r} references unknown points")
        adjacency[edge.start_point_id].append((edge.end_point_id, edge.id))
        adjacency[edge.end_point_id].append((edge.start_point_id, edge.id))
        point_to_edge_ids[edge.start_point_id].append(edge.id)
        point_to_edge_ids[edge.end_point_id].append(edge.id)
        participating_points.add(edge.start_point_id)
        participating_points.add(edge.end_point_id)

    duplicate_edge_groups = _find_duplicate_edges(geometry)
    overlapping_edge_pairs = _find_pairwise_edge_issues(geometry, point_by_id)
    components = _connected_components(participating_points, adjacency)
    component_rows: list[dict[str, object]] = []
    for index, component in enumerate(components, start=1):
        component_edge_ids = [
            edge.id
            for edge in geometry.edges
            if edge.start_point_id in component and edge.end_point_id in component
        ]
        degree_rows = [
            {
                "point_id": point_id,
                "degree": len(adjacency[point_id]),
                "edge_ids": sorted(point_to_edge_ids[point_id]),
            }
            for point_id in sorted(component)
        ]
        component_rows.append(
            {
                "index": index,
                "point_ids": sorted(component),
                "node_count": len(component),
                "edge_count": len(component_edge_ids),
                "edge_ids": sorted(component_edge_ids),
                "degree_rows": degree_rows,
            }
        )

    candidate_face_count = 0
    dangle_count = 0
    cut_count = 0
    invalid_count = len(overlapping_edge_pairs)
    if not duplicate_edge_groups and not overlapping_edge_pairs and len(geometry.edges) >= 3:
        try:
            _, polygonize_diagnostics = _extract_face_loops(geometry, require_all_edges=False), None
        except ValueError:
            polygonize_diagnostics = None
        else:
            polygonize_diagnostics = None
        try:
            loops = _extract_face_loops(geometry, require_all_edges=False)
            candidate_face_count = len(loops)
        except ValueError:
            pass
        try:
            if LineString is not None and unary_union is not None and polygonize_full is not None:
                _, polygonize_diag = _extract_face_loops_with_shapely(geometry, point_by_id, {edge.id: edge for edge in geometry.edges})
            else:
                _, polygonize_diag = _extract_face_loops_fallback(geometry, point_by_id, {edge.id: edge for edge in geometry.edges})
            dangle_count = int(polygonize_diag["dangle_count"])
            cut_count = int(polygonize_diag["cut_count"])
            invalid_count += int(polygonize_diag["invalid_count"])
        except ValueError:
            pass

    return {
        "point_count": len(geometry.points),
        "edge_count": len(geometry.edges),
        "components": component_rows,
        "duplicate_edge_groups": duplicate_edge_groups,
        "overlapping_edge_pairs": overlapping_edge_pairs,
        "candidate_face_count": candidate_face_count,
        "dangle_count": dangle_count,
        "cut_count": cut_count,
        "invalid_count": invalid_count,
    }


def _build_sorted_adjacency(
    geometry: GeometryModel,
    point_by_id: dict[str, GeometryPoint],
) -> dict[str, list[str]]:
    adjacency: dict[str, list[str]] = defaultdict(list)
    for edge in geometry.edges:
        adjacency[edge.start_point_id].append(edge.end_point_id)
        adjacency[edge.end_point_id].append(edge.start_point_id)
    for point_id, neighbors in adjacency.items():
        unique_neighbors = sorted(
            set(neighbors),
            key=lambda neighbor_id: (
                math.atan2(
                    point_by_id[neighbor_id].y - point_by_id[point_id].y,
                    point_by_id[neighbor_id].x - point_by_id[point_id].x,
                ),
                neighbor_id,
            ),
        )
        adjacency[point_id] = unique_neighbors
    return adjacency


def _trace_face_cycle(
    start_point_id: str,
    end_point_id: str,
    adjacency: dict[str, list[str]],
    point_by_id: dict[str, GeometryPoint],
    edge_id_by_endpoint_pair: dict[frozenset[str], str],
) -> tuple[list[str], list[str]]:
    start = (start_point_id, end_point_id)
    current = start
    seen_directed_edges: set[tuple[str, str]] = set()
    point_ids = [start_point_id]
    edge_ids: list[str] = []

    while True:
        current_start_id, current_end_id = current
        if current in seen_directed_edges:
            raise ValueError("闭合面生成失败：检测到非法环遍历，可能存在重复边或错误连接。")
        seen_directed_edges.add(current)
        point_ids.append(current_end_id)

        edge_id = edge_id_by_endpoint_pair.get(frozenset((current_start_id, current_end_id)))
        if edge_id is None:
            raise ValueError("闭合面生成失败：面边界段无法映射到原始几何边。")
        edge_ids.append(edge_id)

        next_point_id = _choose_next_face_neighbor(current_start_id, current_end_id, adjacency)
        current = (current_end_id, next_point_id)
        if current == start:
            break
        if len(point_ids) > len(edge_id_by_endpoint_pair) + 2:
            raise ValueError("闭合面生成失败：面边界遍历异常，可能存在未节点化交叉。")

    if point_ids[-1] == point_ids[0]:
        point_ids.pop()
    return point_ids, edge_ids


def _choose_next_face_neighbor(
    previous_point_id: str,
    current_point_id: str,
    adjacency: dict[str, list[str]],
) -> str:
    neighbors = adjacency[current_point_id]
    if previous_point_id not in neighbors:
        raise ValueError("闭合面生成失败：边连接关系异常。")
    previous_index = neighbors.index(previous_point_id)
    return neighbors[(previous_index - 1) % len(neighbors)]


def _map_polygon_segments_to_geometry(
    coords: list[tuple[float, float]],
    geometry: GeometryModel,
    point_by_id: dict[str, GeometryPoint],
    edge_by_id: dict[str, GeometryEdge],
) -> tuple[list[str], list[str]]:
    if len(coords) < 4:
        raise ValueError("闭合面生成失败：polygonize 返回了无效边界。")

    unique_coords = coords[:-1]
    point_ids: list[str] = []
    edge_ids: list[str] = []
    point_id_by_coord = _point_ids_by_coordinate(point_by_id)
    edge_lookup = _edge_lookup_by_endpoint_coordinates(geometry, point_by_id)

    for coord in unique_coords:
        point_id = _point_id_for_coordinate(coord, point_id_by_coord)
        if point_id is None:
            raise ValueError(
                "闭合面生成失败：polygonize 生成的顶点无法映射到原始几何点。"
                " 检测到未节点化共线边，请在交点处拆分边后再生成闭合面。"
            )
        point_ids.append(point_id)

    for index, start_coord in enumerate(unique_coords):
        end_coord = unique_coords[(index + 1) % len(unique_coords)]
        edge_id = edge_lookup.get(_canonical_segment_key(start_coord, end_coord))
        if edge_id is None:
            raise ValueError(
                "闭合面生成失败：面边界段无法映射到原始几何边。"
                " 请检查是否存在未节点化交叉或重叠边。"
            )
        edge_ids.append(edge_id)
    return point_ids, edge_ids


def _point_ids_by_coordinate(point_by_id: dict[str, GeometryPoint]) -> dict[tuple[int, int], str]:
    mapping: dict[tuple[int, int], str] = {}
    for point_id, point in point_by_id.items():
        mapping[_coord_key((point.x, point.y))] = point_id
    return mapping


def _edge_lookup_by_endpoint_coordinates(
    geometry: GeometryModel,
    point_by_id: dict[str, GeometryPoint],
) -> dict[tuple[tuple[int, int], tuple[int, int]], str]:
    lookup: dict[tuple[tuple[int, int], tuple[int, int]], str] = {}
    for edge in geometry.edges:
        start_xy = _point_xy(point_by_id[edge.start_point_id])
        end_xy = _point_xy(point_by_id[edge.end_point_id])
        lookup[_canonical_segment_key(start_xy, end_xy)] = edge.id
    return lookup


def _point_id_for_coordinate(
    coord: tuple[float, float],
    point_id_by_coord: dict[tuple[int, int], str],
) -> str | None:
    return point_id_by_coord.get(_coord_key(coord))


def _find_duplicate_edges(geometry: GeometryModel) -> list[dict[str, object]]:
    grouped_edge_ids_by_endpoint_pair: dict[frozenset[str], list[str]] = defaultdict(list)
    for edge in geometry.edges:
        endpoint_pair = frozenset((edge.start_point_id, edge.end_point_id))
        grouped_edge_ids_by_endpoint_pair[endpoint_pair].append(edge.id)
    return [
        {"point_ids": sorted(endpoint_pair), "edge_ids": edge_ids}
        for endpoint_pair, edge_ids in grouped_edge_ids_by_endpoint_pair.items()
        if len(edge_ids) > 1
    ]


def _find_pairwise_edge_issues(
    geometry: GeometryModel,
    point_by_id: dict[str, GeometryPoint],
) -> list[dict[str, object]]:
    issues: list[dict[str, object]] = []
    edges = list(geometry.edges)
    for index, edge in enumerate(edges):
        a1 = _point_xy(point_by_id[edge.start_point_id])
        a2 = _point_xy(point_by_id[edge.end_point_id])
        for other_edge in edges[index + 1 :]:
            b1 = _point_xy(point_by_id[other_edge.start_point_id])
            b2 = _point_xy(point_by_id[other_edge.end_point_id])
            shared_point_ids = {
                edge.start_point_id,
                edge.end_point_id,
            } & {
                other_edge.start_point_id,
                other_edge.end_point_id,
            }

            overlap_kind = _collinear_overlap_kind(a1, a2, b1, b2)
            if overlap_kind is not None:
                issues.append(
                    {
                        "edge_ids": (edge.id, other_edge.id),
                        "kind": overlap_kind,
                        "detail": "collinear overlap detected",
                    }
                )
                continue

            intersection = _segment_intersection_point(a1, a2, b1, b2)
            if intersection is None:
                continue
            if _shared_endpoint_intersection_ok(intersection, a1, a2, b1, b2, shared_point_ids):
                continue
            issues.append(
                {
                    "edge_ids": (edge.id, other_edge.id),
                    "kind": "non_noded_intersection",
                    "detail": f"intersection=({_fmt(intersection[0])},{_fmt(intersection[1])})",
                }
            )
    return issues


def _shared_endpoint_intersection_ok(
    intersection: tuple[float, float],
    a1: tuple[float, float],
    a2: tuple[float, float],
    b1: tuple[float, float],
    b2: tuple[float, float],
    shared_point_ids: set[str],
) -> bool:
    if not shared_point_ids:
        return False
    return (
        _same_xy(intersection, a1) or _same_xy(intersection, a2)
    ) and (
        _same_xy(intersection, b1) or _same_xy(intersection, b2)
    )


def _collinear_overlap_kind(
    a1: tuple[float, float],
    a2: tuple[float, float],
    b1: tuple[float, float],
    b2: tuple[float, float],
) -> str | None:
    if abs(_orientation(a1, a2, b1)) > _EPS or abs(_orientation(a1, a2, b2)) > _EPS:
        return None

    if max(min(a1[0], a2[0]), min(b1[0], b2[0])) > min(max(a1[0], a2[0]), max(b1[0], b2[0])) + _EPS:
        return None
    if max(min(a1[1], a2[1]), min(b1[1], b2[1])) > min(max(a1[1], a2[1]), max(b1[1], b2[1])) + _EPS:
        return None

    shared_endpoints = sum(
        1
        for point_a in (a1, a2)
        for point_b in (b1, b2)
        if _same_xy(point_a, point_b)
    )
    if shared_endpoints == 1 and _overlap_only_at_single_point(a1, a2, b1, b2):
        return None
    if shared_endpoints == 2:
        return "duplicate_overlap"
    return "collinear_overlap"


def _overlap_only_at_single_point(
    a1: tuple[float, float],
    a2: tuple[float, float],
    b1: tuple[float, float],
    b2: tuple[float, float],
) -> bool:
    shared_points = [
        point_a
        for point_a in (a1, a2)
        for point_b in (b1, b2)
        if _same_xy(point_a, point_b)
    ]
    if not shared_points:
        return False
    shared = shared_points[0]
    return (
        (_same_xy(shared, a1) or _same_xy(shared, a2))
        and (_same_xy(shared, b1) or _same_xy(shared, b2))
        and not (_point_on_segment_strict(a1, b1, a2) or _point_on_segment_strict(a1, b2, a2))
        and not (_point_on_segment_strict(b1, a1, b2) or _point_on_segment_strict(b1, a2, b2))
    )


def _segment_intersection_point(
    a1: tuple[float, float],
    a2: tuple[float, float],
    b1: tuple[float, float],
    b2: tuple[float, float],
) -> tuple[float, float] | None:
    denominator = (a1[0] - a2[0]) * (b1[1] - b2[1]) - (a1[1] - a2[1]) * (b1[0] - b2[0])
    if abs(denominator) <= _EPS:
        for candidate in (a1, a2, b1, b2):
            if _point_on_segment(candidate, a1, a2) and _point_on_segment(candidate, b1, b2):
                return candidate
        return None

    det_a = a1[0] * a2[1] - a1[1] * a2[0]
    det_b = b1[0] * b2[1] - b1[1] * b2[0]
    x = (det_a * (b1[0] - b2[0]) - (a1[0] - a2[0]) * det_b) / denominator
    y = (det_a * (b1[1] - b2[1]) - (a1[1] - a2[1]) * det_b) / denominator
    point = (x, y)
    if _point_on_segment(point, a1, a2) and _point_on_segment(point, b1, b2):
        return point
    return None


def _point_on_segment(point: tuple[float, float], start: tuple[float, float], end: tuple[float, float]) -> bool:
    return (
        abs(_orientation(start, end, point)) <= _EPS
        and min(start[0], end[0]) - _EPS <= point[0] <= max(start[0], end[0]) + _EPS
        and min(start[1], end[1]) - _EPS <= point[1] <= max(start[1], end[1]) + _EPS
    )


def _point_on_segment_strict(
    start: tuple[float, float],
    point: tuple[float, float],
    end: tuple[float, float],
) -> bool:
    if not _point_on_segment(point, start, end):
        return False
    return not (_same_xy(point, start) or _same_xy(point, end))


def _canonical_cycle_key(point_ids: list[str]) -> tuple[str, ...]:
    rotations = [tuple(point_ids[index:] + point_ids[:index]) for index in range(len(point_ids))]
    reverse_ids = list(reversed(point_ids))
    reverse_rotations = [
        tuple(reverse_ids[index:] + reverse_ids[:index]) for index in range(len(reverse_ids))
    ]
    return min(rotations + reverse_rotations)


def _format_polygonize_failure(diagnostics: dict[str, object], reason: str) -> str:
    return (
        "闭合面生成失败："
        f"{reason}；"
        f" candidate_faces={diagnostics['candidate_face_count']}；"
        f" dangles={diagnostics['dangle_count']}；"
        f" cuts={diagnostics['cut_count']}；"
        f" invalids={diagnostics['invalid_count']}；"
        f" unmapped_segments={diagnostics.get('missing_segment_count', 0)}。"
    )


def _create_unique_numbered_id(existing_ids: Iterable[str], base_id: str) -> str:
    existing = set(existing_ids)
    index = 1
    while True:
        candidate = f"{base_id}{index}"
        if candidate not in existing:
            return candidate
        index += 1


def _require_point(geometry: GeometryModel, point_id: str) -> GeometryPoint:
    for point in geometry.points:
        if point.id == point_id:
            return point
    raise ValueError(f"Unknown sketch point id: {point_id}")


def _require_edge(geometry: GeometryModel, edge_id: str) -> GeometryEdge:
    for edge in geometry.edges:
        if edge.id == edge_id:
            return edge
    raise ValueError(f"Unknown sketch edge id: {edge_id}")


def _edge_exists_between(geometry: GeometryModel, start_point_id: str, end_point_id: str) -> bool:
    endpoints = {start_point_id, end_point_id}
    return any({edge.start_point_id, edge.end_point_id} == endpoints for edge in geometry.edges)


def _connected_components(
    participating_points: set[str],
    adjacency: dict[str, list[tuple[str, str]]],
) -> list[set[str]]:
    remaining = set(participating_points)
    components: list[set[str]] = []
    while remaining:
        start = next(iter(remaining))
        queue: deque[str] = deque([start])
        component: set[str] = set()
        while queue:
            point_id = queue.popleft()
            if point_id in component:
                continue
            component.add(point_id)
            for neighbor_id, _ in adjacency[point_id]:
                if neighbor_id not in component:
                    queue.append(neighbor_id)
        components.append(component)
        remaining -= component
    return components


def _component_sort_key(points: list[tuple[float, float]]) -> tuple[float, float, float, float]:
    xs = [point[0] for point in points]
    ys = [point[1] for point in points]
    return (min(xs), min(ys), max(xs), max(ys))


def _signed_area_xy(points: list[tuple[float, float]]) -> float:
    area = 0.0
    for index, point in enumerate(points):
        next_point = points[(index + 1) % len(points)]
        area += point[0] * next_point[1] - next_point[0] * point[1]
    return 0.5 * area


def _orientation(a: tuple[float, float], b: tuple[float, float], c: tuple[float, float]) -> float:
    return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])


def _point_xy(point: GeometryPoint) -> tuple[float, float]:
    return float(point.x), float(point.y)


def _same_xy(a: tuple[float, float], b: tuple[float, float]) -> bool:
    return abs(a[0] - b[0]) <= _EPS and abs(a[1] - b[1]) <= _EPS


def _coord_key(coord: tuple[float, float]) -> tuple[int, int]:
    return (round(coord[0] / _EPS), round(coord[1] / _EPS))


def _canonical_segment_key(
    start: tuple[float, float],
    end: tuple[float, float],
) -> tuple[tuple[int, int], tuple[int, int]]:
    start_key = _coord_key(start)
    end_key = _coord_key(end)
    return tuple(sorted((start_key, end_key)))


def _fmt(value: float) -> str:
    return f"{value:.6g}"
