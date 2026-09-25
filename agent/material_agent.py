from __future__ import annotations

import json
from typing import Any

from agent.llm_client import LLMClient, StructuredOutputError
from agent.simulation_plan import SimulationPlan
from core.engineering.engineering_project import EngineeringProject
from services.material_manager_service import (
    add_material,
    add_or_update_section,
    delete_material,
)


MATERIAL_SYSTEM_PROMPT = """You are the Material specialist for Fem2dWorkbench Agent 1.0.
Read only the structured material subplan and compact material/section context. Return a
schema-constrained sequence of create_material, assign_material, or delete_material
actions. Refer to materials by semantic name, never by an invented internal ID. Preserve
E, nu, thickness, and plane_mode from the validated subplan. Do not modify geometry,
boundary conditions, loads, mesh, or solver state. Use these exact per-action fields and
no others: create_material has action,name,E,nu and optionally color,unit_weight;
assign_material has action,name,thickness,plane_mode; delete_material has action,name.
Never emit null placeholder fields. When no exact name+E+nu material exists, return
create_material first and assign_material second."""


MATERIAL_ACTION_SCHEMA: dict[str, Any] = {
    "title": "MaterialActions",
    "type": "object",
    "additionalProperties": False,
    "required": ["actions"],
    "properties": {
        "actions": {
            "type": "array",
            "minItems": 1,
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["action", "name"],
                "properties": {
                    "action": {"enum": ["create_material", "assign_material", "delete_material"]},
                    "name": {"type": "string", "minLength": 1},
                    "E": {"type": "number", "exclusiveMinimum": 0},
                    "nu": {"type": "number", "exclusiveMinimum": -1, "exclusiveMaximum": 0.5},
                    "color": {"type": "string"},
                    "unit_weight": {"type": "number", "minimum": 0},
                    "thickness": {"type": "number", "exclusiveMinimum": 0},
                    "plane_mode": {"enum": ["stress", "strain"]},
                },
            },
        }
    },
}


