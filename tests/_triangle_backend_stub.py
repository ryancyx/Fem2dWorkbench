from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass
class TriangleBackendStub:
    """Test-only triangle backend.

    It mimics constrained triangulation on a seeded simple polygon by ear clipping
    the provided PSLG boundary vertices. It is not used by production code.
    """

    def triangulate(self, input_data, options: str):
        vertices = np.asarray(input_data["vertices"], dtype=float)
        segments = np.asarray(input_data["segments"], dtype=int)
        ordered_indices = _order_loop_from_segments(segments)
        ordered_points = [tuple(vertices[index]) for index in ordered_indices]
        if _signed_area(ordered_points) < 0.0:
            ordered_indices.reverse()
            ordered_points.reverse()
        local_triangles = _ear_clip(ordered_points)
        global_triangles = np.asarray(
            [[ordered_indices[a], ordered_indices[b], ordered_indices[c]] for a, b, c in local_triangles],
            dtype=np.int32,
        )
        return {
            "vertices": vertices,
            "triangles": global_triangles,
            "segments": segments,
            "segment_markers": np.asarray(input_data.get("segment_markers", [])),
            "options": options,
        }


def install_fake_triangle_backend(monkeypatch, mesher_module) -> None:
    monkeypatch.setattr(mesher_module, "triangle_backend", TriangleBackendStub())


def _order_loop_from_segments(segments: np.ndarray) -> list[int]:
    adjacency: dict[int, list[int]] = {}
    for start, end in segments:
        adjacency.setdefault(int(start), []).append(int(end))
        adjacency.setdefault(int(end), []).append(int(start))
    if any(len(neighbors) != 2 for neighbors in adjacency.values()):
        raise ValueError("Stub backend requires a single closed loop PSLG")
    start_index = min(adjacency)
    previous_index: int | None = None
    current_index = start_index
    ordered = [start_index]
    while True:
        next_candidates = [item for item in adjacency[current_index] if item != previous_index]
        if not next_candidates:
            break
        next_index = next_candidates[0]
        previous_index, current_index = current_index, next_index
        if current_index == start_index:
            break
        ordered.append(current_index)
        if len(ordered) > len(adjacency) + 1:
            raise ValueError("Stub backend failed to reconstruct loop")
    return ordered


def _ear_clip(points: list[tuple[float, float]]) -> list[tuple[int, int, int]]:
    if len(points) < 3:
        raise ValueError("At least 3 points are required")
    remaining = list(range(len(points)))
    triangles: list[tuple[int, int, int]] = []
    guard = len(points) * len(points)
    iterations = 0
    while len(remaining) > 3:
        iterations += 1
        if iterations > guard:
            raise ValueError("Stub ear clipping failed")
        ear_found = False
        for local_index, current_index in enumerate(remaining):
            previous_index = remaining[local_index - 1]
            next_index = remaining[(local_index + 1) % len(remaining)]
            coords = [points[previous_index], points[current_index], points[next_index]]
            if _signed_area(coords) <= 1.0e-12:
                continue
            if any(
                _point_in_triangle(points[other_index], coords[0], coords[1], coords[2])
                for other_index in remaining
                if other_index not in {previous_index, current_index, next_index}
            ):
                continue
            triangles.append((previous_index, current_index, next_index))
            del remaining[local_index]
            ear_found = True
            break
        if not ear_found:
            raise ValueError("Stub ear clipping failed")
    triangles.append((remaining[0], remaining[1], remaining[2]))
    return triangles


def _point_in_triangle(
    point: tuple[float, float],
    a: tuple[float, float],
    b: tuple[float, float],
    c: tuple[float, float],
) -> bool:
    c1 = _orientation(point, a, b)
    c2 = _orientation(point, b, c)
    c3 = _orientation(point, c, a)
    has_negative = c1 < -1.0e-12 or c2 < -1.0e-12 or c3 < -1.0e-12
    has_positive = c1 > 1.0e-12 or c2 > 1.0e-12 or c3 > 1.0e-12
    return not (has_negative and has_positive)


def _signed_area(points: list[tuple[float, float]]) -> float:
    area = 0.0
    for index, point in enumerate(points):
        next_point = points[(index + 1) % len(points)]
        area += point[0] * next_point[1] - next_point[0] * point[1]
    return 0.5 * area


def _orientation(
    a: tuple[float, float],
    b: tuple[float, float],
    c: tuple[float, float],
) -> float:
    return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])
