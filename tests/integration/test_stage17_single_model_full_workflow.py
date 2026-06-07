from __future__ import annotations

import json
from pathlib import Path

import pytest

from ui.backend.workbench_bridge import WorkbenchBridge


def _json_list(text: str) -> list[dict]:
    data = json.loads(text)
    assert isinstance(data, list)
    return data


def _parse_option_id(option_text: str) -> str:
    return str(option_text).split("|", 1)[0].strip()


def _find_material_id_by_name(bridge: WorkbenchBridge, material_name: str) -> str:
    for option in bridge.materialOptions:
        if material_name in option:
            return _parse_option_id(option)
    raise AssertionError(f"material option for {material_name!r} not found: {bridge.materialOptions}")


def _find_edge_by_point_ids(
    bridge: WorkbenchBridge,
    start_point_id: str,
    end_point_id: str,
) -> str:
    edges = _json_list(bridge.modelEdgesJson)
    for edge in edges:
        if (
            edge["start_point_id"] == start_point_id
            and edge["end_point_id"] == end_point_id
        ):
            return edge["id"]
    raise AssertionError(
        f"edge {start_point_id}->{end_point_id} not found in {edges}"
    )


def _build_rectangle_model(bridge: WorkbenchBridge) -> None:
    """
    建立一个 2 x 1 的四边形闭合面：

        p4 -------- p3
        |           |
        |           |
        p1 -------- p2
    """
    assert bridge.addModelPoint(0.0, 0.0), bridge.statusText
    assert bridge.addModelPoint(2.0, 0.0), bridge.statusText
    assert bridge.addModelPoint(2.0, 1.0), bridge.statusText
    assert bridge.addModelPoint(0.0, 1.0), bridge.statusText

    points = _json_list(bridge.modelPointsJson)
    assert len(points) == 4

    point_ids = [point["id"] for point in points]
    p1, p2, p3, p4 = point_ids

    assert bridge.connectModelEdge(p1, p2), bridge.statusText
    assert bridge.connectModelEdge(p2, p3), bridge.statusText
    assert bridge.connectModelEdge(p3, p4), bridge.statusText
    assert bridge.connectModelEdge(p4, p1), bridge.statusText

    assert bridge.modelEdgeCount == 4
    assert bridge.buildModelFaces(), bridge.statusText
    assert bridge.modelFaceCount == 1

    faces = _json_list(bridge.modelFacesJson)
    assert len(faces) == 1
    assert faces[0]["id"] != ""


@pytest.mark.integration
def test_stage17_single_model_full_workflow_solve_query_export(tmp_path: Path) -> None:
    """
    阶段 17 单模型全流程集成测试：

    新建工程
    -> 建模点/边/闭合面
    -> 闭合面材料
    -> Gmsh 网格
    -> 几何边约束/载荷
    -> 求解
    -> 结果查询
    -> 导出
    """
    pytest.importorskip("gmsh", reason="full workflow requires gmsh backend")

    bridge = WorkbenchBridge()

    assert bridge.newProject(), bridge.statusText
    assert bridge.hasProject
    assert bridge.modelPointCount == 0
    assert bridge.modelEdgeCount == 0
    assert bridge.modelFaceCount == 0

    _build_rectangle_model(bridge)

    # 1. 新增材料并分配给闭合面
    assert bridge.addMaterial(
        "steel",
        210_000_000_000.0,
        0.3,
        "#8FB7D8",
    ), bridge.statusText

    material_id = _find_material_id_by_name(bridge, "steel")

    faces = _json_list(bridge.modelFacesJson)
    face_id = faces[0]["id"]

    assert bridge.selectGeometryFace(face_id), bridge.statusText
    assert bridge.selectedFaceId == face_id
    assert bridge.assignMaterialToSelectedFace(material_id, 0.01), bridge.statusText

    face_material_rows = _json_list(bridge.faceMaterialJson)
    assert any(row["face_id"] == face_id for row in face_material_rows), bridge.faceMaterialJson
    assert "steel" in bridge.faceMaterialRowsPreview

    # 2. 生成 Gmsh CST 网格
    assert bridge.generateMesh(0.25, 25.0), bridge.statusText
    assert bridge.hasMesh
    assert bridge.currentMeshType != "none"
    assert bridge.sketchMeshNodeCount > 4
    assert bridge.sketchMeshElementCount > 2

    mesh_nodes = _json_list(bridge.meshNodesJson)
    mesh_elements = _json_list(bridge.meshElementsJson)
    assert len(mesh_nodes) == bridge.sketchMeshNodeCount
    assert len(mesh_elements) == bridge.sketchMeshElementCount
    assert bridge.meshQualitySummaryText != ""

    # 3. 给左边固定约束，右边施加向下均布载荷
    points = _json_list(bridge.modelPointsJson)
    p1, p2, p3, p4 = [point["id"] for point in points]

    right_edge_id = _find_edge_by_point_ids(bridge, p2, p3)
    left_edge_id = _find_edge_by_point_ids(bridge, p4, p1)

    assert bridge.selectGeometryEdge(left_edge_id), bridge.statusText
    assert bridge.selectedTargetType == "edge"
    assert bridge.selectedTargetId == left_edge_id
    assert bridge.addConstraintToSelectedTarget(True, True), bridge.statusText
    assert bridge.boundaryConditionRowsPreview != ""

    assert bridge.selectGeometryEdge(right_edge_id), bridge.statusText
    assert bridge.selectedTargetType == "edge"
    assert bridge.selectedTargetId == right_edge_id
    assert bridge.addLoadToSelectedTarget("edge_uniform", 0.0, -1000.0), bridge.statusText
    assert bridge.loadRowsPreview != ""

    boundary_conditions = _json_list(bridge.boundaryConditionsJson)
    loads = _json_list(bridge.loadsJson)

    assert len(boundary_conditions) == 1
    assert boundary_conditions[0]["target_type"] == "geometry_edge"
    assert boundary_conditions[0]["target_id"] == left_edge_id

    assert len(loads) == 1
    assert loads[0]["load_type"] == "edge_uniform"
    assert loads[0]["target_type"] == "geometry_edge"
    assert loads[0]["target_id"] == right_edge_id
    assert loads[0]["qy"] == -1000.0

    # 4. 求解
    assert bridge.solveCurrentModel(), bridge.statusText
    assert bridge.hasSolution
    assert bridge.nodeCount > 0
    assert bridge.elementCount > 0
    assert bridge.maxDisplacement != ""
    assert bridge.maxVonMises != ""

    node_rows = _json_list(bridge.nodeRowsJson)
    element_rows = _json_list(bridge.elementRowsJson)

    assert len(node_rows) == bridge.nodeCount
    assert len(element_rows) == bridge.elementCount

    # 5. 查询模型内部一点的结果
    assert bridge.queryResultAtPoint(1.0, 0.5), bridge.statusText
    assert bridge.resultQueryText != ""
    assert "ux" in bridge.resultQueryText or "位移" in bridge.resultQueryText

    # 6. 导出结果
    export_dir = tmp_path / "stage17_full_workflow_export"
    assert bridge.exportResults(str(export_dir)), bridge.statusText

    assert (export_dir / "node_displacements.csv").exists()
    assert (export_dir / "element_results.csv").exists()
    assert (export_dir / "summary.txt").exists()


