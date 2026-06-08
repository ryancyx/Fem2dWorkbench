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


GEOMETRY_TOLERANCE = 1.0e-8


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


def normalize_edges_by_embedded_points(geometry: GeometryModel) -> dict[str, int]:
    point_by_id = {point.id: point for point in geometry.points}
    new_edges: list[GeometryEdge] = []
    created_segment_keys: dict[frozenset[str], str] = {}
    split_edge_count = 0
    created_edge_count = 0
    reused_segment_count = 0

    for edge in geometry.edges:
        start_xy = _point_xy(point_by_id[edge.start_point_id])
        end_xy = _point_xy(point_by_id[edge.end_point_id])
        embedded_points: list[tuple[float, str]] = []
        for point in geometry.points:
            if point.id in {edge.start_point_id, edge.end_point_id}:
                continue
            t = _point_projection_parameter(_point_xy(point), start_xy, end_xy)
            if t is None:
                continue
            if t <= GEOMETRY_TOLERANCE or t >= 1.0 - GEOMETRY_TOLERANCE:
                continue
            embedded_points.append((t, point.id))

        if not embedded_points:
            if _append_edge_if_new(new_edges, created_segment_keys, edge.id, edge.start_point_id, edge.end_point_id):
                created_edge_count += 1
            else:
                reused_segment_count += 1
            continue

        split_edge_count += 1
        unique_embedded_points: list[tuple[float, str]] = []
        seen_point_ids: set[str] = set()
        for t, point_id in sorted(embedded_points, key=lambda item: (item[0], item[1])):
            if point_id in seen_point_ids:
                continue
            seen_point_ids.add(point_id)
            unique_embedded_points.append((t, point_id))

        ordered_point_ids = [edge.start_point_id] + [point_id for _, point_id in unique_embedded_points] + [edge.end_point_id]
        segment_index = 1
        for start_point_id, end_point_id in zip(ordered_point_ids[:-1], ordered_point_ids[1:]):
            if start_point_id == end_point_id:
                continue
            segment_id = f"{edge.id}_{segment_index}"
            if _append_edge_if_new(new_edges, created_segment_keys, segment_id, start_point_id, end_point_id):
                created_edge_count += 1
            else:
                reused_segment_count += 1
            segment_index += 1

    geometry.edges = new_edges
    geometry.faces = []
    stats = {
        "split_edge_count": split_edge_count,
        "created_edge_count": created_edge_count,
        "reused_segment_count": reused_segment_count,
        "final_edge_count": len(new_edges),
    }
    geometry._normalization_stats = stats
    return stats


def can_build_single_closed_face(geometry: GeometryModel) -> bool:
    try:
        candidate = _clone_geometry(geometry)
        return len(_extract_face_loops(candidate, require_all_edges=False)) == 1
    except ValueError:
        return False


def can_build_closed_faces(geometry: GeometryModel) -> bool:
    return len(geometry.points) >= 3 and len(geometry.edges) >= 3


