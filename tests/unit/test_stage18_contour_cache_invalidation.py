from __future__ import annotations

from pathlib import Path

from ui.backend.workbench_bridge import WorkbenchBridge


def _first_material_id(bridge: WorkbenchBridge) -> str:
    option = bridge.materialOptions[0]
    return option.split("|", 1)[0].strip()


def _solve_default_project(bridge: WorkbenchBridge) -> None:
    assert bridge.createDefaultProject(2.0, 1.0, 210e9, 0.3, 0.01, -1000.0), bridge.statusText
    assert bridge.solveCurrentProject(4, 2), bridge.statusText
    assert bridge.contourCacheValid
    assert bridge.contourImageCacheValid


def test_stage18_contour_cache_invalidation_for_geometry_material_load_mesh_and_new_project() -> None:
    bridge = WorkbenchBridge()

    _solve_default_project(bridge)
    image_dir = bridge.contourImageCacheDir
    assert bridge.addModelPoint(2.5, 0.5), bridge.statusText
    assert not bridge.contourCacheValid
    assert not bridge.contourImageCacheValid
    assert not Path(image_dir).exists()

    _solve_default_project(bridge)
    material_id = _first_material_id(bridge)
    assert bridge.updateMaterial(material_id, "steel", 211e9, 0.3, "#8FB7D8", 0.0), bridge.statusText
    assert not bridge.contourCacheValid
    assert not bridge.contourImageCacheValid

    _solve_default_project(bridge)
    assert bridge.selectGeometryEdge("right"), bridge.statusText
    assert bridge.addLoadToSelectedTarget("edge_uniform", 0.0, -900.0), bridge.statusText
    assert not bridge.contourCacheValid
    assert not bridge.contourImageCacheValid

    _solve_default_project(bridge)
    assert bridge.clearMesh(), bridge.statusText
    assert not bridge.contourCacheValid
    assert not bridge.contourImageCacheValid

    _solve_default_project(bridge)
    assert bridge.newProject(), bridge.statusText
    assert not bridge.contourCacheValid
    assert not bridge.contourImageCacheValid
    assert bridge.deformationPreviewJson == "{}"
