from __future__ import annotations

import math
from typing import Iterable

try:
    import gmsh  # type: ignore
except ImportError:  # pragma: no cover - depends on local environment
    gmsh = None

from core.engineering.geometry import GeometryModel
from core.engineering.mesh_model import MeshElement, MeshModel, MeshNode
from core.meshing.quality_sketch_mesher import (
    BoundaryLoop,
    _reconstruct_boundary_loops_from_geometry,
)
from services.mesh_quality_service import (
    build_mesh_quality_summary,
    find_unused_mesh_node_ids,
    validate_mesh_covers_geometry,
)


_EPS = 1.0e-12
_GMSH_MISSING_MESSAGE = (
    "Gmsh meshing backend is not installed. Please install package 'gmsh' "
    "to generate CST meshes."
)


def generate_gmsh_cst_mesh(
    geometry: GeometryModel,
    target_size: float = 0.2,
    max_area: float | None = None,
    min_angle: float = 25.0,
) -> MeshModel:
    if gmsh is None:
        raise ValueError(_GMSH_MISSING_MESSAGE)
    if target_size <= 0.0:
        raise ValueError("target_size must be positive")
    if max_area is not None and max_area <= 0.0:
        raise ValueError("max_area must be positive when provided")
    if min_angle <= 0.0 or min_angle >= 180.0:
        raise ValueError("min_angle must be between 0 and 180")

    loops = _reconstruct_boundary_loops_from_geometry(geometry)
    polygon_area = sum(abs(_signed_area(loop.ordered_points)) for loop in loops)
    if polygon_area <= _EPS:
        raise ValueError("Geometry loop area must be positive")

    gmsh.initialize()
    try:
        gmsh.option.setNumber("General.Terminal", 0)
        mesh_data = _generate_with_gmsh_model(
            geometry=geometry,
            loops=loops,
            target_size=target_size,
        )
    except Exception as exc:
        if isinstance(exc, ValueError):
            raise
        raise ValueError(f"Gmsh CST mesh generation failed: {exc}") from exc
    finally:
        gmsh.finalize()

    mesh = _build_mesh_model(
        geometry=geometry,
        loops=loops,
        target_size=target_size,
        max_area=max_area,
        min_angle=min_angle,
        polygon_area=polygon_area,
        node_coordinates=mesh_data["node_coordinates"],
        triangle_rows=mesh_data["triangle_rows"],
    )
    _validate_gmsh_mesh_integrity(geometry, loops, mesh)
    return mesh


