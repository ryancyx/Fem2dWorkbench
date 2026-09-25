from __future__ import annotations

import json
from typing import Any

from agent.llm_client import LLMClient, StructuredOutputError
from agent.simulation_plan import SimulationPlan
from core.engineering.engineering_project import EngineeringProject


ARCHITECT_SYSTEM_PROMPT = """You are the Architect Agent for Fem2dWorkbench Agent 1.0.
Convert the user's modeling intent into exactly one schema-constrained SimulationPlan.
Do not solve FEM equations, generate meshes, or control workflow stages.
Never invent internal point, edge, face, material, section, part, or step IDs.
Targets must use semantic selectors or coordinates. Use only rectangle or circle geometry.
Semantic selectors must be exact canonical tokens: left, right, top, bottom,
outer_boundary, bottom_left, bottom_right, top_left, top_right, or center. Never write
natural-language variants such as "left edge" or "bottom-left corner".
Point loads are [Fx, Fy]; edge loads are [qx, qy]. A null displacement component means
that direction is unconstrained. Material thickness and plane_mode are mandatory: use
explicit user values when supplied, otherwise inherit the defaults supplied in project
context. Return data only through the requested structured-output schema."""


SIMULATION_PLAN_SCHEMA: dict[str, Any] = {
    "title": "SimulationPlan",
    "type": "object",
    "additionalProperties": False,
    "required": [
        "version",
        "geometry",
        "material",
        "pointConstraints",
        "edgeConstraints",
        "pointLoads",
        "edgeLoads",
        "meshSize",
        "requestedResult",
    ],
    "properties": {
        "version": {"type": "integer", "minimum": 1},
        "geometry": {
            "type": "object",
            "required": ["type"],
            "properties": {
                "type": {"enum": ["rectangle", "circle"]},
                "width": {"type": "number", "exclusiveMinimum": 0},
                "height": {"type": "number", "exclusiveMinimum": 0},
                "originX": {"type": "number"},
                "originY": {"type": "number"},
                "centerX": {"type": "number"},
                "centerY": {"type": "number"},
                "radius": {"type": "number", "exclusiveMinimum": 0},
            },
        },
        "material": {
            "type": "object",
            "additionalProperties": True,
            "required": ["name", "E", "nu", "thickness", "plane_mode"],
            "properties": {
                "name": {"type": "string", "minLength": 1},
                "E": {"type": "number", "exclusiveMinimum": 0},
                "nu": {"type": "number", "exclusiveMinimum": -1, "exclusiveMaximum": 0.5},
                "thickness": {"type": "number", "exclusiveMinimum": 0},
                "plane_mode": {"enum": ["stress", "strain"]},
            },
        },
        "pointConstraints": {"type": "array", "items": {"$ref": "#/$defs/constraint"}},
        "edgeConstraints": {"type": "array", "items": {"$ref": "#/$defs/constraint"}},
        "pointLoads": {"type": "array", "items": {"$ref": "#/$defs/load"}},
        "edgeLoads": {"type": "array", "items": {"$ref": "#/$defs/load"}},
        "meshSize": {"type": "number", "exclusiveMinimum": 0},
        "requestedResult": {"enum": ["displacement", "stress", "strain", "von_mises"]},
    },
    "$defs": {
        "target": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "selector": {
                    "enum": [
                        "left",
                        "right",
                        "top",
                        "bottom",
                        "outer_boundary",
                        "bottom_left",
                        "bottom_right",
                        "top_left",
                        "top_right",
                        "center",
                    ]
                },
                "coordinate": {
                    "type": "array",
                    "prefixItems": [{"type": "number"}, {"type": "number"}],
                    "minItems": 2,
                    "maxItems": 2,
                },
            },
            "anyOf": [{"required": ["selector"]}, {"required": ["coordinate"]}],
        },
        "constraint": {
            "type": "object",
            "additionalProperties": False,
            "required": ["target", "ux", "uy"],
            "properties": {
                "target": {"$ref": "#/$defs/target"},
                "ux": {"type": ["number", "null"]},
                "uy": {"type": ["number", "null"]},
            },
        },
        "load": {
            "type": "object",
            "additionalProperties": False,
            "required": ["target", "vector"],
            "properties": {
                "target": {"$ref": "#/$defs/target"},
                "vector": {
                    "type": "array",
                    "prefixItems": [{"type": "number"}, {"type": "number"}],
                    "minItems": 2,
                    "maxItems": 2,
                },
            },
        },
    },
}


class ArchitectAgent:
    def __init__(self, llm: LLMClient) -> None:
        self.llm = llm

    def create_plan(self, user_input: str, project: EngineeringProject) -> SimulationPlan:
        content = {
            "mode": "create",
            "userInput": str(user_input),
            "projectContext": self._project_context(project),
        }
        return self._request_plan(content, expected_version=1)

    def revise_plan(
        self,
        user_input: str,
        current_plan: SimulationPlan,
        project: EngineeringProject,
    ) -> SimulationPlan:
        content = {
            "mode": "revise",
            "userInput": str(user_input),
            "currentPlan": current_plan.to_dict(),
            "projectContext": self._project_context(project),
        }
        return self._request_plan(content, expected_version=current_plan.version + 1)

    def _request_plan(self, content: dict[str, Any], expected_version: int) -> SimulationPlan:
        try:
            response = self.llm.request(
                system_prompt=ARCHITECT_SYSTEM_PROMPT,
                user_content=json.dumps(content, ensure_ascii=False, separators=(",", ":")),
                schema=SIMULATION_PLAN_SCHEMA,
            )
        except Exception as exc:
            raise StructuredOutputError(f"Architect LLM request failed: {exc}") from exc
        if not isinstance(response, dict):
            raise StructuredOutputError("Architect response must be a dictionary")
        response = dict(response)
        response["version"] = expected_version
        try:
            return SimulationPlan.from_dict(response)
        except (KeyError, TypeError, ValueError) as exc:
            raise StructuredOutputError(f"Invalid Architect structured output: {exc}") from exc

    @staticmethod
    def _project_context(project: EngineeringProject) -> dict[str, Any]:
        default_section = project.sections[0] if project.sections else None
        return {
            "name": project.name,
            "defaultSection": (
                {
                    "thickness": default_section.thickness,
                    "plane_mode": default_section.plane_mode,
                }
                if default_section
                else {"thickness": 0.01, "plane_mode": "stress"}
            ),
            "materials": [material.to_dict() for material in project.materials],
            "parts": [
                {
                    "id": part.id,
                    "name": part.name,
                    "pointCount": len(part.geometry.points),
                    "edgeCount": len(part.geometry.edges),
                    "faceCount": len(part.geometry.faces),
                }
                for part in project.parts
            ],
        }

    def createPlan(self, userInput: str, project: EngineeringProject) -> SimulationPlan:
        return self.create_plan(userInput, project)

    def revisePlan(
        self,
        userInput: str,
        currentPlan: SimulationPlan,
        project: EngineeringProject,
    ) -> SimulationPlan:
        return self.revise_plan(userInput, currentPlan, project)