def build_geometry_diagnostics_text(geometry: GeometryModel) -> str:
    diagnostics = _analyze_geometry_topology(geometry)
    lines = [
        f"point_count={diagnostics['point_count']}",
        f"edge_count={diagnostics['edge_count']}",
        f"candidate_face_count={diagnostics['candidate_face_count']}",
        f"dangles={diagnostics['dangle_count']}",
        f"cuts={diagnostics['cut_count']}",
        f"invalids={diagnostics['invalid_count']}",
        f"embedded_point_hits={diagnostics['embedded_point_hits']}",
    ]
    if diagnostics["duplicate_edge_groups"]:
        duplicate_rows = ["/".join(group["edge_ids"]) for group in diagnostics["duplicate_edge_groups"]]
        lines.append(f"duplicate_edges={'; '.join(duplicate_rows)}")
    if diagnostics["pairwise_edge_issues"]:
        issue_rows = [
            f"{row['edge_ids'][0]}/{row['edge_ids'][1]}@{row['kind']}"
            for row in diagnostics["pairwise_edge_issues"]
        ]
        lines.append(f"edge_issues={'; '.join(issue_rows)}")
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
    previous_section_by_edge_set = {
        frozenset(face.edge_ids): face.section_id
        for face in geometry.faces
        if face.section_id
    }
    previous_section_by_point_set = {
        frozenset(face.point_ids): face.section_id
        for face in geometry.faces
        if face.section_id and face.point_ids
    }
    loop_rows = _extract_face_loops(geometry, require_all_edges=True)
    geometry.faces = []
    for index, loop_row in enumerate(loop_rows, start=1):
        section_id = previous_section_by_edge_set.get(frozenset(loop_row.edge_ids), "")
        if not section_id:
            section_id = previous_section_by_point_set.get(frozenset(loop_row.point_ids), "")
        geometry.faces.append(
            GeometryFace(
                id=f"f{index}",
                edge_ids=list(loop_row.edge_ids),
                point_ids=list(loop_row.point_ids),
                section_id=section_id,
            )
        )
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
    normalize_edges_by_embedded_points(geometry)
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

    pairwise_edge_issues = _find_pairwise_edge_issues(geometry, point_by_id)
    if pairwise_edge_issues:
        first_issue = pairwise_edge_issues[0]
        raise ValueError(
            "闭合面生成失败：检测到未节点化交叉或重叠边。"
            f" edge_ids={first_issue['edge_ids'][0]}/{first_issue['edge_ids'][1]};"
            f" kind={first_issue['kind']};"
            f" detail={first_issue['detail']}。"
        )

    if len(geometry.edges) < 3:
        raise ValueError("闭合面生成失败：至少需要 3 条边。")

    if LineString is not None and unary_union is not None and polygonize_full is not None:
        loop_rows, diagnostics = _extract_face_loops_with_shapely(geometry, point_by_id)
    else:
        loop_rows, diagnostics = _extract_face_loops_fallback(geometry, point_by_id)

    if not loop_rows:
        raise ValueError(_format_face_failure(diagnostics, "未识别到任何闭合面"))
    if require_all_edges and (diagnostics["dangle_count"] or diagnostics["cut_count"] or diagnostics["invalid_count"]):
        raise ValueError(_format_face_failure(diagnostics, "线网中仍有未参与成面的边"))
    loop_rows.sort(key=lambda row: row.sort_key)
    geometry._face_build_stats = diagnostics
    return loop_rows


