from __future__ import annotations

from agent.geometry_agent import GeometryAgent
from agent.llm_client import StructuredOutputError
from agent.material_agent import MATERIAL_ACTION_SCHEMA, MaterialAgent
import pytest


def test_material_agent_create_and_delete(empty_project, fake_llm) -> None:
    agent = MaterialAgent(fake_llm)

    material_id = agent.create_material("aluminum", 70e9, 0.33, empty_project)
    material = empty_project.get_material_by_id(material_id)
    assert material is not None
    assert material.young_modulus == 70e9
    assert material.poisson_ratio == 0.33

    assert agent.delete_material(material_id, empty_project)
    assert empty_project.get_material_by_id(material_id) is None


def test_material_agent_assigns_one_material_to_all_model_faces(
    empty_project,
    valid_plan,
    fake_llm,
) -> None:
    GeometryAgent(fake_llm).create(valid_plan, empty_project)
    agent = MaterialAgent(fake_llm)
    material_id = agent.create_material("custom", 1234.0, 0.2, empty_project)

    assert agent.assign_material(material_id, empty_project, thickness=0.25, plane_mode="strain")

    for part in empty_project.parts:
        section = empty_project.get_section_by_id(part.section_id or "")
        assert section is not None
        assert section.material_id == material_id
        assert section.thickness == 0.25
        assert section.plane_mode == "strain"
        assert all(face.section_id == section.id for face in part.geometry.faces)


def test_material_agent_apply_uses_structured_llm_actions(
    empty_project,
    valid_plan,
    fake_llm,
) -> None:
    GeometryAgent(fake_llm).create(valid_plan, empty_project)
    agent = MaterialAgent(fake_llm)

    assert agent.apply(valid_plan, empty_project)

    assert fake_llm.requests[-1][2] == MATERIAL_ACTION_SCHEMA
    assigned = empty_project.get_section_by_id(empty_project.parts[0].section_id or "")
    assert assigned is not None
    assert empty_project.get_material_by_id(assigned.material_id).name == "Steel"


def test_material_agent_rejects_internal_id_from_llm(empty_project, valid_plan) -> None:
    from conftest import FakeLLMClient

    llm = FakeLLMClient(
        {
            "actions": [
                {
                    "action": "assign_material",
                    "name": "Steel",
                    "material_id": "mat_fake",
                    "thickness": 0.01,
                    "plane_mode": "stress",
                }
            ]
        }
    )

    with pytest.raises(StructuredOutputError, match="internal IDs|Invalid fields"):
        MaterialAgent(llm).apply(valid_plan, empty_project)


def test_material_agent_rejects_assign_only_when_same_name_has_different_properties(
    empty_project,
    valid_plan,
) -> None:
    from conftest import FakeLLMClient

    GeometryAgent(FakeLLMClient({})).create_rectangle(100.0, 50.0, empty_project)
    part = empty_project.parts[0]
    original_section_id = part.section_id
    llm = FakeLLMClient(
        {
            "actions": [
                {
                    "action": "assign_material",
                    "name": "Steel",
                    "thickness": 0.01,
                    "plane_mode": "stress",
                }
            ]
        }
    )

    with pytest.raises(StructuredOutputError, match="create_material is required"):
        MaterialAgent(llm).apply(valid_plan, empty_project)

    assert part.section_id == original_section_id
    assigned_section = empty_project.get_section_by_id(part.section_id or "")
    assigned_material = empty_project.get_material_by_id(assigned_section.material_id)
    assert assigned_material.young_modulus == 210e9
    assert assigned_material.young_modulus != valid_plan.material["E"]


def test_material_agent_create_then_assign_uses_exact_planned_properties(
    empty_project,
    valid_plan,
) -> None:
    from conftest import FakeLLMClient

    GeometryAgent(FakeLLMClient({})).create_rectangle(100.0, 50.0, empty_project)
    llm = FakeLLMClient(
        {
            "actions": [
                {
                    "action": "create_material",
                    "name": "Steel",
                    "E": valid_plan.material["E"],
                    "nu": valid_plan.material["nu"],
                },
                {
                    "action": "assign_material",
                    "name": "Steel",
                    "thickness": valid_plan.material["thickness"],
                    "plane_mode": valid_plan.material["plane_mode"],
                },
            ]
        }
    )

    assert MaterialAgent(llm).apply(valid_plan, empty_project)

    section = empty_project.get_section_by_id(empty_project.parts[0].section_id or "")
    material = empty_project.get_material_by_id(section.material_id)
    assert material.name == valid_plan.material["name"]
    assert material.young_modulus == valid_plan.material["E"]
    assert material.poisson_ratio == valid_plan.material["nu"]


def test_material_agent_rejects_assign_before_create_when_exact_material_is_missing(
    empty_project,
    valid_plan,
) -> None:
    from conftest import FakeLLMClient

    GeometryAgent(FakeLLMClient({})).create_rectangle(100.0, 50.0, empty_project)
    material_count = len(empty_project.materials)
    original_section_id = empty_project.parts[0].section_id
    llm = FakeLLMClient(
        {
            "actions": [
                {
                    "action": "assign_material",
                    "name": "Steel",
                    "thickness": valid_plan.material["thickness"],
                    "plane_mode": valid_plan.material["plane_mode"],
                },
                {
                    "action": "create_material",
                    "name": "Steel",
                    "E": valid_plan.material["E"],
                    "nu": valid_plan.material["nu"],
                },
            ]
        }
    )

    with pytest.raises(StructuredOutputError, match="must precede"):
        MaterialAgent(llm).apply(valid_plan, empty_project)

    assert len(empty_project.materials) == material_count
    assert empty_project.parts[0].section_id == original_section_id


def test_material_agent_allows_assign_only_when_exact_material_exists(
    empty_project,
    valid_plan,
) -> None:
    from conftest import FakeLLMClient

    GeometryAgent(FakeLLMClient({})).create_rectangle(100.0, 50.0, empty_project)
    agent = MaterialAgent(FakeLLMClient({}))
    material_id = agent.create_material(
        valid_plan.material["name"],
        valid_plan.material["E"],
        valid_plan.material["nu"],
        empty_project,
    )
    llm = FakeLLMClient(
        {
            "actions": [
                {
                    "action": "assign_material",
                    "name": "Steel",
                    "thickness": valid_plan.material["thickness"],
                    "plane_mode": valid_plan.material["plane_mode"],
                }
            ]
        }
    )

    assert MaterialAgent(llm).apply(valid_plan, empty_project)

    section = empty_project.get_section_by_id(empty_project.parts[0].section_id or "")
    assert section is not None
    assert section.material_id == material_id
