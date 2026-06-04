from __future__ import annotations

import math
from dataclasses import dataclass

from core.engineering.mesh_model import MeshElement, MeshModel, MeshNode
from services.result_service import ElementResultRow, NodeDisplacementRow


@dataclass(slots=True)
class ResultQuerySummary:
    query_x: float
    query_y: float
    nearest_node_id: int
    nearest_node_distance: float
    containing_element_id: int | None
    inside_element: bool
    ux: float
    uy: float
    displacement_magnitude: float
    stress_x: float | None
    stress_y: float | None
    stress_xy: float | None
    von_mises: float | None


def query_result_at_point(
    mesh: MeshModel,
    node_rows: list[NodeDisplacementRow],
    element_rows: list[ElementResultRow],
    x: float,
    y: float,
) -> ResultQuerySummary:
    if not mesh.nodes:
        raise ValueError("结果查询失败: 当前网格为空")
    if not node_rows:
        raise ValueError("结果查询失败: 当前没有节点结果")

    node_row_by_id = {row.node_id: row for row in node_rows}
    element_row_by_id = {row.element_id: row for row in element_rows}
    node_by_id = {node.id: node for node in mesh.nodes}

    nearest_node = min(mesh.nodes, key=lambda node: (node.x - x) ** 2 + (node.y - y) ** 2)
    nearest_row = node_row_by_id.get(nearest_node.id)
    if nearest_row is None:
        raise ValueError(f"结果查询失败: 缺少节点 {nearest_node.id} 的结果")

    containing_element = _find_containing_element(mesh, node_by_id, x, y)
    element_row = (
        element_row_by_id.get(containing_element.id) if containing_element is not None else None
    )

    return ResultQuerySummary(
        query_x=float(x),
        query_y=float(y),
        nearest_node_id=nearest_node.id,
        nearest_node_distance=math.hypot(nearest_node.x - x, nearest_node.y - y),
        containing_element_id=containing_element.id if containing_element is not None else None,
        inside_element=containing_element is not None,
        ux=nearest_row.ux,
        uy=nearest_row.uy,
        displacement_magnitude=nearest_row.u_magnitude,
        stress_x=element_row.stress_x if element_row is not None else None,
        stress_y=element_row.stress_y if element_row is not None else None,
        stress_xy=element_row.stress_xy if element_row is not None else None,
        von_mises=element_row.von_mises if element_row is not None else None,
    )


def format_result_query_text(summary: ResultQuerySummary) -> str:
    lines = [
        f"查询点: ({summary.query_x:.6g}, {summary.query_y:.6g})",
        (
            f"最近节点: {summary.nearest_node_id} "
            f"(距离 {summary.nearest_node_distance:.6g})"
        ),
        (
            f"节点位移: ux={summary.ux:.6e}, "
            f"uy={summary.uy:.6e}, |u|={summary.displacement_magnitude:.6e}"
        ),
    ]
    if summary.inside_element and summary.containing_element_id is not None:
        lines.extend(
            [
                f"所在单元: {summary.containing_element_id}",
                f"单元应力: sx={summary.stress_x:.6e}, sy={summary.stress_y:.6e}, txy={summary.stress_xy:.6e}",
                f"Von Mises: {summary.von_mises:.6e}",
            ]
        )
    else:
        lines.append("所在单元: 未命中三角形，已返回最近节点结果")
    return "\n".join(lines)


def _find_containing_element(
    mesh: MeshModel,
    node_by_id: dict[int, MeshNode],
    x: float,
    y: float,
) -> MeshElement | None:
    for element in mesh.elements:
        a = node_by_id.get(element.node_ids[0])
        b = node_by_id.get(element.node_ids[1])
        c = node_by_id.get(element.node_ids[2])
        if a is None or b is None or c is None:
            continue
        if _point_in_triangle(x, y, a.x, a.y, b.x, b.y, c.x, c.y):
            return element
    return None


def _point_in_triangle(
    px: float,
    py: float,
    ax: float,
    ay: float,
    bx: float,
    by: float,
    cx: float,
    cy: float,
) -> bool:
    denominator = (by - cy) * (ax - cx) + (cx - bx) * (ay - cy)
    if abs(denominator) <= 1e-12:
        return False

    w1 = ((by - cy) * (px - cx) + (cx - bx) * (py - cy)) / denominator
    w2 = ((cy - ay) * (px - cx) + (ax - cx) * (py - cy)) / denominator
    w3 = 1.0 - w1 - w2
    tolerance = -1e-9
    return w1 >= tolerance and w2 >= tolerance and w3 >= tolerance