def _extract_face_loops_with_shapely(
    geometry: GeometryModel,
    point_by_id: dict[str, GeometryPoint],
) -> tuple[list[_FaceLoop], dict[str, int]]:
    lines = [
        LineString(
            [
                _point_xy(point_by_id[edge.start_point_id]),
                _point_xy(point_by_id[edge.end_point_id]),
            ]
        )
        for edge in geometry.edges
    ]
    merged = unary_union(lines)
    polygons, dangles, cuts, invalids = polygonize_full(merged)
    loop_rows: list[_FaceLoop] = []
    edge_lookup = _edge_lookup_by_points(geometry)
    point_lookup = _point_lookup_by_coordinates(point_by_id)
    for polygon in polygons.geoms:
        coords = list(polygon.exterior.coords)
        point_ids, edge_ids = _map_polygon_coords_to_geometry(coords, point_lookup, edge_lookup)
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
) -> tuple[list[_FaceLoop], dict[str, int]]:
    adjacency = _build_sorted_adjacency(geometry, point_by_id)
    edge_id_by_endpoint_pair = {
        frozenset((edge.start_point_id, edge.end_point_id)): edge.id for edge in geometry.edges
    }
    visited_half_edges: set[tuple[str, str]] = set()
    candidate_faces: list[_FaceLoop] = []
    for edge in geometry.edges:
        for start_point_id, end_point_id in (
            (edge.start_point_id, edge.end_point_id),
            (edge.end_point_id, edge.start_point_id),
        ):
            if (start_point_id, end_point_id) in visited_half_edges:
                continue
            try:
                point_ids, edge_ids = _trace_face_cycle(
                    start_point_id,
                    end_point_id,
                    adjacency,
                    edge_id_by_endpoint_pair,
                )
            except ValueError:
                continue
            directed_edges = list(zip(point_ids, point_ids[1:] + [point_ids[0]]))
            for directed_edge in directed_edges:
                visited_half_edges.add(directed_edge)
            ordered_points = [_point_xy(point_by_id[point_id]) for point_id in point_ids]
            signed_area = _signed_area_xy(ordered_points)
            if abs(signed_area) <= GEOMETRY_TOLERANCE or signed_area < 0.0:
                continue
            candidate_faces.append(
                _FaceLoop(
                    edge_ids=edge_ids,
                    point_ids=point_ids,
                    ordered_points=ordered_points,
                    sort_key=_component_sort_key(ordered_points),
                )
            )

    unique_faces: list[_FaceLoop] = []
    seen_keys: set[tuple[str, ...]] = set()
    for face in candidate_faces:
        face_key = _canonical_cycle_key(face.point_ids)
        if face_key in seen_keys:
            continue
        seen_keys.add(face_key)
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
        if start_degree <= 1 or end_degree <= 1:
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
    participating_points: set[str] = set()
    for edge in geometry.edges:
        if edge.start_point_id not in point_by_id or edge.end_point_id not in point_by_id:
            raise ValueError(f"Sketch edge {edge.id!r} references unknown points")
        adjacency[edge.start_point_id].append((edge.end_point_id, edge.id))
        adjacency[edge.end_point_id].append((edge.start_point_id, edge.id))
        participating_points.add(edge.start_point_id)
        participating_points.add(edge.end_point_id)

    duplicate_edge_groups = _find_duplicate_edges(geometry)
    pairwise_edge_issues = _find_pairwise_edge_issues(geometry, point_by_id)
    embedded_point_hits = _count_embedded_points(geometry, point_by_id)
    candidate_face_count = 0
    dangle_count = 0
    cut_count = 0
    invalid_count = len(pairwise_edge_issues)
    if len(geometry.edges) >= 3 and not duplicate_edge_groups and not pairwise_edge_issues:
        temp_geometry = _clone_geometry(geometry)
        try:
            loops = _extract_face_loops(temp_geometry, require_all_edges=False)
            candidate_face_count = len(loops)
            stats = getattr(temp_geometry, "_face_build_stats", {})
            dangle_count = int(stats.get("dangle_count", 0))
            cut_count = int(stats.get("cut_count", 0))
            invalid_count += int(stats.get("invalid_count", 0))
        except ValueError:
            pass

    component_rows = []
    for index, component in enumerate(_connected_components(participating_points, adjacency), start=1):
        component_edge_ids = [
            edge.id
            for edge in geometry.edges
            if edge.start_point_id in component and edge.end_point_id in component
        ]
        component_rows.append(
            {
                "index": index,
                "point_ids": sorted(component),
                "node_count": len(component),
                "edge_count": len(component_edge_ids),
                "edge_ids": sorted(component_edge_ids),
            }
        )

    return {
        "point_count": len(geometry.points),
        "edge_count": len(geometry.edges),
        "components": component_rows,
        "duplicate_edge_groups": duplicate_edge_groups,
        "pairwise_edge_issues": pairwise_edge_issues,
        "embedded_point_hits": embedded_point_hits,
        "candidate_face_count": candidate_face_count,
        "dangle_count": dangle_count,
        "cut_count": cut_count,
        "invalid_count": invalid_count,
    }


def _count_embedded_points(
    geometry: GeometryModel,
    point_by_id: dict[str, GeometryPoint],
) -> int:
    embedded_hit_count = 0
    for edge in geometry.edges:
        start_xy = _point_xy(point_by_id[edge.start_point_id])
        end_xy = _point_xy(point_by_id[edge.end_point_id])
        for point in geometry.points:
            if point.id in {edge.start_point_id, edge.end_point_id}:
                continue
            t = _point_projection_parameter(_point_xy(point), start_xy, end_xy)
            if t is None:
                continue
            if GEOMETRY_TOLERANCE < t < 1.0 - GEOMETRY_TOLERANCE:
                embedded_hit_count += 1
    return embedded_hit_count


def _point_projection_parameter(
    point: tuple[float, float],
    start: tuple[float, float],
    end: tuple[float, float],
) -> float | None:
    dx = end[0] - start[0]
    dy = end[1] - start[1]
    length_sq = dx * dx + dy * dy
    if length_sq <= GEOMETRY_TOLERANCE:
        return None
    t = ((point[0] - start[0]) * dx + (point[1] - start[1]) * dy) / length_sq
    projection = (start[0] + t * dx, start[1] + t * dy)
    if _distance(point, projection) > GEOMETRY_TOLERANCE:
        return None
    if not _point_on_segment(projection, start, end):
        return None
    return t


