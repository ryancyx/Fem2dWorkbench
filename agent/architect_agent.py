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
context. Fem2dWorkbench Agent 1.0 can execute only plane stress. If the user explicitly
requests plane strain, preserve that intent as plane_mode="strain"; never silently change
it to plane stress. The Agent capability contract will stop before engineering execution
and ask the user whether to revise the plan. The requestedResult field is independent:
requestedResult="strain" means strain visualization/output and is valid with
plane_mode="stress". Return data only through the requested structured-output schema."""


PLANE_STRAIN_UNSUPPORTED_MESSAGE = (
    "当前 Fem2dWorkbench Agent 1.0 后端仅支持平面应力（plane stress），"
    "暂不支持平面应变（plane strain）。如需继续，请确认是否改用 plane stress。"
)


class UnsupportedCapabilityError(ValueError):
    """The plan is valid, but its requested analysis is outside Agent 1.0."""


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
        self._pending_unsupported_plan: SimulationPlan | None = None

    def create_plan(self, user_input: str, project: EngineeringProject) -> SimulationPlan:
        if self._pending_unsupported_plan is not None:
            return self.revise_plan(
                user_input,
                self._pending_unsupported_plan,
                project,
            )
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
        base_plan = self._pending_unsupported_plan or current_plan
        content = {
            "mode": "revise",
            "userInput": str(user_input),
            "currentPlan": base_plan.to_dict(),
            "projectContext": self._project_context(project),
        }
        return self._request_plan(content, expected_version=base_plan.version + 1)

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
            plan = SimulationPlan.from_dict(response)
        except (KeyError, TypeError, ValueError) as exc:
            raise StructuredOutputError(f"Invalid Architect structured output: {exc}") from exc
        try:
            self._validate_capabilities(plan)
        except UnsupportedCapabilityError:
            self._pending_unsupported_plan = plan
            raise
        self._pending_unsupported_plan = None
        return plan

    @staticmethod
    def _validate_capabilities(plan: SimulationPlan) -> None:
        if plan.material["plane_mode"] == "strain":
            raise UnsupportedCapabilityError(PLANE_STRAIN_UNSUPPORTED_MESSAGE)

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
            "agentCapabilities": {
                "planeModes": ["stress"],
                "unsupportedPlaneModesRequireUserRevision": ["strain"],
            },
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