def _generate_with_gmsh_model(
    geometry: GeometryModel,
    loops: list[BoundaryLoop],
    target_size: float,
) -> dict[str, object]:
    gmsh.model.add("fem2dworkbench_part")
    gmsh.option.setNumber("Mesh.MeshSizeMin", float(target_size))
    gmsh.option.setNumber("Mesh.MeshSizeMax", float(target_size))
    gmsh.option.setNumber("Mesh.ElementOrder", 1)
    gmsh.option.setNumber("Mesh.RecombineAll", 0)

    point_tags: dict[str, int] = {}
    for point in geometry.points:
        point_tags[point.id] = gmsh.model.geo.addPoint(
            float(point.x),
            float(point.y),
            0.0,
            float(target_size),
        )

    edge_by_id = {edge.id: edge for edge in geometry.edges}
    line_tags_by_edge_id: dict[str, int] = {}
    for edge in geometry.edges:
        line_tags_by_edge_id[edge.id] = gmsh.model.geo.addLine(
            point_tags[edge.start_point_id],
            point_tags[edge.end_point_id],
        )

    surface_tags_by_face_id: dict[str, int] = {}
    for loop in loops:
        ordered_line_tags: list[int] = []
        for index, edge_id in enumerate(loop.ordered_edge_ids):
            edge = edge_by_id[edge_id]
            start_point_id = loop.ordered_point_ids[index]
            end_point_id = loop.ordered_point_ids[(index + 1) % len(loop.ordered_point_ids)]
            line_tag = line_tags_by_edge_id[edge_id]
            if edge.start_point_id == start_point_id and edge.end_point_id == end_point_id:
                ordered_line_tags.append(line_tag)
            elif edge.start_point_id == end_point_id and edge.end_point_id == start_point_id:
                ordered_line_tags.append(-line_tag)
            else:
                raise ValueError(f"Geometry edge {edge_id!r} does not match the face loop order")
        curve_loop_tag = gmsh.model.geo.addCurveLoop(ordered_line_tags)
        surface_tags_by_face_id[loop.face_id] = gmsh.model.geo.addPlaneSurface([curve_loop_tag])

    gmsh.model.geo.synchronize()

    last_error: Exception | None = None
    for algorithm in (6, 5, 8):
        try:
            gmsh.option.setNumber("Mesh.Algorithm", algorithm)
            gmsh.model.mesh.clear()
            gmsh.model.mesh.generate(2)
            break
        except Exception as exc:  # pragma: no cover - depends on gmsh internals
            last_error = exc
    else:
        assert last_error is not None
        raise last_error

    node_tags, node_coords, _ = gmsh.model.mesh.getNodes()
    gmsh_tag_to_mesh_id: dict[int, int] = {}
    node_coordinates: dict[int, tuple[float, float]] = {}
    for mesh_node_id, node_tag in enumerate(node_tags, start=1):
        coord_index = (mesh_node_id - 1) * 3
        x = float(node_coords[coord_index])
        y = float(node_coords[coord_index + 1])
        gmsh_tag_to_mesh_id[int(node_tag)] = mesh_node_id
        node_coordinates[mesh_node_id] = (x, y)

    triangle_rows: list[tuple[list[int], str]] = []
    for face_id, surface_tag in surface_tags_by_face_id.items():
        element_types, _, element_node_tags = gmsh.model.mesh.getElements(2, surface_tag)
        for element_type, node_tags_for_type in zip(element_types, element_node_tags):
            if int(element_type) != 2:
                continue
            tags = [int(tag) for tag in node_tags_for_type]
            for index in range(0, len(tags), 3):
                try:
                    triangle_rows.append(
                        (
                            [
                                gmsh_tag_to_mesh_id[tags[index]],
                                gmsh_tag_to_mesh_id[tags[index + 1]],
                                gmsh_tag_to_mesh_id[tags[index + 2]],
                            ],
                            face_id,
                        )
                    )
                except KeyError as exc:
                    raise ValueError(
                        f"Gmsh triangle references unknown node tag {exc.args[0]!r}"
                    ) from exc

    if not triangle_rows:
        raise ValueError("Gmsh did not generate any 3-node triangle elements")

    return {
        "node_coordinates": node_coordinates,
        "triangle_rows": triangle_rows,
    }


def _build_mesh_model(
    geometry: GeometryModel,
    loops: list[BoundaryLoop],
    target_size: float,
    max_area: float | None,
    min_angle: float,
    polygon_area: float,
    node_coordinates: dict[int, tuple[float, float]],
    triangle_rows: list[tuple[list[int], str]],
) -> MeshModel:
    nodes = [
        MeshNode(id=node_id, x=coord[0], y=coord[1])
        for node_id, coord in sorted(node_coordinates.items())
    ]

    elements: list[MeshElement] = []
    element_areas: list[float] = []
    for element_id, (node_ids, face_id) in enumerate(triangle_rows, start=1):
        coords = [node_coordinates[node_id] for node_id in node_ids]
        signed_area = _signed_area(coords)
        if abs(signed_area) <= _EPS:
            raise ValueError("Gmsh produced degenerate triangle elements")
        if signed_area < 0.0:
            node_ids = [node_ids[0], node_ids[2], node_ids[1]]
            signed_area = -signed_area
        element_areas.append(signed_area)
        elements.append(
            MeshElement(
                id=element_id,
                node_ids=list(node_ids),
                element_type="CST",
                source_face_id=face_id,
            )
        )

    geometry_point_to_mesh_node_ids = _map_geometry_points_to_mesh_nodes(
        geometry=geometry,
        node_coordinates=node_coordinates,
        target_size=target_size,
    )
    geometry_edge_to_mesh_node_ids = _map_geometry_edges_to_mesh_nodes(
        geometry=geometry,
        node_coordinates=node_coordinates,
        target_size=target_size,
    )
    geometry_edge_to_mesh_element_edges = _map_geometry_edges_to_element_edges(
        elements=elements,
        geometry_edge_to_mesh_node_ids=geometry_edge_to_mesh_node_ids,
    )

    mesh_area = sum(element_areas)
    relative_area_error = abs(mesh_area - polygon_area) / polygon_area
    p10_area = _percentile(sorted(element_areas), 0.10)
    p90_area = _percentile(sorted(element_areas), 0.90)
    warnings: list[str] = []
    p90_p10_ratio = p90_area / max(p10_area, _EPS)
    if p90_p10_ratio > 8.0:
        warnings.append("Element area spread is high; consider increasing target edge length")

    mesh = MeshModel(
        nodes=nodes,
        elements=elements,
        geometry_point_to_mesh_node_ids=geometry_point_to_mesh_node_ids,
        geometry_edge_to_mesh_node_ids=geometry_edge_to_mesh_node_ids,
        geometry_edge_to_mesh_element_edges=geometry_edge_to_mesh_element_edges,
        metadata={
            "mesh_type": "gmsh_cst",
            "mesher_backend": "gmsh",
            "gmsh_version": getattr(gmsh, "__version__", ""),
            "target_size": float(target_size),
            "max_area": max_area,
            "min_angle": float(min_angle),
            "polygon_area": polygon_area,
            "mesh_area": mesh_area,
            "relative_area_error": relative_area_error,
            "node_count": len(nodes),
            "element_count": len(elements),
            "min_element_area": min(element_areas),
            "max_element_area": max(element_areas),
            "avg_element_area": mesh_area / len(elements),
            "p10_element_area": p10_area,
            "p90_element_area": p90_area,
            "p90_p10_area_ratio": p90_p10_ratio,
            "warnings": warnings,
            "face_ids": [loop.face_id for loop in loops],
        },
    )
    quality = build_mesh_quality_summary(mesh)
    mesh.metadata["min_angle"] = quality.min_angle
    mesh.metadata["max_angle"] = quality.max_angle
    mesh.metadata["warning_count"] = len(warnings)
    return mesh


