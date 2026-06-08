from __future__ import annotations

import pytest

from core.compiler.gravity_load_mapper import map_gravity_load_to_nodal_loads
from core.compiler.project_to_fem import compile_project_to_fem
from core.engineering.analysis_step import AnalysisStep
from core.engineering.engineering_project import EngineeringProject
from core.engineering.geometry import GeometryEdge, GeometryFace, GeometryModel, GeometryPoint
from core.engineering.load_definition import LoadDefinition
from core.engineering.material_definition import MaterialDefinition
from core.engineering.mesh_model import MeshElement, MeshModel, MeshNode
from core.engineering.part import Part
from core.engineering.section import SectionDefinition


def test_stage18_gravity_load_mapper_single_triangle_expected_resultant() -> None:
    mesh = MeshModel(
        nodes=[
            MeshNode(id=1, x=0.0, y=0.0),
            MeshNode(id=2, x=2.0, y=0.0),
            MeshNode(id=3, x=0.0, y=1.0),
        ],
        elements=[MeshElement(id=1, node_ids=[1, 2, 3], source_face_id="f1")],
    )

    loads, _, stats = map_gravity_load_to_nodal_loads(
        mesh=mesh,
        mesh_node_to_fem_node_id={1: 1, 2: 2, 3: 3},
        element_unit_weights={1: 1000.0},
        element_thicknesses={1: 0.1},
        start_load_id=1,
    )

    assert stats["total_fx"] == pytest.approx(0.0)
    assert stats["total_fy"] == pytest.approx(-100.0)
    assert len(loads) == 3
    assert sum(load.fy for load in loads) == pytest.approx(-100.0)
    for load in loads:
        assert load.fy == pytest.approx(-100.0 / 3.0)


def test_stage18_gravity_load_mapper_zero_unit_weight_produces_no_load() -> None:
    mesh = MeshModel(
        nodes=[
            MeshNode(id=1, x=0.0, y=0.0),
            MeshNode(id=2, x=2.0, y=0.0),
            MeshNode(id=3, x=0.0, y=1.0),
        ],
        elements=[MeshElement(id=1, node_ids=[1, 2, 3], source_face_id="f1")],
    )

    loads, _, stats = map_gravity_load_to_nodal_loads(
        mesh=mesh,
        mesh_node_to_fem_node_id={1: 1, 2: 2, 3: 3},
        element_unit_weights={1: 0.0},
        element_thicknesses={1: 0.1},
        start_load_id=1,
    )

    assert loads == []
    assert stats["active_element_count"] == 0.0


def test_stage18_gravity_load_mapper_gravity_disabled_in_compile_produces_no_load() -> None:
    project, mesh = _single_face_project_and_mesh(unit_weight=1000.0, gravity_enabled=False)

    compiled = compile_project_to_fem(project, mesh, "step_static")

    assert compiled.fem_model.loads == []


def test_stage18_gravity_load_mapper_two_faces_use_different_material_unit_weights() -> None:
    project, mesh = _two_face_project_and_mesh(gravity_enabled=True)

    compiled = compile_project_to_fem(project, mesh, "step_static")

    total_fy = sum(load.fy for load in compiled.fem_model.loads)
    assert total_fy == pytest.approx(-(1000.0 * 1.0 * 0.1 + 2000.0 * 1.0 * 0.1))


def test_stage18_gravity_load_mapper_adds_to_manual_loads() -> None:
    project, mesh = _single_face_project_and_mesh(unit_weight=1000.0, gravity_enabled=True)
    project.loads.append(
        LoadDefinition(
            id="load1",
            name="point_load",
            step_id="step_static",
            target_type="geometry_point",
            target_id="p1",
            load_type="nodal_concentrated",
            qx=0.0,
            qy=-50.0,
        )
    )

    compiled = compile_project_to_fem(project, mesh, "step_static")

    assert sum(load.fy for load in compiled.fem_model.loads) == pytest.approx(-150.0)


