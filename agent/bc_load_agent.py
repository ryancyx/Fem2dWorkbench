from __future__ import annotations

import json
import math
from collections.abc import Iterable
from typing import Any, Literal

from agent.llm_client import LLMClient, StructuredOutputError
from agent.simulation_plan import SimulationPlan
from core.engineering.boundary_condition_definition import BoundaryConditionDefinition
from core.engineering.engineering_project import EngineeringProject
from core.engineering.geometry import GeometryEdge, GeometryModel, GeometryPoint
from core.engineering.load_definition import LoadDefinition


EntityKind = Literal["point", "edge"]


BC_LOAD_SYSTEM_PROMPT = """You are the boundary-condition and load specialist for
Fem2dWorkbench Agent 1.0. Convert the validated constraint/load subplan into only the
schema-constrained actions add_point_constraint, add_edge_constraint, add_point_load,
or add_edge_load. Targets must remain semantic selectors or coordinates. Never emit or
invent internal point/edge IDs; deterministic code resolves targets after validation.
Preserve every displacement component and two-dimensional load vector. Do not modify
geometry, materials, mesh, or solver state."""


BC_LOAD_ACTION_SCHEMA: dict[str, Any] = {
    "title": "BCLoadActions",
    "type": "object",
    "additionalProperties": False,
    "required": ["actions"],
    "properties": {
        "actions": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["action", "target"],
                "properties": {
                    "action": {
                        "enum": [
                            "add_point_constraint",
                            "add_edge_constraint",
                            "add_point_load",
                            "add_edge_load",
                        ]
                    },
                    "target": {
                        "type": "object",
                        "additionalProperties": False,
                        "properties": {
                            "selector": {"type": "string", "minLength": 1},
                            "coordinate": {
                                "type": "array",
                                "prefixItems": [{"type": "number"}, {"type": "number"}],
                                "minItems": 2,
                                "maxItems": 2,
                            },
                        },
                    },
                    "ux": {"type": ["number", "null"]},
                    "uy": {"type": ["number", "null"]},
                    "vector": {
                        "type": "array",
                        "prefixItems": [{"type": "number"}, {"type": "number"}],
                        "minItems": 2,
                        "maxItems": 2,
                    },
                },
            },
        }
    },
}


