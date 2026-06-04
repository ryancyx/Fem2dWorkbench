from __future__ import annotations

import json

from ui.backend.workbench_bridge import WorkbenchBridge


def _build_triangle_sketch(bridge: WorkbenchBridge) -> None:
    assert bridge.createEmptySketchForActivePart()
    assert bridge.addSketchPoint(0.0, 0.0)
    assert bridge.addSketchPoint(2.0, 0.0)
    assert bridge.addSketchPoint(1.0, 1.0)
    assert bridge.addSketchEdge("p1", "p2")
    assert bridge.addSketchEdge("p2", "p3")
    assert bridge.addSketchEdge("p3", "p1")
    assert bridge.buildSketchFace()


def _build_quad_sketch(bridge: WorkbenchBridge) -> None:
    assert bridge.createEmptySketchForActivePart()
    assert bridge.addSketchPoint(0.0, 0.0)
    assert bridge.addSketchPoint(2.0, 0.0)
    assert bridge.addSketchPoint(2.0, 1.0)
    assert bridge.addSketchPoint(0.0, 1.0)
    assert bridge.addSketchEdge("p1", "p2")
    assert bridge.addSketchEdge("p2", "p3")
    assert bridge.addSketchEdge("p3", "p4")
    assert bridge.addSketchEdge("p4", "p1")
    assert bridge.buildSketchFace()


def _assert_gmsh_sketch_mesh(bridge: WorkbenchBridge, geometry_point_count: int) -> None:
    assert bridge.hasSketchMesh is True
    assert bridge.currentMeshType == "gmsh_cst"
    assert bridge.sketchMeshNodeCount > geometry_point_count
    assert bridge.sketchMeshElementCount > geometry_point_count - 2

    nodes = json.loads(bridge.sketchMeshNodesJson)
    elements = json.loads(bridge.sketchMeshElementsJson)

    assert len(nodes) == bridge.sketchMeshNodeCount
    assert len(elements) == bridge.sketchMeshElementCount
    assert all(len(element["node_ids"]) == 3 for element in elements)


def test_bridge_generate_triangle_sketch_mesh():
    bridge = WorkbenchBridge()

    assert bridge.newProject()
    _build_triangle_sketch(bridge)

    assert bridge.generateSketchMeshForActivePart()
    _assert_gmsh_sketch_mesh(bridge, geometry_point_count=3)


def test_bridge_generate_quad_sketch_mesh():
    bridge = WorkbenchBridge()

    assert bridge.newProject()
    _build_quad_sketch(bridge)

    assert bridge.generateSketchMeshForActivePart()
    _assert_gmsh_sketch_mesh(bridge, geometry_point_count=4)


def test_bridge_clear_sketch_mesh():
    bridge = WorkbenchBridge()

    assert bridge.newProject()
    _build_triangle_sketch(bridge)
    assert bridge.generateSketchMeshForActivePart()

    assert bridge.clearSketchMesh()

    assert bridge.hasSketchMesh is False
    assert bridge.sketchMeshNodeCount == 0
    assert bridge.sketchMeshElementCount == 0
    assert bridge.sketchMeshNodesJson == "[]"
    assert bridge.sketchMeshElementsJson == "[]"


def test_bridge_unclosed_sketch_mesh_generation_fails():
    bridge = WorkbenchBridge()

    assert bridge.newProject()
    assert bridge.createEmptySketchForActivePart()
    assert bridge.addSketchPoint(0.0, 0.0)
    assert bridge.addSketchPoint(1.0, 0.0)
    assert bridge.addSketchPoint(0.0, 1.0)
    assert bridge.addSketchEdge("p1", "p2")
    assert bridge.addSketchEdge("p2", "p3")

    assert bridge.generateSketchMeshForActivePart() is False

    assert bridge.hasSketchMesh is False
    assert bridge.sketchMeshNodeCount == 0
    assert bridge.sketchMeshElementCount == 0
    assert "失败" in bridge.statusText or "face" in bridge.statusText.lower()


def test_bridge_sketch_mesh_is_cleared_when_sketch_changes():
    bridge = WorkbenchBridge()

    assert bridge.newProject()
    _build_triangle_sketch(bridge)
    assert bridge.generateSketchMeshForActivePart()
    assert bridge.hasSketchMesh is True

    assert bridge.addSketchPoint(3.0, 3.0)

    assert bridge.hasSketchMesh is False
    assert bridge.sketchMeshNodeCount == 0
    assert bridge.sketchMeshElementCount == 0