class MaterialAgent:
    def __init__(self, llm: LLMClient) -> None:
        self.llm = llm

    def create_material(
        self,
        name: str,
        young_modulus: float,
        poisson_ratio: float,
        project: EngineeringProject,
        color: str = "#808080",
        unit_weight: float = 0.0,
    ) -> str:
        existing_ids = {material.id for material in project.materials}
        add_material(
            project=project,
            name=name,
            young_modulus=young_modulus,
            poisson_ratio=poisson_ratio,
            color=color,
            unit_weight=unit_weight,
        )
        created = [material.id for material in project.materials if material.id not in existing_ids]
        if len(created) != 1:
            raise RuntimeError("Material creation did not produce exactly one material")
        return created[0]

    def delete_material(self, material_id: str, project: EngineeringProject) -> bool:
        delete_material(project, material_id)
        return True

    def assign_material(
        self,
        material_id: str,
        project: EngineeringProject,
        thickness: float | None = None,
        plane_mode: str | None = None,
    ) -> bool:
        material = project.get_material_by_id(material_id)
        if material is None:
            raise ValueError(f"Unknown material id: {material_id}")
        if not project.parts:
            raise ValueError("Cannot assign material because the project has no parts")
        resolved_thickness, resolved_plane_mode = self._resolve_section_defaults(
            project, thickness, plane_mode
        )
        section_id = add_or_update_section(
            project=project,
            name=f"{material.name}_agent_section",
            material_id=material_id,
            thickness=resolved_thickness,
            plane_mode=resolved_plane_mode,
        )
        for part in project.parts:
            part.section_id = section_id
            for face in part.geometry.faces:
                face.section_id = section_id
        project.validate_references()
        return True

    def apply(self, plan: SimulationPlan, project: EngineeringProject) -> bool:
        material_subplan = plan.material
        actions = self._request_actions(material_subplan, project)
        for action in actions:
            name = action["name"]
            if action["action"] == "create_material":
                existing = self._find_matching_material(project, action)
                if existing is None:
                    self.create_material(
                        name=name,
                        young_modulus=action["E"],
                        poisson_ratio=action["nu"],
                        project=project,
                        color=action.get("color", "#808080"),
                        unit_weight=action.get("unit_weight", 0.0),
                    )
            elif action["action"] == "assign_material":
                material = self._find_matching_subplan_material(project, material_subplan)
                if material is None:
                    raise ValueError(
                        f"Cannot assign material {name!r}: no material matches the planned E and nu"
                    )
                self.assign_material(
                    material.id,
                    project,
                    thickness=action["thickness"],
                    plane_mode=action["plane_mode"],
                )
            elif action["action"] == "delete_material":
                material = self._find_material_by_name(project, name)
                if material is None:
                    raise ValueError(f"Cannot delete unknown material name: {name}")
                self.delete_material(material.id, project)
        return True

    def _request_actions(
        self,
        material_subplan: dict[str, Any],
        project: EngineeringProject,
    ) -> list[dict[str, Any]]:
        content = {
            "material": material_subplan,
            "projectContext": {
                "materials": [
                    {
                        "name": row.name,
                        "E": row.young_modulus,
                        "nu": row.poisson_ratio,
                    }
                    for row in project.materials
                ],
                "sections": [
                    {
                        "materialName": (
                            project.get_material_by_id(row.material_id).name
                            if project.get_material_by_id(row.material_id)
                            else ""
                        ),
                        "thickness": row.thickness,
                        "plane_mode": row.plane_mode,
                    }
                    for row in project.sections
                ],
            },
        }
        try:
            response = self.llm.request(
                MATERIAL_SYSTEM_PROMPT,
                json.dumps(content, ensure_ascii=False, separators=(",", ":")),
                MATERIAL_ACTION_SCHEMA,
            )
            return self._validate_actions(response, material_subplan, project)
        except StructuredOutputError:
            raise
        except Exception as exc:
            raise StructuredOutputError(f"Material specialist output is invalid: {exc}") from exc

    @staticmethod
    def _validate_actions(
        response: dict[str, Any],
        material_subplan: dict[str, Any],
        project: EngineeringProject,
    ) -> list[dict[str, Any]]:
        if not isinstance(response, dict) or set(response) != {"actions"}:
            raise StructuredOutputError("Material output requires only an actions list")
        rows = response.get("actions")
        if not isinstance(rows, list) or not rows:
            raise StructuredOutputError("Material actions must be a non-empty list")
        normalized: list[dict[str, Any]] = []
        operation = str(material_subplan.get("operation", "create_assign"))
        for row in rows:
            if not isinstance(row, dict):
                raise StructuredOutputError("Each material action must be a dictionary")
            action = row.get("action")
            name = str(row.get("name", "")).strip()
            if not name or action not in {"create_material", "assign_material", "delete_material"}:
                raise StructuredOutputError("Material action or name is invalid")
            if "id" in row or "material_id" in row or "materialId" in row:
                raise StructuredOutputError("Material actions must not contain internal IDs")
            allowed = {
                "create_material": {"action", "name", "E", "nu", "color", "unit_weight"},
                "assign_material": {"action", "name", "thickness", "plane_mode"},
                "delete_material": {"action", "name"},
            }[action]
            required = {
                "create_material": {"action", "name", "E", "nu"},
                "assign_material": {"action", "name", "thickness", "plane_mode"},
                "delete_material": {"action", "name"},
            }[action]
            if not required.issubset(row) or not set(row).issubset(allowed):
                raise StructuredOutputError(f"Invalid fields for {action}")
            item = dict(row)
            item["name"] = name
            if action == "create_material":
                item["E"] = float(item["E"])
                item["nu"] = float(item["nu"])
                item["unit_weight"] = float(item.get("unit_weight", 0.0))
                if item["E"] <= 0.0 or not -1.0 < item["nu"] < 0.5 or item["unit_weight"] < 0.0:
                    raise StructuredOutputError("Material physical parameters are invalid")
            elif action == "assign_material":
                item["thickness"] = float(item["thickness"])
                item["plane_mode"] = str(item["plane_mode"])
                if item["thickness"] <= 0.0 or item["plane_mode"] not in {"stress", "strain"}:
                    raise StructuredOutputError("Section parameters are invalid")
            normalized.append(item)
        if operation == "delete":
            if any(row["action"] != "delete_material" for row in normalized):
                raise StructuredOutputError("Delete subplan permits only delete_material")
        else:
            if any(row["action"] == "delete_material" for row in normalized):
                raise StructuredOutputError("Create/assign subplan must not delete materials")
            if not any(row["action"] == "assign_material" for row in normalized):
                raise StructuredOutputError("Material subplan requires assign_material")
            expected_name = str(material_subplan["name"])
            for row in normalized:
                if row["name"].casefold() != expected_name.casefold():
                    raise StructuredOutputError("Material actions must preserve the subplan name")
                if row["action"] == "create_material" and (
                    row["E"] != float(material_subplan["E"])
                    or row["nu"] != float(material_subplan["nu"])
                ):
                    raise StructuredOutputError("Material action must preserve E and nu")
                if row["action"] == "assign_material" and (
                    row["thickness"] != float(material_subplan["thickness"])
                    or row["plane_mode"] != str(material_subplan["plane_mode"])
                ):
                    raise StructuredOutputError("Material action must preserve Section values")
            matching_material_exists = (
                MaterialAgent._find_matching_subplan_material(project, material_subplan)
                is not None
            )
            creates_matching_material = any(
                row["action"] == "create_material"
                and row["name"].casefold() == expected_name.casefold()
                and row["E"] == float(material_subplan["E"])
                and row["nu"] == float(material_subplan["nu"])
                for row in normalized
            )
            if not matching_material_exists and not creates_matching_material:
                raise StructuredOutputError(
                    "No existing material matches name + E + nu; create_material is required"
                )
            if not matching_material_exists:
                create_index = next(
                    index
                    for index, row in enumerate(normalized)
                    if row["action"] == "create_material"
                    and row["name"].casefold() == expected_name.casefold()
                    and row["E"] == float(material_subplan["E"])
                    and row["nu"] == float(material_subplan["nu"])
                )
                first_assign_index = next(
                    index
                    for index, row in enumerate(normalized)
                    if row["action"] == "assign_material"
                )
                if first_assign_index < create_index:
                    raise StructuredOutputError(
                        "create_material must precede assign_material when no exact material exists"
                    )
        return normalized

    @staticmethod
    def _find_material_by_name(project: EngineeringProject, name: str):
        return next(
            (row for row in reversed(project.materials) if row.name.casefold() == name.casefold()),
            None,
        )

    @staticmethod
    def _find_matching_material(project: EngineeringProject, action: dict[str, Any]):
        return next(
            (
                row
                for row in project.materials
                if row.name.casefold() == action["name"].casefold()
                and row.young_modulus == action["E"]
                and row.poisson_ratio == action["nu"]
            ),
            None,
        )

    @staticmethod
    def _find_matching_subplan_material(
        project: EngineeringProject,
        material_subplan: dict[str, Any],
    ):
        name = str(material_subplan["name"])
        young_modulus = float(material_subplan["E"])
        poisson_ratio = float(material_subplan["nu"])
        return next(
            (
                row
                for row in reversed(project.materials)
                if row.name.casefold() == name.casefold()
                and row.young_modulus == young_modulus
                and row.poisson_ratio == poisson_ratio
            ),
            None,
        )

    @staticmethod
    def _resolve_section_defaults(
        project: EngineeringProject,
        thickness: float | None,
        plane_mode: str | None,
    ) -> tuple[float, str]:
        default_section = project.sections[0] if project.sections else None
        resolved_thickness = (
            float(thickness)
            if thickness is not None
            else float(default_section.thickness if default_section else 0.01)
        )
        resolved_plane_mode = (
            str(plane_mode)
            if plane_mode is not None
            else str(default_section.plane_mode if default_section else "stress")
        )
        return resolved_thickness, resolved_plane_mode

    def createMaterial(
        self,
        name: str,
        E: float,
        nu: float,
        project: EngineeringProject,
    ) -> str:
        return self.create_material(name, E, nu, project)

    def deleteMaterial(self, materialId: str, project: EngineeringProject) -> bool:
        return self.delete_material(materialId, project)

    def assignMaterial(self, materialId: str, project: EngineeringProject) -> bool:
        return self.assign_material(materialId, project)
