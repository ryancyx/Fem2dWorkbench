from __future__ import annotations

import json
import math
from typing import Any

from agent.llm_client import LLMClient, StructuredOutputError
from agent.simulation_plan import SimulationPlan
from core.engineering.engineering_project import EngineeringProject
from core.engineering.geometry import GeometryModel
from services.part_edit_service import add_rectangle_part, add_sketch_part
from services.sketch_geometry_service import create_geometry_from_polygon_points


GEOMETRY_SYSTEM_PROMPT = """You are the Geometry specialist for Fem2dWorkbench Agent 1.0.
Read only the structured geometry subplan and the compact project context. Produce one
schema-constrained geometry action: create_rectangle or create_circle. Preserve all
numeric dimensions and coordinates from the subplan. Do not invent entity IDs, perform
meshing, solve FEM equations, or modify materials, constraints, or loads."""


GEOMETRY_ACTION_SCHEMA: dict[str, Any] = {
    "title": "GeometryAction",
    "type": "object",
    "additionalProperties": False,
    "required": ["action", "parameters"],
    "properties": {
        "action": {"enum": ["create_rectangle", "create_circle"]},
        "parameters": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "width": {"type": "number", "exclusiveMinimum": 0},
                "height": {"type": "number", "exclusiveMinimum": 0},
                "originX": {"type": "number"},
                "originY": {"type": "number"},
                "centerX": {"type": "number"},
                "centerY": {"type": "number"},
                "radius": {"type": "number", "exclusiveMinimum": 0},
            },
        },
    },
}


class GeometryAgent:
    CIRCLE_SEGMENTS = 64

    def __init__(self, llm: LLMClient) -> None:
        self.llm = llm

    def create(self, plan: SimulationPlan, project: EngineeringProject) -> bool:
        action = self._request_action(plan.geometry, project)
        parameters = action["parameters"]
        if action["action"] == "create_rectangle":
            return self.create_rectangle(
                width=float(parameters["width"]),
                height=float(parameters["height"]),
                project=project,
                origin_x=float(parameters.get("originX", 0.0)),
                origin_y=float(parameters.get("originY", 0.0)),
            )
        if action["action"] == "create_circle":
            return self.create_circle(
                center_x=float(parameters["centerX"]),
                center_y=float(parameters["centerY"]),
                radius=float(parameters["radius"]),
                project=project,
            )
        raise StructuredOutputError(f"Unsupported geometry action: {action['action']}")

    def _request_action(
        self,
        geometry_subplan: dict[str, Any],
        project: EngineeringProject,
    ) -> dict[str, Any]:
        content = {
            "geometry": geometry_subplan,
            "projectContext": {
                "projectName": project.name,
                "partCount": len(project.parts),
                "hasManagedPart": bool(project.metadata.get("agent_managed_part_id")),
            },
        }
        try:
            response = self.llm.request(
                GEOMETRY_SYSTEM_PROMPT,
                json.dumps(content, ensure_ascii=False, separators=(",", ":")),
                GEOMETRY_ACTION_SCHEMA,
            )
            return self._validate_action(response, geometry_subplan)
        except StructuredOutputError:
            raise
        except Exception as exc:
            raise StructuredOutputError(f"Geometry specialist output is invalid: {exc}") from exc

    @staticmethod
    def _validate_action(
        response: dict[str, Any],
        geometry_subplan: dict[str, Any],
    ) -> dict[str, Any]:
        if not isinstance(response, dict) or set(response) != {"action", "parameters"}:
            raise StructuredOutputError("Geometry action requires only action and parameters")
        action = response.get("action")
        parameters = response.get("parameters")
        if not isinstance(parameters, dict):
            raise StructuredOutputError("Geometry action parameters must be a dictionary")
        geometry_type = geometry_subplan["type"]
        expected_action = f"create_{geometry_type}"
        if action != expected_action:
            raise StructuredOutputError(
                f"Geometry action {action!r} does not match subplan type {geometry_type!r}"
            )
        expected_keys = (
            {"width", "height", "originX", "originY"}
            if geometry_type == "rectangle"
            else {"centerX", "centerY", "radius"}
        )
        required_keys = (
            {"width", "height"} if geometry_type == "rectangle" else {"centerX", "centerY", "radius"}
        )
        if not required_keys.issubset(parameters) or not set(parameters).issubset(expected_keys):
            raise StructuredOutputError("Geometry action contains missing or unsupported parameters")
        normalized = {key: float(value) for key, value in parameters.items()}
        expected = {
            key: float(geometry_subplan.get(key, 0.0))
            for key in expected_keys
            if key in geometry_subplan or key in required_keys
        }
        if normalized != expected:
            raise StructuredOutputError("Geometry action must preserve the validated subplan values")
        if any(value <= 0.0 for key, value in normalized.items() if key in {"width", "height", "radius"}):
            raise StructuredOutputError("Geometry dimensions must be positive")
        return {"action": action, "parameters": normalized}

    def create_rectangle(
        self,
        width: float,
        height: float,
        project: EngineeringProject,
        origin_x: float = 0.0,
        origin_y: float = 0.0,
    ) -> bool:
        part = self._managed_part(project)
        if part is None:
            add_rectangle_part(
                project=project,
                name="agent_rectangle",
                width=width,
                height=height,
                make_active=True,
            )
            part = project.get_part_by_id(str(project.metadata["active_part_id"]))
        else:
            part.name = "agent_rectangle"
            part.geometry = GeometryModel.create_rectangle(width=width, height=height)
            project.metadata["active_part_id"] = part.id
        if part is None:
            raise RuntimeError("Rectangle part was not added to the project")
        project.metadata["agent_managed_part_id"] = part.id
        if origin_x or origin_y:
            for point in part.geometry.points:
                point.x += origin_x
                point.y += origin_y
        project.validate_references()
        return True

    def create_circle(
        self,
        center_x: float,
        center_y: float,
        radius: float,
        project: EngineeringProject,
    ) -> bool:
        if radius <= 0.0:
            raise ValueError("radius must be positive")
        points = [
            (
                center_x + radius * math.cos(2.0 * math.pi * index / self.CIRCLE_SEGMENTS),
                center_y + radius * math.sin(2.0 * math.pi * index / self.CIRCLE_SEGMENTS),
            )
            for index in range(self.CIRCLE_SEGMENTS)
        ]
        part = self._managed_part(project)
        if part is None:
            add_sketch_part(project, name="agent_circle", make_active=True)
            part = project.get_part_by_id(str(project.metadata["active_part_id"]))
        if part is None:
            raise RuntimeError("Circle part was not added to the project")
        part.name = "agent_circle"
        part.geometry = create_geometry_from_polygon_points(points)
        project.metadata["active_part_id"] = part.id
        project.metadata["agent_managed_part_id"] = part.id
        project.validate_references()
        return True

    @staticmethod
    def _managed_part(project: EngineeringProject):
        part_id = str(project.metadata.get("agent_managed_part_id", ""))
        return project.get_part_by_id(part_id) if part_id else None

    def createRectangle(
        self,
        width: float,
        height: float,
        project: EngineeringProject,
    ) -> bool:
        return self.create_rectangle(width, height, project)

    def createCircle(
        self,
        centerX: float,
        centerY: float,
        radius: float,
        project: EngineeringProject,
    ) -> bool:
        return self.create_circle(centerX, centerY, radius, project)