def _map_geometry_points_to_mesh_nodes(
    geometry: GeometryModel,
    node_coordinates: dict[int, tuple[float, float]],
    target_size: float,
) -> dict[str, list[int]]:
    tolerance = _mapping_tolerance(target_size)
    mapping: dict[str, list[int]] = {}
    for point in geometry.points:
        nearest_distance = math.inf
        nearest_node_id: int | None = None
        for node_id, coord in node_coordinates.items():
            distance = _distance((point.x, point.y), coord)
            if distance < nearest_distance:
                nearest_distance = distance
                nearest_node_id = node_id
        if nearest_node_id is None or nearest_distance > tolerance:
            raise ValueError(f"Could not map geometry point {point.id!r} to Gmsh mesh node")
        mapping[point.id] = [nearest_node_id]
    return mapping


def _map_geometry_edges_to_mesh_nodes(
    geometry: GeometryModel,
    node_coordinates: dict[int, tuple[float, float]],
    target_size: float,
) -> dict[str, list[int]]:
    tolerance = _mapping_tolerance(target_size)
    point_by_id = {point.id: point for point in geometry.points}
    mapping: dict[str, list[int]] = {}

    for edge in geometry.edges:
        start = point_by_id[edge.start_point_id]
        end = point_by_id[edge.end_point_id]
        start_xy = (float(start.x), float(start.y))
        end_xy = (float(end.x), float(end.y))
        edge_length_sq = max(
            (end_xy[0] - start_xy[0]) ** 2 + (end_xy[1] - start_xy[1]) ** 2,
            _EPS,
        )
        on_edge_nodes: list[tuple[float, int]] = []
        for node_id, coord in node_coordinates.items():
            t = (
                (coord[0] - start_xy[0]) * (end_xy[0] - start_xy[0])
                + (coord[1] - start_xy[1]) * (end_xy[1] - start_xy[1])
            ) / edge_length_sq
            if t < -tolerance or t > 1.0 + tolerance:
                continue
            if _distance_point_to_segment(coord, start_xy, end_xy) <= tolerance:
                on_edge_nodes.append((min(1.0, max(0.0, t)), node_id))

        on_edge_nodes.sort(key=lambda item: (item[0], item[1]))
        ordered_node_ids: list[int] = []
        for _, node_id in on_edge_nodes:
            if node_id not in ordered_node_ids:
                ordered_node_ids.append(node_id)
        if len(ordered_node_ids) < 2:
            raise ValueError(f"Geometry edge {edge.id!r} does not map to enough Gmsh mesh nodes")
        mapping[edge.id] = ordered_node_ids

    return mapping


