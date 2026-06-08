from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

from services.solve_service import WorkbenchSolveResult


@dataclass(slots=True)
class NodeDisplacementRow:
    node_id: int
    x: float
    y: float
    ux: float
    uy: float
    u_magnitude: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "node_id": self.node_id,
            "x": self.x,
            "y": self.y,
            "ux": self.ux,
            "uy": self.uy,
            "u_magnitude": self.u_magnitude,
        }


@dataclass(slots=True)
class ElementResultRow:
    element_id: int
    node_ids: list[int]
    source_face_id: str | None
    strain_x: float
    strain_y: float
    strain_xy: float
    stress_x: float
    stress_y: float
    stress_xy: float
    von_mises: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "element_id": self.element_id,
            "node_ids": list(self.node_ids),
            "source_face_id": self.source_face_id,
            "strain_x": self.strain_x,
            "strain_y": self.strain_y,
            "strain_xy": self.strain_xy,
            "stress_x": self.stress_x,
            "stress_y": self.stress_y,
            "stress_xy": self.stress_xy,
            "von_mises": self.von_mises,
        }


@dataclass(slots=True)
class ResultSummary:
    node_count: int
    element_count: int
    max_displacement: float
    max_displacement_node_id: int | None
    max_von_mises: float
    max_von_mises_element_id: int | None
    warning_count: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "node_count": self.node_count,
            "element_count": self.element_count,
            "max_displacement": self.max_displacement,
            "max_displacement_node_id": self.max_displacement_node_id,
            "max_von_mises": self.max_von_mises,
            "max_von_mises_element_id": self.max_von_mises_element_id,
            "warning_count": self.warning_count,
        }


def build_node_displacement_rows(
    solution: WorkbenchSolveResult,
) -> list[NodeDisplacementRow]:
    rows: list[NodeDisplacementRow] = []
    node_displacements = solution.solver_result.node_displacements

    for node in solution.mesh.nodes:
        displacement = node_displacements.get(node.id)
        if displacement is None:
            raise ValueError(f"Missing displacement result for node_id {node.id!r}")

        ux, uy = displacement
        rows.append(
            NodeDisplacementRow(
                node_id=node.id,
                x=node.x,
                y=node.y,
                ux=float(ux),
                uy=float(uy),
                u_magnitude=math.hypot(float(ux), float(uy)),
            )
        )

    return rows


def build_element_result_rows(
    solution: WorkbenchSolveResult,
) -> list[ElementResultRow]:
    result_by_element_id = {
        result.element_id: result for result in solution.solver_result.element_results
    }
    rows: list[ElementResultRow] = []

    for element in solution.mesh.elements:
        result = result_by_element_id.get(element.id)
        if result is None:
            raise ValueError(f"Missing element result for element_id {element.id!r}")

        strain = result.strain
        stress = result.stress
        strain_x = float(strain[0])
        strain_y = float(strain[1])
        strain_xy = float(strain[2])
        stress_x = float(stress[0])
        stress_y = float(stress[1])
        stress_xy = float(stress[2])

        rows.append(
            ElementResultRow(
                element_id=element.id,
                node_ids=list(element.node_ids),
                source_face_id=element.source_face_id,
                strain_x=strain_x,
                strain_y=strain_y,
                strain_xy=strain_xy,
                stress_x=stress_x,
                stress_y=stress_y,
                stress_xy=stress_xy,
                von_mises=_plane_stress_von_mises(stress_x, stress_y, stress_xy),
            )
        )

    return rows


def build_result_summary(solution: WorkbenchSolveResult) -> ResultSummary:
    node_rows = build_node_displacement_rows(solution)
    element_rows = build_element_result_rows(solution)

    max_displacement_row = max(node_rows, key=lambda row: row.u_magnitude, default=None)
    max_von_mises_row = max(element_rows, key=lambda row: row.von_mises, default=None)

    return ResultSummary(
        node_count=len(node_rows),
        element_count=len(element_rows),
        max_displacement=(
            max_displacement_row.u_magnitude if max_displacement_row is not None else 0.0
        ),
        max_displacement_node_id=(
            max_displacement_row.node_id if max_displacement_row is not None else None
        ),
        max_von_mises=max_von_mises_row.von_mises if max_von_mises_row is not None else 0.0,
        max_von_mises_element_id=(
            max_von_mises_row.element_id if max_von_mises_row is not None else None
        ),
        warning_count=len(solution.warnings),
    )


