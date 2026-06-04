from __future__ import annotations

from core.engineering.engineering_project import EngineeringProject
from core.engineering.geometry import GeometryModel
from core.engineering.material_definition import MaterialDefinition
from core.engineering.part import Part
from core.engineering.section import SectionDefinition
from services.face_material_service import (
    assign_material_to_face,
    assign_material_to_part,
    get_face_material_info,
    get_part_face_material_rows,
)


def _project_with_two_faces() -> EngineeringProject:
    project = EngineeringProject(name="face_materials")
    project.add_material(MaterialDefinition("mat_a", "A", 100.0, 0.25, "#AA0000"))
    project.add_material(MaterialDefinition("mat_b", "B", 200.0, 0.30, "#00AA00"))
    project.add_section(SectionDefinition("sec_default", "default", "mat_a", 0.01))
    geometry = GeometryModel.create_rectangle(1.0, 1.0)
    geometry.faces[0].id = "f1"
    geometry.faces.append(type(geometry.faces[0])(id="f2", edge_ids=list(geometry.faces[0].edge_ids)))
    project.add_part(Part("part", "part", geometry, section_id="sec_default"))
    return project


def test_assign_material_to_individual_faces_and_query():
    project = _project_with_two_faces()

    assign_material_to_face(project, "part", "f1", "mat_a", 0.01)
    assign_material_to_face(project, "part", "f2", "mat_b", 0.02)

    f1 = get_face_material_info(project, "part", "f1")
    f2 = get_face_material_info(project, "part", "f2")
    assert f1["material_id"] == "mat_a"
    assert f2["material_id"] == "mat_b"
    assert f2["thickness"] == 0.02
    assert len(get_part_face_material_rows(project, "part")) == 2


def test_assign_material_to_part_updates_default_and_faces():
    project = _project_with_two_faces()

    assign_material_to_part(project, "part", "mat_b", 0.03)

    part = project.get_part_by_id("part")
    assert part is not None
    assert part.section_id
    assert all(face.section_id == part.section_id for face in part.geometry.faces)
    assert all(row["material_id"] == "mat_b" for row in get_part_face_material_rows(project, "part"))


def test_face_material_mapping_round_trips_through_project_dict():
    project = _project_with_two_faces()
    assign_material_to_face(project, "part", "f2", "mat_b", 0.02)

    restored = EngineeringProject.from_dict(project.to_dict())

    assert get_face_material_info(restored, "part", "f2")["material_id"] == "mat_b"