def _append_edge_if_new(
    edge_rows: list[GeometryEdge],
    segment_keys: dict[frozenset[str], str],
    edge_id: str,
    start_point_id: str,
    end_point_id: str,
) -> bool:
    if start_point_id == end_point_id:
        return False
    segment_key = frozenset((start_point_id, end_point_id))
    if segment_key in segment_keys:
        return False
    segment_keys[segment_key] = edge_id
    edge_rows.append(
        GeometryEdge(
            id=edge_id,
            start_point_id=start_point_id,
            end_point_id=end_point_id,
        )
    )
    return True


def _build_sorted_adjacency(
    geometry: GeometryModel,
    point_by_id: dict[str, GeometryPoint],
) -> dict[str, list[str]]:
    adjacency: dict[str, list[str]] = defaultdict(list)
    for edge in geometry.edges:
        adjacency[edge.start_point_id].append(edge.end_point_id)
        adjacency[edge.end_point_id].append(edge.start_point_id)
    for point_id, neighbors in adjacency.items():
        adjacency[point_id] = sorted(
            set(neighbors),
            key=lambda neighbor_id: (
                math.atan2(
                    point_by_id[neighbor_id].y - point_by_id[point_id].y,
                    point_by_id[neighbor_id].x - point_by_id[point_id].x,
                ),
                neighbor_id,
            ),
        )
    return adjacency