class BCLoadAgent:
    def __init__(self, llm: LLMClient) -> None:
        self.llm = llm

    def apply(self, plan: SimulationPlan, project: EngineeringProject) -> bool:
        actions = self._request_actions(plan, project)
        resolved_actions: list[tuple[dict[str, Any], str]] = []
        for row in actions:
            action = row["action"]
            entity_kind: EntityKind = "point" if "point" in action else "edge"
            target_ids = self.resolve_target(row["target"], entity_kind, project)
            for target_id in target_ids:
                target_type = "geometry_point" if entity_kind == "point" else "geometry_edge"
                self._require_entity(project, target_type, target_id)
                resolved_actions.append((row, target_id))

        self._step_id(project)
        old_boundary_conditions = list(project.boundary_conditions)
        old_loads = list(project.loads)
        old_metadata = dict(project.metadata)
        created_boundary_condition_ids: list[str] = []
        created_load_ids: list[str] = []
        try:
            self.clear_managed_definitions(project)
            for row, target_id in resolved_actions:
                action = row["action"]
                if action == "add_point_constraint":
                    self.add_point_constraint(target_id, row["ux"], row["uy"], project)
                    created_boundary_condition_ids.append(project.boundary_conditions[-1].id)
                elif action == "add_edge_constraint":
                    self.add_edge_constraint(target_id, row["ux"], row["uy"], project)
                    created_boundary_condition_ids.append(project.boundary_conditions[-1].id)
                elif action == "add_point_load":
                    self.add_point_load(target_id, row["vector"][0], row["vector"][1], project)
                    created_load_ids.append(project.loads[-1].id)
                elif action == "add_edge_load":
                    self.add_edge_load(target_id, row["vector"][0], row["vector"][1], project)
                    created_load_ids.append(project.loads[-1].id)
            project.metadata["agent_boundary_condition_ids"] = created_boundary_condition_ids
            project.metadata["agent_load_ids"] = created_load_ids
            project.validate_references()
        except Exception:
            project.boundary_conditions = old_boundary_conditions
            project.loads = old_loads
            project.metadata = old_metadata
            raise
        return True

    def _request_actions(
        self,
        plan: SimulationPlan,
        project: EngineeringProject,
    ) -> list[dict[str, Any]]:
        geometry = self._active_geometry(project)
        xs = [point.x for point in geometry.points]
        ys = [point.y for point in geometry.points]
        content = {
            "constraintsAndLoads": {
                "pointConstraints": plan.point_constraints,
                "edgeConstraints": plan.edge_constraints,
                "pointLoads": plan.point_loads,
                "edgeLoads": plan.edge_loads,
            },
            "geometryContext": {
                "pointCount": len(geometry.points),
                "edgeCount": len(geometry.edges),
                "bounds": [min(xs), min(ys), max(xs), max(ys)] if xs and ys else [],
                "points": [[point.x, point.y] for point in geometry.points],
                "edges": [
                    [
                        [next(point for point in geometry.points if point.id == edge.start_point_id).x,
                         next(point for point in geometry.points if point.id == edge.start_point_id).y],
                        [next(point for point in geometry.points if point.id == edge.end_point_id).x,
                         next(point for point in geometry.points if point.id == edge.end_point_id).y],
                    ]
                    for edge in geometry.edges
                ],
            },
        }
        try:
            response = self.llm.request(
                BC_LOAD_SYSTEM_PROMPT,
                json.dumps(content, ensure_ascii=False, separators=(",", ":")),
                BC_LOAD_ACTION_SCHEMA,
            )
            return self._validate_actions(response, plan)
        except StructuredOutputError:
            raise
        except Exception as exc:
            raise StructuredOutputError(f"BC/Load specialist output is invalid: {exc}") from exc

    @staticmethod
    def _validate_actions(
        response: dict[str, Any],
        plan: SimulationPlan,
    ) -> list[dict[str, Any]]:
        if not isinstance(response, dict) or set(response) != {"actions"}:
            raise StructuredOutputError("BC/Load output requires only an actions list")
        rows = response.get("actions")
        if not isinstance(rows, list):
            raise StructuredOutputError("BC/Load actions must be a list")
        expected: list[dict[str, Any]] = []
        expected.extend(
            {"action": "add_point_constraint", **row} for row in plan.point_constraints
        )
        expected.extend(
            {"action": "add_edge_constraint", **row} for row in plan.edge_constraints
        )
        expected.extend({"action": "add_point_load", **row} for row in plan.point_loads)
        expected.extend({"action": "add_edge_load", **row} for row in plan.edge_loads)
        normalized: list[dict[str, Any]] = []
        for row in rows:
            if not isinstance(row, dict):
                raise StructuredOutputError("Each BC/Load action must be a dictionary")
            action = row.get("action")
            is_constraint = action in {"add_point_constraint", "add_edge_constraint"}
            is_load = action in {"add_point_load", "add_edge_load"}
            allowed = {"action", "target", "ux", "uy"} if is_constraint else {"action", "target", "vector"}
            required = allowed
            if not (is_constraint or is_load) or set(row) != required:
                raise StructuredOutputError("BC/Load action fields are invalid")
            target = row.get("target")
            if not isinstance(target, dict) or set(target) not in ({"selector"}, {"coordinate"}):
                raise StructuredOutputError("BC/Load targets must use selector or coordinate only")
            if any(key in target for key in {"id", "point_id", "pointId", "edge_id", "edgeId"}):
                raise StructuredOutputError("BC/Load actions must not contain internal IDs")
            item = {"action": action, "target": dict(target)}
            if is_constraint:
                ux = row.get("ux")
                uy = row.get("uy")
                if ux is None and uy is None:
                    raise StructuredOutputError("Constraint action must constrain ux or uy")
                item.update(ux=None if ux is None else float(ux), uy=None if uy is None else float(uy))
            else:
                vector = row.get("vector")
                if not isinstance(vector, (list, tuple)) or len(vector) != 2:
                    raise StructuredOutputError("Load action vector must contain two components")
                item["vector"] = [float(vector[0]), float(vector[1])]
            normalized.append(item)
        if normalized != expected:
            raise StructuredOutputError("BC/Load actions must preserve the validated subplan")
        return normalized

    @staticmethod
    def clear_managed_definitions(project: EngineeringProject) -> None:
        boundary_condition_ids = {
            str(item) for item in project.metadata.get("agent_boundary_condition_ids", [])
        }
        load_ids = {str(item) for item in project.metadata.get("agent_load_ids", [])}
        if boundary_condition_ids:
            project.boundary_conditions = [
                row for row in project.boundary_conditions if row.id not in boundary_condition_ids
            ]
        if load_ids:
            project.loads = [row for row in project.loads if row.id not in load_ids]
        project.metadata["agent_boundary_condition_ids"] = []
        project.metadata["agent_load_ids"] = []

    def resolve_target(
        self,
        target: dict[str, Any],
        entity_kind: EntityKind,
        project: EngineeringProject,
    ) -> list[str]:
        geometry = self._active_geometry(project)
        if "coordinate" in target:
            coordinate = target["coordinate"]
            ids = self._resolve_coordinate(geometry, entity_kind, float(coordinate[0]), float(coordinate[1]))
        else:
            selector = str(target.get("selector", "")).strip().lower()
            ids = self._resolve_selector(geometry, entity_kind, selector)
        if not ids:
            raise ValueError(f"Target {target!r} did not resolve to any geometry {entity_kind}")
        return ids

    def add_point_constraint(
        self,
        point_id: str,
        ux: float | None,
        uy: float | None,
        project: EngineeringProject,
    ) -> bool:
        return self._add_constraint("geometry_point", point_id, ux, uy, project)

    def add_edge_constraint(
        self,
        edge_id: str,
        ux: float | None,
        uy: float | None,
        project: EngineeringProject,
    ) -> bool:
        return self._add_constraint("geometry_edge", edge_id, ux, uy, project)

    def add_point_load(
        self,
        point_id: str,
        fx: float,
        fy: float,
        project: EngineeringProject,
    ) -> bool:
        return self._add_load("geometry_point", point_id, "nodal_concentrated", fx, fy, project)

    def add_edge_load(
        self,
        edge_id: str,
        qx: float,
        qy: float,
        project: EngineeringProject,
    ) -> bool:
        return self._add_load("geometry_edge", edge_id, "edge_uniform", qx, qy, project)

    def _add_constraint(
        self,
        target_type: str,
        target_id: str,
        ux: float | None,
        uy: float | None,
        project: EngineeringProject,
    ) -> bool:
        if ux is None and uy is None:
            raise ValueError("A constraint must define ux or uy")
        self._require_entity(project, target_type, target_id)
        project.add_boundary_condition(
            BoundaryConditionDefinition(
                id=self._unique_id("bc", (row.id for row in project.boundary_conditions)),
                name=f"agent_constraint_{target_id}",
                step_id=self._step_id(project),
                target_type=target_type,
                target_id=target_id,
                ux_fixed=ux is not None,
                uy_fixed=uy is not None,
                ux_value=0.0 if ux is None else float(ux),
                uy_value=0.0 if uy is None else float(uy),
            )
        )
        project.validate_references()
        return True

    def _add_load(
        self,
        target_type: str,
        target_id: str,
        load_type: str,
        x_component: float,
        y_component: float,
        project: EngineeringProject,
    ) -> bool:
        self._require_entity(project, target_type, target_id)
        project.add_load(
            LoadDefinition(
                id=self._unique_id("load", (row.id for row in project.loads)),
                name=f"agent_load_{target_id}",
                step_id=self._step_id(project),
                target_type=target_type,
                target_id=target_id,
                load_type=load_type,
                qx=float(x_component),
                qy=float(y_component),
            )
        )
        project.validate_references()
        return True

    @staticmethod
    def _active_geometry(project: EngineeringProject) -> GeometryModel:
        part_id = str(project.metadata.get("active_part_id", ""))
        part = project.get_part_by_id(part_id) if part_id else None
        if part is None and len(project.parts) == 1:
            part = project.parts[0]
        if part is None:
            raise ValueError("The project has no unambiguous active part")
        return part.geometry

    def _resolve_selector(
        self,
        geometry: GeometryModel,
        entity_kind: EntityKind,
        selector: str,
    ) -> list[str]:
        if selector in {"boundary", "outer_boundary", "all", "all_edges"}:
            if entity_kind != "edge":
                raise ValueError(f"Selector {selector!r} is only valid for edges")
            return [edge.id for edge in geometry.edges]
        if entity_kind == "point":
            return self._select_points(geometry.points, selector)
        return self._select_edges(geometry, selector)

    @staticmethod
    def _select_points(points: list[GeometryPoint], selector: str) -> list[str]:
        if not points:
            return []
        xs = [point.x for point in points]
        ys = [point.y for point in points]
        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)
        if selector in {"left", "right", "top", "bottom"}:
            target_value = {"left": min_x, "right": max_x, "top": max_y, "bottom": min_y}[selector]
            coordinate = (lambda row: row.x) if selector in {"left", "right"} else (lambda row: row.y)
            tolerance = max(max_x - min_x, max_y - min_y, 1.0) * 1.0e-9
            return [point.id for point in points if abs(coordinate(point) - target_value) <= tolerance]
        corner_map = {
            "bottom_left": (min_x, min_y),
            "bottom_right": (max_x, min_y),
            "top_left": (min_x, max_y),
            "top_right": (max_x, max_y),
            "center": ((min_x + max_x) / 2.0, (min_y + max_y) / 2.0),
        }
        if selector not in corner_map:
            return []
        target_x, target_y = corner_map[selector]
        nearest = min(points, key=lambda point: (point.x - target_x) ** 2 + (point.y - target_y) ** 2)
        return [nearest.id]

    @staticmethod
    def _select_edges(geometry: GeometryModel, selector: str) -> list[str]:
        if selector not in {"left", "right", "top", "bottom"}:
            return []
        point_by_id = {point.id: point for point in geometry.points}
        rows = []
        for edge in geometry.edges:
            start = point_by_id[edge.start_point_id]
            end = point_by_id[edge.end_point_id]
            rows.append((edge.id, (start.x + end.x) / 2.0, (start.y + end.y) / 2.0))
        if not rows:
            return []
        coordinate_index = 1 if selector in {"left", "right"} else 2
        values = [row[coordinate_index] for row in rows]
        target_value = min(values) if selector in {"left", "bottom"} else max(values)
        span = max(max(values) - min(values), 1.0)
        tolerance = span * 1.0e-9
        return [row[0] for row in rows if abs(row[coordinate_index] - target_value) <= tolerance]

    @staticmethod
    def _resolve_coordinate(
        geometry: GeometryModel,
        entity_kind: EntityKind,
        x: float,
        y: float,
    ) -> list[str]:
        tolerance = BCLoadAgent._coordinate_tolerance(geometry)
        if entity_kind == "point":
            if not geometry.points:
                return []
            point = min(geometry.points, key=lambda row: (row.x - x) ** 2 + (row.y - y) ** 2)
            distance = math.hypot(point.x - x, point.y - y)
            return [point.id] if distance <= tolerance else []
        point_by_id = {point.id: point for point in geometry.points}
        if not geometry.edges:
            return []
        edge_distances = [
            (
                row,
                BCLoadAgent._point_segment_distance(
                    x,
                    y,
                    point_by_id[row.start_point_id],
                    point_by_id[row.end_point_id],
                ),
            )
            for row in geometry.edges
        ]
        edge, distance = min(edge_distances, key=lambda item: item[1])
        return [edge.id] if distance <= tolerance else []

    @staticmethod
    def _coordinate_tolerance(geometry: GeometryModel) -> float:
        if not geometry.points:
            return 1.0e-9
        xs = [point.x for point in geometry.points]
        ys = [point.y for point in geometry.points]
        span = max(max(xs) - min(xs), max(ys) - min(ys))
        return max(span * 1.0e-6, 1.0e-9)

    @staticmethod
    def _point_segment_distance(x: float, y: float, start: GeometryPoint, end: GeometryPoint) -> float:
        dx = end.x - start.x
        dy = end.y - start.y
        length_squared = dx * dx + dy * dy
        if length_squared <= 1.0e-24:
            return math.hypot(x - start.x, y - start.y)
        ratio = max(0.0, min(1.0, ((x - start.x) * dx + (y - start.y) * dy) / length_squared))
        return math.hypot(x - (start.x + ratio * dx), y - (start.y + ratio * dy))

    @staticmethod
    def _step_id(project: EngineeringProject) -> str:
        if not project.analysis_steps:
            raise ValueError("The project has no analysis step")
        return project.analysis_steps[0].id

    @staticmethod
    def _unique_id(base_id: str, existing_ids: Iterable[str]) -> str:
        existing = set(existing_ids)
        if base_id not in existing:
            return base_id
        index = 2
        while f"{base_id}_{index}" in existing:
            index += 1
        return f"{base_id}_{index}"

    @staticmethod
    def _require_entity(project: EngineeringProject, target_type: str, target_id: str) -> None:
        geometry = BCLoadAgent._active_geometry(project)
        existing = (
            {point.id for point in geometry.points}
            if target_type == "geometry_point"
            else {edge.id for edge in geometry.edges}
        )
        if target_id not in existing:
            raise ValueError(f"Unknown {target_type}: {target_id}")

    def addPointConstraint(self, pointId: str, ux: float | None, uy: float | None, project: EngineeringProject) -> bool:
        return self.add_point_constraint(pointId, ux, uy, project)

    def addEdgeConstraint(self, edgeId: str, ux: float | None, uy: float | None, project: EngineeringProject) -> bool:
        return self.add_edge_constraint(edgeId, ux, uy, project)

    def addPointLoad(self, pointId: str, fx: float, fy: float, project: EngineeringProject) -> bool:
        return self.add_point_load(pointId, fx, fy, project)

    def addEdgeLoad(self, edgeId: str, qx: float, qy: float, project: EngineeringProject) -> bool:
        return self.add_edge_load(edgeId, qx, qy, project)