def _plane_stress_von_mises(stress_x: float, stress_y: float, stress_xy: float) -> float:
    value = stress_x**2 - stress_x * stress_y + stress_y**2 + 3.0 * stress_xy**2
    return math.sqrt(max(value, 0.0))


def build_deformation_plot_data(solution: WorkbenchSolveResult) -> dict[str, Any]:
    node_rows = build_node_displacement_rows(solution)
    max_displacement = max((row.u_magnitude for row in node_rows), default=0.0)
    return {
        "plot_type": "deformation_preview",
        "title": "变形示意图",
        "scalar_label": "|u|",
        "nodes": [row.to_dict() for row in node_rows],
        "elements": [
            {
                "element_id": element.id,
                "node_ids": list(element.node_ids),
                "source_face_id": element.source_face_id,
            }
            for element in solution.mesh.elements
        ],
        "summary": {
            "max_displacement": max_displacement,
            "default_scale_factor": _estimate_deformation_scale(solution, node_rows, max_displacement),
        },
    }


def build_displacement_contour_data(solution: WorkbenchSolveResult) -> dict[str, Any]:
    node_rows = build_node_displacement_rows(solution)
    displacement_values = [row.u_magnitude for row in node_rows]
    return {
        "plot_type": "displacement_contour",
        "title": "位移云图",
        "scalar_label": "位移幅值 |u|",
        "unit_label": "",
        "nodes": [
            {
                "id": row.node_id,
                "x": row.x,
                "y": row.y,
                "ux": row.ux,
                "uy": row.uy,
                "u": row.u_magnitude,
            }
            for row in node_rows
        ],
        "elements": [
            {
                "id": element.id,
                "node_ids": list(element.node_ids),
                "source_face_id": element.source_face_id,
            }
            for element in solution.mesh.elements
        ],
        "min_displacement": min(displacement_values) if displacement_values else 0.0,
        "max_displacement": max(displacement_values) if displacement_values else 0.0,
        "default_scale_factor": _estimate_deformation_scale(
            solution,
            node_rows,
            max(displacement_values) if displacement_values else 0.0,
        ),
    }


def build_stress_contour_data(solution: WorkbenchSolveResult) -> dict[str, Any]:
    element_rows = build_element_result_rows(solution)
    nodal_smoothed = _build_smoothed_nodal_von_mises(element_rows)
    element_von_mises_values = [row.von_mises for row in element_rows]
    smoothed_values = [nodal_smoothed.get(node.id, 0.0) for node in solution.mesh.nodes]
    return {
        "plot_type": "stress_contour",
        "title": "Von Mises 应力云图",
        "scalar_label": "Von Mises",
        "unit_label": "Pa",
        "nodes": [
            {
                "id": node.id,
                "x": node.x,
                "y": node.y,
                "smoothed_von_mises": nodal_smoothed.get(node.id, 0.0),
            }
            for node in solution.mesh.nodes
        ],
        "elements": [
            {
                "id": row.element_id,
                "node_ids": list(row.node_ids),
                "source_face_id": row.source_face_id,
                "von_mises": row.von_mises,
                "element_von_mises": row.von_mises,
                "nodal_smoothed_von_mises": [
                    nodal_smoothed.get(node_id, row.von_mises)
                    for node_id in row.node_ids
                ],
            }
            for row in element_rows
        ],
        "min_von_mises": min(element_von_mises_values) if element_von_mises_values else 0.0,
        "max_von_mises": max(element_von_mises_values) if element_von_mises_values else 0.0,
        "min_smoothed_von_mises": min(smoothed_values) if smoothed_values else 0.0,
        "max_smoothed_von_mises": max(smoothed_values) if smoothed_values else 0.0,
    }


def _build_smoothed_nodal_von_mises(
    element_rows: list[ElementResultRow],
) -> dict[int, float]:
    node_id_to_values: dict[int, list[float]] = {}
    for row in element_rows:
        for node_id in row.node_ids:
            node_id_to_values.setdefault(node_id, []).append(row.von_mises)
    return {
        node_id: (sum(values) / len(values) if values else 0.0)
        for node_id, values in node_id_to_values.items()
    }


def _estimate_deformation_scale(
    solution: WorkbenchSolveResult,
    node_rows: list[NodeDisplacementRow],
    max_displacement: float,
) -> float:
    if max_displacement <= 1.0e-16 or not solution.mesh.nodes:
        return 1.0
    xs = [node.x for node in solution.mesh.nodes]
    ys = [node.y for node in solution.mesh.nodes]
    span = max(max(xs) - min(xs), max(ys) - min(ys), 1.0)
    return max(1.0, 0.15 * span / max_displacement)
