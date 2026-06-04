from core.meshing.sketch_polygon_mesher import generate_sketch_tri_mesh
from services.project_file_service import load_workbench_project
from ui.backend.workbench_bridge import WorkbenchBridge


def test_stage13b_bridge_sketch_save_load_then_generate_mesh(tmp_path):
    bridge = WorkbenchBridge()

    assert bridge.newProject()
    assert bridge.createEmptySketchForActivePart()

    assert bridge.addSketchPoint(0.0, 0.0)
    assert bridge.addSketchPoint(2.0, 0.0)
    assert bridge.addSketchPoint(2.0, 1.0)
    assert bridge.addSketchPoint(0.0, 1.0)

    assert bridge.addSketchEdge("p1", "p2")
    assert bridge.addSketchEdge("p2", "p3")
    assert bridge.addSketchEdge("p3", "p4")
    assert bridge.addSketchEdge("p4", "p1")

    assert bridge.sketchCanBuildFace is True
    assert bridge.buildSketchFace()
    assert bridge.sketchHasFace is True

    file_path = tmp_path / "stage13b_sketch_project.f2dw.json"

    assert bridge.saveCurrentProject(str(file_path))

    loaded_project = load_workbench_project(file_path)
    active_part = loaded_project.get_part_by_id(loaded_project.metadata["active_part_id"])

    assert active_part is not None

    mesh = generate_sketch_tri_mesh(active_part.geometry)

    assert len(mesh.nodes) == 4
    assert len(mesh.elements) == 2
    assert set(mesh.geometry_edge_to_mesh_node_ids) == {"e1", "e2", "e3", "e4"}
    assert set(mesh.geometry_edge_to_mesh_element_edges) == {"e1", "e2", "e3", "e4"}


def test_stage13b_triangle_sketch_generates_one_mesh_element_through_bridge():
    bridge = WorkbenchBridge()

    assert bridge.newProject()
    assert bridge.createEmptySketchForActivePart()

    assert bridge.addSketchPoint(0.0, 0.0)
    assert bridge.addSketchPoint(2.0, 0.0)
    assert bridge.addSketchPoint(1.0, 1.0)

    assert bridge.addSketchEdge("p1", "p2")
    assert bridge.addSketchEdge("p2", "p3")
    assert bridge.addSketchEdge("p3", "p1")

    assert bridge.buildSketchFace()

    active_part = bridge.current_project.get_part_by_id(bridge.activePartId)

    assert active_part is not None

    mesh = generate_sketch_tri_mesh(active_part.geometry)

    assert len(mesh.nodes) == 3
    assert len(mesh.elements) == 1


def test_stage13b_unclosed_bridge_sketch_cannot_generate_mesh():
    bridge = WorkbenchBridge()

    assert bridge.newProject()
    assert bridge.createEmptySketchForActivePart()

    assert bridge.addSketchPoint(0.0, 0.0)
    assert bridge.addSketchPoint(1.0, 0.0)
    assert bridge.addSketchPoint(0.0, 1.0)

    assert bridge.addSketchEdge("p1", "p2")
    assert bridge.addSketchEdge("p2", "p3")

    assert bridge.sketchCanBuildFace is False
    assert bridge.buildSketchFace() is False