def _single_face_project_and_mesh(
    unit_weight: float,
    gravity_enabled: bool,
) -> tuple[EngineeringProject, MeshModel]:
    geometry = GeometryModel(
        points=[
            GeometryPoint(id="p1", x=0.0, y=0.0),
            GeometryPoint(id="p2", x=2.0, y=0.0),
            GeometryPoint(id="p3", x=0.0, y=1.0),
        ],
        edges=[
            GeometryEdge(id="e1", start_point_id="p1", end_point_id="p2"),
            GeometryEdge(id="e2", start_point_id="p2", end_point_id="p3"),
            GeometryEdge(id="e3", start_point_id="p3", end_point_id="p1"),
        ],
        faces=[GeometryFace(id="f1", edge_ids=["e1", "e2", "e3"], point_ids=["p1", "p2", "p3"], section_id="sec1")],
    )
    project = EngineeringProject(
        name="gravity_project",
        materials=[
            MaterialDefinition(
                id="mat1",
                name="mat1",
                young_modulus=1.0,
                poisson_ratio=0.25,
                unit_weight=unit_weight,
            )
        ],
        sections=[SectionDefinition(id="sec1", name="sec1", material_id="mat1", thickness=0.1)],
        parts=[Part(id="part1", name="part1", geometry=geometry)],
        analysis_steps=[AnalysisStep(id="step_static", name="static")],
        metadata={
            "gravity_enabled": gravity_enabled,
            "gravity_direction_x": 0.0,
            "gravity_direction_y": -1.0,
        },
    )
    mesh = MeshModel(
        nodes=[
            MeshNode(id=1, x=0.0, y=0.0),
            MeshNode(id=2, x=2.0, y=0.0),
            MeshNode(id=3, x=0.0, y=1.0),
        ],
        elements=[MeshElement(id=1, node_ids=[1, 2, 3], source_face_id="f1")],
        geometry_point_to_mesh_node_ids={"p1": [1], "p2": [2], "p3": [3]},
    )
    return project, mesh


def _two_face_project_and_mesh(
    gravity_enabled: bool,
) -> tuple[EngineeringProject, MeshModel]:
    geometry = GeometryModel(
        points=[
            GeometryPoint(id="p1", x=0.0, y=0.0),
            GeometryPoint(id="p2", x=2.0, y=0.0),
            GeometryPoint(id="p3", x=0.0, y=1.0),
            GeometryPoint(id="p4", x=3.0, y=0.0),
            GeometryPoint(id="p5", x=5.0, y=0.0),
            GeometryPoint(id="p6", x=3.0, y=1.0),
        ],
        edges=[
            GeometryEdge(id="e1", start_point_id="p1", end_point_id="p2"),
            GeometryEdge(id="e2", start_point_id="p2", end_point_id="p3"),
            GeometryEdge(id="e3", start_point_id="p3", end_point_id="p1"),
            GeometryEdge(id="e4", start_point_id="p4", end_point_id="p5"),
            GeometryEdge(id="e5", start_point_id="p5", end_point_id="p6"),
            GeometryEdge(id="e6", start_point_id="p6", end_point_id="p4"),
        ],
        faces=[
            GeometryFace(id="f1", edge_ids=["e1", "e2", "e3"], point_ids=["p1", "p2", "p3"], section_id="sec1"),
            GeometryFace(id="f2", edge_ids=["e4", "e5", "e6"], point_ids=["p4", "p5", "p6"], section_id="sec2"),
        ],
    )
    project = EngineeringProject(
        name="gravity_project",
        materials=[
            MaterialDefinition(id="mat1", name="mat1", young_modulus=1.0, poisson_ratio=0.25, unit_weight=1000.0),
            MaterialDefinition(id="mat2", name="mat2", young_modulus=1.0, poisson_ratio=0.25, unit_weight=2000.0),
        ],
        sections=[
            SectionDefinition(id="sec1", name="sec1", material_id="mat1", thickness=0.1),
            SectionDefinition(id="sec2", name="sec2", material_id="mat2", thickness=0.1),
        ],
        parts=[Part(id="part1", name="part1", geometry=geometry)],
        analysis_steps=[AnalysisStep(id="step_static", name="static")],
        metadata={
            "gravity_enabled": gravity_enabled,
            "gravity_direction_x": 0.0,
            "gravity_direction_y": -1.0,
        },
    )
    mesh = MeshModel(
        nodes=[
            MeshNode(id=1, x=0.0, y=0.0),
            MeshNode(id=2, x=2.0, y=0.0),
            MeshNode(id=3, x=0.0, y=1.0),
            MeshNode(id=4, x=3.0, y=0.0),
            MeshNode(id=5, x=5.0, y=0.0),
            MeshNode(id=6, x=3.0, y=1.0),
        ],
        elements=[
            MeshElement(id=1, node_ids=[1, 2, 3], source_face_id="f1"),
            MeshElement(id=2, node_ids=[4, 5, 6], source_face_id="f2"),
        ],
    )
    return project, mesh