def _map_geometry_edges_to_element_edges(
    elements: list[MeshElement],
    geometry_edge_to_mesh_node_ids: dict[str, list[int]],
) -> dict[str, list[tuple[int, int, int]]]:
    edge_index: dict[frozenset[int], list[tuple[int, int, int]]] = {}
    for element in elements:
        for local_a, local_b in ((0, 1), (1, 2), (2, 0)):
            edge_key = frozenset((element.node_ids[local_a], element.node_ids[local_b]))
            edge_index.setdefault(edge_key, []).append((element.id, local_a, local_b))

    mapping: dict[str, list[tuple[int, int, int]]] = {}
    for edge_id, node_ids in geometry_edge_to_mesh_node_ids.items():
        edge_mappings: list[tuple[int, int, int]] = []
        for node_a, node_b in zip(node_ids[:-1], node_ids[1:]):
            triangle_edges = edge_index.get(frozenset((node_a, node_b)), [])
            if not triangle_edges:
                raise ValueError(f"Geometry edge {edge_id!r} is not preserved as mesh boundary")
            for triangle_edge in triangle_edges:
                if triangle_edge not in edge_mappings:
                    edge_mappings.append(triangle_edge)
        if not edge_mappings:
            raise ValueError(f"Geometry edge {edge_id!r} is not preserved as mesh boundary")
        mapping[edge_id] = edge_mappings
    return mapping


def _validate_gmsh_mesh_integrity(
    geometry: GeometryModel,
    loops: list[BoundaryLoop],
    mesh: MeshModel,
) -> None:
    coverage = validate_mesh_covers_geometry(geometry, mesh, tolerance=0.03)
    if coverage.polygon_area <= _EPS:
        raise ValueError("Geometry polygon area must be positive")
    if coverage.mesh_area <= _EPS:
        raise ValueError("Gmsh mesh area must be positive")
    if coverage.relative_area_error > 0.03:
        raise ValueError("Gmsh mesh does not cover geometry face")
    if coverage.degenerate_element_count:
        raise ValueError("Gmsh mesh contains degenerate elements")
    unused_node_ids = find_unused_mesh_node_ids(mesh)
    if unused_node_ids:
        raise ValueError("Gmsh mesh contains unused nodes")
    if coverage.missing_edge_mapping_ids:
        raise ValueError(
            f"Geometry edge {coverage.missing_edge_mapping_ids[0]!r} is not preserved as mesh boundary"
        )
    if set(mesh.geometry_point_to_mesh_node_ids) != {point.id for point in geometry.points}:
        raise ValueError("Not all geometry points are mapped to Gmsh mesh nodes")
    if set(mesh.geometry_edge_to_mesh_node_ids) != {edge.id for edge in geometry.edges}:
        raise ValueError("Not all geometry edges are mapped to Gmsh mesh nodes")
    if set(mesh.geometry_edge_to_mesh_element_edges) != {edge.id for edge in geometry.edges}:
        raise ValueError("Not all geometry edges are mapped to mesh element edges")
    expected_face_ids = {loop.face_id for loop in loops}
    actual_face_ids = {element.source_face_id for element in mesh.elements}
    if expected_face_ids - actual_face_ids:
        raise ValueError("Mesh elements are not tagged with every source face id")
    minimum_element_count = max(1, sum(max(1, len(loop.ordered_point_ids) - 2) for loop in loops))
    if len(mesh.elements) < minimum_element_count:
        raise ValueError("Gmsh generated too few triangle elements")

    quality = build_mesh_quality_summary(mesh)
    if quality.degenerate_element_count:
        raise ValueError("Gmsh mesh contains degenerate elements")


def _mapping_tolerance(target_size: float) -> float:
    return max(1.0e-8, target_size * 1.0e-6)


def _signed_area(points: Iterable[tuple[float, float]]) -> float:
    point_list = list(points)
    area = 0.0
    for index, point in enumerate(point_list):
        next_point = point_list[(index + 1) % len(point_list)]
        area += point[0] * next_point[1] - next_point[0] * point[1]
    return 0.5 * area


def _distance(a: tuple[float, float], b: tuple[float, float]) -> float:
    return math.hypot(b[0] - a[0], b[1] - a[1])


def _distance_point_to_segment(
    point: tuple[float, float],
    start: tuple[float, float],
    end: tuple[float, float],
) -> float:
    dx = end[0] - start[0]
    dy = end[1] - start[1]
    length_squared = dx * dx + dy * dy
    if length_squared <= _EPS:
        return _distance(point, start)
    t = ((point[0] - start[0]) * dx + (point[1] - start[1]) * dy) / length_squared
    t = max(0.0, min(1.0, t))
    closest = (start[0] + t * dx, start[1] + t * dy)
    return _distance(point, closest)


def _percentile(values: list[float], ratio: float) -> float:
    if not values:
        return 0.0
    if len(values) == 1:
        return values[0]
    position = ratio * (len(values) - 1)
    lower = int(math.floor(position))
    upper = int(math.ceil(position))
    if lower == upper:
        return values[lower]
    fraction = position - lower
    return values[lower] * (1.0 - fraction) + values[upper] * fraction