@pytest.mark.integration
def test_stage17_solve_fails_without_any_material_assignment() -> None:
    """
    当前后端允许闭合面没有单独材料时回退到 Part 默认材料。

    因此这个负向测试需要显式清除：
    1. part.section_id
    2. face.section_id

    然后再验证求解会在进入 solver 前失败。
    """
    pytest.importorskip("gmsh", reason="mesh generation requires gmsh backend")

    bridge = WorkbenchBridge()

    assert bridge.newProject(), bridge.statusText
    _build_rectangle_model(bridge)

    # 当前工程可能自带默认 part.section_id。
    # 为了真正测试“无任何材料/截面”，这里显式清空 Part 和 Face 的 section。
    part = bridge._require_active_part()
    part.section_id = None
    for face in part.geometry.faces:
        face.section_id = ""

    bridge.projectChanged.emit()

    assert bridge.generateMesh(0.25, 25.0), bridge.statusText

    points = _json_list(bridge.modelPointsJson)
    p1, p2, p3, p4 = [point["id"] for point in points]

    left_edge_id = _find_edge_by_point_ids(bridge, p4, p1)
    right_edge_id = _find_edge_by_point_ids(bridge, p2, p3)

    assert bridge.selectGeometryEdge(left_edge_id), bridge.statusText
    assert bridge.addConstraintToSelectedTarget(True, True), bridge.statusText

    assert bridge.selectGeometryEdge(right_edge_id), bridge.statusText
    assert bridge.addLoadToSelectedTarget("edge_uniform", 0.0, -1000.0), bridge.statusText

    assert not bridge.solveCurrentModel()
    assert "材料" in bridge.statusText or "未分配" in bridge.statusText


@pytest.mark.integration
def test_stage17_solve_fails_without_constraint_or_load() -> None:
    """
    有材料和网格，但缺少约束/载荷时，应给出明确错误。
    """
    pytest.importorskip("gmsh", reason="mesh generation requires gmsh backend")

    bridge = WorkbenchBridge()

    assert bridge.newProject(), bridge.statusText
    _build_rectangle_model(bridge)

    assert bridge.addMaterial(
        "steel",
        210_000_000_000.0,
        0.3,
        "#8FB7D8",
    ), bridge.statusText

    material_id = _find_material_id_by_name(bridge, "steel")
    face_id = _json_list(bridge.modelFacesJson)[0]["id"]

    assert bridge.selectGeometryFace(face_id), bridge.statusText
    assert bridge.assignMaterialToSelectedFace(material_id, 0.01), bridge.statusText

    assert bridge.generateMesh(0.25, 25.0), bridge.statusText

    # 没有约束，也没有载荷
    assert not bridge.solveCurrentModel()
    assert "约束" in bridge.statusText or "载荷" in bridge.statusText

    points = _json_list(bridge.modelPointsJson)
    p1, p2, p3, p4 = [point["id"] for point in points]
    left_edge_id = _find_edge_by_point_ids(bridge, p4, p1)

    assert bridge.selectGeometryEdge(left_edge_id), bridge.statusText
    assert bridge.addConstraintToSelectedTarget(True, True), bridge.statusText

    # 有约束，但没有载荷
    assert not bridge.solveCurrentModel()
    assert "载荷" in bridge.statusText
