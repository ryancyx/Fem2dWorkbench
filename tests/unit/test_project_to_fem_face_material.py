from __future__ import annotations

import pytest

from core.compiler.project_to_fem import compile_project_to_fem
from core.engineering.analysis_step import AnalysisStep
from core.engineering.engineering_project import EngineeringProject
from core.engineering.geometry import GeometryModel
from core.engineering.material_definition import MaterialDefinition
from core.engineering.mesh_model import MeshElement, MeshModel, MeshNode
from core.engineering.part import Part
from core.engineering.section import SectionDefinition


def _base_project(part_section_id: str | None = "sec_a") -> EngineeringProject:
    project = EngineeringProject(name="compile_faces")
    project.add_material(MaterialDefinition("mat_a", "A", 100.0, 0.25, "#AA0000"))
    project.add_material(MaterialDefinition("mat_b", "B", 200.0, 0.30, "#00AA00"))
    project.add_section(SectionDefinition("sec_a", "A section", "mat_a", 0.01))
    project.add_section(SectionDefinition("sec_b", "B section", "mat_b", 0.02))
    geometry = GeometryModel.create_rectangle(1.0, 1.0)
    geometry.faces[0].id = "f1"
    geometry.faces.append(type(geometry.faces[0])(id="f2", edge_ids=list(geometry.faces[0].edge_ids)))
    project.add_part(Part("part", "part", geometry, section_id=part_section_id))
    project.add_analysis_step(AnalysisStep("step", "step", "static_linear"))
    return project


def _two_face_mesh() -> MeshModel:
    return MeshModel(
        nodes=[
            MeshNode(1, 0.0, 0.0),
            MeshNode(2, 1.0, 0.0),
            MeshNode(3, 1.0, 1.0),
            MeshNode(4, 0.0, 1.0),
        ],
        elements=[
            MeshElement(1, [1, 2, 3], source_face_id="f1"),
            MeshElement(2, [1, 3, 4], source_face_id="f2"),
        ],
    )


def test_compiler_uses_face_material_overrides():
    project = _base_project()
    part = project.parts[0]
    part.geometry.faces[0].section_id = "sec_a"
    part.geometry.faces[1].section_id = "sec_b"

    bundle = compile_project_to_fem(project, _two_face_mesh(), "step")

    element_materials = {element.id: element.material_id for element in bundle.fem_model.elements}
    assert element_materials[1] != element_materials[2]
    assert len(bundle.fem_model.materials) == 2


def test_compiler_falls_back_to_part_section():
    project = _base_project(part_section_id="sec_a")

    bundle = compile_project_to_fem(project, _two_face_mesh(), "step")

    assert len(bundle.fem_model.materials) == 1
    assert {element.material_id for element in bundle.fem_model.elements} == {1}


def test_compiler_fails_when_face_and_part_have_no_material():
    project = _base_project(part_section_id=None)

    with pytest.raises(ValueError, match="未分配材料"):
        compile_project_to_fem(project, _two_face_mesh(), "step")