def _trace_face_cycle(
    start_point_id: str,
    end_point_id: str,
    adjacency: dict[str, list[str]],
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
            raise ValueError("duplicate directed edge traversal")
        seen_directed_edges.add(current)
        point_ids.append(current_end_id)
        edge_id = edge_id_by_endpoint_pair.get(frozenset((current_start_id, current_end_id)))
        if edge_id is None:
            raise ValueError("missing mapped edge")
        edge_ids.append(edge_id)
        next_point_id = _choose_next_face_neighbor(current_start_id, current_end_id, adjacency)
        current = (current_end_id, next_point_id)
        if current == start:
            break
        if len(point_ids) > len(edge_id_by_endpoint_pair) + 2:
            raise ValueError("trace exceeded edge count")
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
        raise ValueError("neighbor ordering mismatch")
    previous_index = neighbors.index(previous_point_id)
    return neighbors[(previous_index - 1) % len(neighbors)]


def _edge_lookup_by_points(geometry: GeometryModel) -> dict[tuple[tuple[int, int], tuple[int, int]], str]:
    point_by_id = {point.id: point for point in geometry.points}
    lookup: dict[tuple[tuple[int, int], tuple[int, int]], str] = {}
    for edge in geometry.edges:
        lookup[_canonical_segment_key(_point_xy(point_by_id[edge.start_point_id]), _point_xy(point_by_id[edge.end_point_id]))] = edge.id
    return lookup


def _point_lookup_by_coordinates(point_by_id: dict[str, GeometryPoint]) -> dict[tuple[int, int], str]:
    return {_coord_key(_point_xy(point)): point_id for point_id, point in point_by_id.items()}


def _map_polygon_coords_to_geometry(
    coords: list[tuple[float, float]],
    point_lookup: dict[tuple[int, int], str],
    edge_lookup: dict[tuple[tuple[int, int], tuple[int, int]], str],
) -> tuple[list[str], list[str]]:
    if len(coords) < 4:
        raise ValueError("polygonize returned invalid face")
    unique_coords = coords[:-1]
    point_ids: list[str] = []
    edge_ids: list[str] = []
    for coord in unique_coords:
        point_id = point_lookup.get(_coord_key(coord))
        if point_id is None:
            raise ValueError("面顶点无法映射到原始几何点，请检查是否仍有未节点化边。")
        point_ids.append(point_id)
    for index, start_coord in enumerate(unique_coords):
        end_coord = unique_coords[(index + 1) % len(unique_coords)]
        edge_id = edge_lookup.get(_canonical_segment_key(start_coord, end_coord))
        if edge_id is None:
            raise ValueError("面边界段无法映射到原始几何边，请检查是否存在重叠边。")
        edge_ids.append(edge_id)
    return point_ids, edge_ids


def _find_duplicate_edges(geometry: GeometryModel) -> list[dict[str, object]]:
    grouped: dict[frozenset[str], list[str]] = defaultdict(list)
    for edge in geometry.edges:
        grouped[frozenset((edge.start_point_id, edge.end_point_id))].append(edge.id)
    return [
        {"point_ids": sorted(endpoint_pair), "edge_ids": edge_ids}
        for endpoint_pair, edge_ids in grouped.items()
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


def _collinear_overlap_kind(
    a1: tuple[float, float],
    a2: tuple[float, float],
    b1: tuple[float, float],
    b2: tuple[float, float],
) -> str | None:
    if abs(_orientation(a1, a2, b1)) > GEOMETRY_TOLERANCE or abs(_orientation(a1, a2, b2)) > GEOMETRY_TOLERANCE:
        return None
    if max(min(a1[0], a2[0]), min(b1[0], b2[0])) > min(max(a1[0], a2[0]), max(b1[0], b2[0])) + GEOMETRY_TOLERANCE:
        return None
    if max(min(a1[1], a2[1]), min(b1[1], b2[1])) > min(max(a1[1], a2[1]), max(b1[1], b2[1])) + GEOMETRY_TOLERANCE:
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
    if abs(denominator) <= GEOMETRY_TOLERANCE:
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
        (_same_xy(intersection, a1) or _same_xy(intersection, a2))
        and (_same_xy(intersection, b1) or _same_xy(intersection, b2))
    )


def _format_face_failure(diagnostics: dict[str, int], reason: str) -> str:
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


def _clone_geometry(geometry: GeometryModel) -> GeometryModel:
    return GeometryModel(
        points=[GeometryPoint(id=point.id, x=point.x, y=point.y) for point in geometry.points],
        edges=[
            GeometryEdge(
                id=edge.id,
                start_point_id=edge.start_point_id,
                end_point_id=edge.end_point_id,
            )
            for edge in geometry.edges
        ],
        faces=[
            GeometryFace(
                id=face.id,
                edge_ids=list(face.edge_ids),
                point_ids=list(face.point_ids),
                section_id=face.section_id,
            )
            for face in geometry.faces
        ],
    )


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


def _point_on_segment(point: tuple[float, float], start: tuple[float, float], end: tuple[float, float]) -> bool:
    return (
        abs(_orientation(start, end, point)) <= GEOMETRY_TOLERANCE
        and min(start[0], end[0]) - GEOMETRY_TOLERANCE <= point[0] <= max(start[0], end[0]) + GEOMETRY_TOLERANCE
        and min(start[1], end[1]) - GEOMETRY_TOLERANCE <= point[1] <= max(start[1], end[1]) + GEOMETRY_TOLERANCE
    )


def _point_on_segment_strict(
    start: tuple[float, float],
    point: tuple[float, float],
    end: tuple[float, float],
) -> bool:
    return _point_on_segment(point, start, end) and not (_same_xy(point, start) or _same_xy(point, end))


def _canonical_cycle_key(point_ids: list[str]) -> tuple[str, ...]:
    rotations = [tuple(point_ids[index:] + point_ids[:index]) for index in range(len(point_ids))]
    reverse_ids = list(reversed(point_ids))
    reverse_rotations = [
        tuple(reverse_ids[index:] + reverse_ids[:index]) for index in range(len(reverse_ids))
    ]
    return min(rotations + reverse_rotations)


def _point_xy(point: GeometryPoint) -> tuple[float, float]:
    return float(point.x), float(point.y)


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


def _same_xy(a: tuple[float, float], b: tuple[float, float]) -> bool:
    return abs(a[0] - b[0]) <= GEOMETRY_TOLERANCE and abs(a[1] - b[1]) <= GEOMETRY_TOLERANCE


def _distance(a: tuple[float, float], b: tuple[float, float]) -> float:
    return math.hypot(b[0] - a[0], b[1] - a[1])


def _coord_key(coord: tuple[float, float]) -> tuple[int, int]:
    return (
        round(coord[0] / GEOMETRY_TOLERANCE),
        round(coord[1] / GEOMETRY_TOLERANCE),
    )


def _canonical_segment_key(
    start: tuple[float, float],
    end: tuple[float, float],
) -> tuple[tuple[int, int], tuple[int, int]]:
    start_key = _coord_key(start)
    end_key = _coord_key(end)
    return tuple(sorted((start_key, end_key)))


def _fmt(value: float) -> str:
    return f"{value:.6g}"
