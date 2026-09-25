from __future__ import annotations

import json
from copy import deepcopy
from typing import Any

from agent.execution_result import ExecutionResult
from agent.llm_client import LLMClient, StructuredOutputError
from agent.review_models import RepairProposal, ReviewResult
from agent.simulation_plan import SimulationPlan
from core.engineering.engineering_project import EngineeringProject


REVIEWER_SYSTEM_PROMPT = """You are the Reviewer specialist for Fem2dWorkbench Agent 1.0.
Diagnose the execution using all three supplied sources: the validated SimulationPlan,
the compact current EngineeringProject snapshot, and the ExecutionResult. Check plan to
model consistency, geometry targets, material assignment and parameters, two-dimensional
rigid-body restraints (Tx, Ty, Rz), load targets/vectors, mesh state, and the reported
execution error. Every diagnosis must cite concrete evidence from the supplied context.
Return only schema-constrained ReviewResult data. Propose the smallest executable repairs
to the SimulationPlan using semantic selectors or coordinates, never internal entity IDs.
Do not modify the project, run tools, solve equations, or invent evidence. If the model is
consistent and the execution result is successful, set hasProblem=false and return no
repair proposals."""


_TARGET_SCHEMA: dict[str, Any] = {
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
}


REVIEW_RESULT_SCHEMA: dict[str, Any] = {
    "title": "ReviewResult",
    "type": "object",
    "additionalProperties": False,
    "required": ["hasProblem", "diagnosis", "evidence", "proposals"],
    "properties": {
        "hasProblem": {"type": "boolean"},
        "diagnosis": {"type": "string"},
        "evidence": {"type": "array", "items": {"type": "string"}},
        "proposals": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["title", "reason", "changes"],
                "properties": {
                    "title": {"type": "string", "minLength": 1},
                    "reason": {"type": "string", "minLength": 1},
                    "changes": {
                        "type": "object",
                        "additionalProperties": False,
                        "required": ["operation"],
                        "properties": {
                            "operation": {
                                "enum": [
                                    "set_mesh_size",
                                    "update_material",
                                    "replace_geometry",
                                    "add_point_constraint",
                                    "update_point_constraint",
                                    "add_edge_constraint",
                                    "update_edge_constraint",
                                    "add_point_load",
                                    "update_point_load",
                                    "add_edge_load",
                                    "update_edge_load",
                                ]
                            },
                            "meshSize": {"type": "number", "exclusiveMinimum": 0},
                            "geometry": {"type": "object"},
                            "name": {"type": "string", "minLength": 1},
                            "E": {"type": "number", "exclusiveMinimum": 0},
                            "nu": {
                                "type": "number",
                                "exclusiveMinimum": -1,
                                "exclusiveMaximum": 0.5,
                            },
                            "thickness": {"type": "number", "exclusiveMinimum": 0},
                            "plane_mode": {"enum": ["stress", "strain"]},
                            "color": {"type": "string"},
                            "unit_weight": {"type": "number", "minimum": 0},
                            "target": _TARGET_SCHEMA,
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
                },
            },
        },
    },
}


_CHANGE_FIELDS = {
    "set_mesh_size": ({"operation", "meshSize"}, {"operation", "meshSize"}),
    "update_material": (
        {"operation", "name", "E", "nu", "thickness", "plane_mode", "color", "unit_weight"},
        {"operation"},
    ),
    "replace_geometry": ({"operation", "geometry"}, {"operation", "geometry"}),
    "add_point_constraint": ({"operation", "target", "ux", "uy"}, {"operation", "target", "ux", "uy"}),
    "update_point_constraint": ({"operation", "target", "ux", "uy"}, {"operation", "target", "ux", "uy"}),
    "add_edge_constraint": ({"operation", "target", "ux", "uy"}, {"operation", "target", "ux", "uy"}),
    "update_edge_constraint": ({"operation", "target", "ux", "uy"}, {"operation", "target", "ux", "uy"}),
    "add_point_load": ({"operation", "target", "vector"}, {"operation", "target", "vector"}),
    "update_point_load": ({"operation", "target", "vector"}, {"operation", "target", "vector"}),
    "add_edge_load": ({"operation", "target", "vector"}, {"operation", "target", "vector"}),
    "update_edge_load": ({"operation", "target", "vector"}, {"operation", "target", "vector"}),
}


class ReviewerAgent:
    def __init__(self, llm: LLMClient) -> None:
        self.llm = llm

    def review(
        self,
        plan: SimulationPlan,
        project: EngineeringProject,
        execution_result: ExecutionResult,
    ) -> ReviewResult:
        context = self.build_review_context(plan, project, execution_result)
        project_before = project.to_dict()
        try:
            response = self.llm.request(
                REVIEWER_SYSTEM_PROMPT,
                json.dumps(context, ensure_ascii=False, separators=(",", ":")),
                REVIEW_RESULT_SCHEMA,
            )
            result = self.parse_review_result(response, plan)
        except StructuredOutputError:
            raise
        except Exception as exc:
            raise StructuredOutputError(f"Reviewer output is invalid: {exc}") from exc
        if project.to_dict() != project_before:
            raise RuntimeError("Reviewer must not modify EngineeringProject")
        return result

    def build_review_context(
        self,
        plan: SimulationPlan,
        project: EngineeringProject,
        execution_result: ExecutionResult,
    ) -> dict[str, Any]:
        return {
            "simulationPlan": plan.to_dict(),
            "projectSnapshot": self._project_snapshot(project),
            "executionResult": self._execution_snapshot(execution_result),
        }

    def parse_review_result(
        self,
        response: dict[str, Any],
        plan: SimulationPlan,
    ) -> ReviewResult:
        required = {"hasProblem", "diagnosis", "evidence", "proposals"}
        if not isinstance(response, dict) or set(response) != required:
            raise StructuredOutputError("Reviewer output requires exactly the ReviewResult fields")
        if not isinstance(response["hasProblem"], bool):
            raise StructuredOutputError("hasProblem must be boolean")
        if not isinstance(response["diagnosis"], str):
            raise StructuredOutputError("diagnosis must be a string")
        evidence = response["evidence"]
        proposals = response["proposals"]
        if not isinstance(evidence, list) or any(not isinstance(item, str) for item in evidence):
            raise StructuredOutputError("evidence must be a list of strings")
        if not isinstance(proposals, list) or any(not isinstance(item, dict) for item in proposals):
            raise StructuredOutputError("proposals must be a list of objects")
        try:
            result = ReviewResult.from_dict(response)
            if result.has_problem and not result.proposals:
                raise ValueError("A problem review requires at least one RepairProposal")
            if not result.has_problem and result.proposals:
                raise ValueError("A no-problem review must not contain RepairProposal entries")
            for proposal in result.proposals:
                self._validate_changes(proposal.changes)
                plan.apply_repair(proposal)
            return result
        except (TypeError, ValueError) as exc:
            raise StructuredOutputError(f"Reviewer structured output failed validation: {exc}") from exc

    @staticmethod
    def _validate_changes(changes: dict[str, Any]) -> None:
        operation = str(changes.get("operation", ""))
        field_contract = _CHANGE_FIELDS.get(operation)
        if field_contract is None:
            raise ValueError(f"Unsupported repair operation: {operation}")
        allowed, required = field_contract
        if not required.issubset(changes) or not set(changes).issubset(allowed):
            raise ValueError(f"Invalid fields for repair operation {operation}")
        if operation == "update_material" and set(changes) == {"operation"}:
            raise ValueError("update_material requires at least one material field")
        target = changes.get("target")
        if target is not None:
            if not isinstance(target, dict) or len(target) != 1:
                raise ValueError("Repair target requires exactly one selector or coordinate")
            if set(target) not in ({"selector"}, {"coordinate"}):
                raise ValueError("Repair target requires selector or coordinate")
        if ReviewerAgent._contains_internal_id(changes):
            raise ValueError("RepairProposal must not contain internal entity IDs")

    @staticmethod
    def _contains_internal_id(value: Any) -> bool:
        if isinstance(value, dict):
            for key, item in value.items():
                normalized = str(key).replace("_", "").lower()
                if normalized in {
                    "id",
                    "pointid",
                    "edgeid",
                    "faceid",
                    "partid",
                    "materialid",
                    "sectionid",
                    "stepid",
                }:
                    return True
                if ReviewerAgent._contains_internal_id(item):
                    return True
        elif isinstance(value, (list, tuple)):
            return any(ReviewerAgent._contains_internal_id(item) for item in value)
        return False

    @staticmethod
    def _project_snapshot(project: EngineeringProject) -> dict[str, Any]:
        materials = [
            {
                "id": row.id,
                "name": row.name,
                "E": row.young_modulus,
                "nu": row.poisson_ratio,
                "unitWeight": row.unit_weight,
            }
            for row in project.materials
        ]
        sections = [
            {
                "id": row.id,
                "materialId": row.material_id,
                "thickness": row.thickness,
                "planeMode": row.plane_mode,
            }
            for row in project.sections
        ]
        parts: list[dict[str, Any]] = []
        for part in project.parts:
            geometry = part.geometry
            parts.append(
                {
                    "id": part.id,
                    "name": part.name,
                    "geometryType": ReviewerAgent._geometry_type(part.name, geometry),
                    "sectionId": part.section_id,
                    "points": [
                        {"id": point.id, "x": point.x, "y": point.y}
                        for point in geometry.points
                    ],
                    "edges": [
                        {
                            "id": edge.id,
                            "startPointId": edge.start_point_id,
                            "endPointId": edge.end_point_id,
                        }
                        for edge in geometry.edges
                    ],
                    "faceCount": len(geometry.faces),
                }
            )
        return {
            "projectName": project.name,
            "parts": parts,
            "materials": materials,
            "sections": sections,
            "boundaryConditions": [
                {
                    "id": row.id,
                    "targetType": row.target_type,
                    "targetId": row.target_id,
                    "ux": row.ux_value if row.ux_fixed else None,
                    "uy": row.uy_value if row.uy_fixed else None,
                }
                for row in project.boundary_conditions
            ],
            "loads": [
                {
                    "id": row.id,
                    "targetType": row.target_type,
                    "targetId": row.target_id,
                    "loadType": row.load_type,
                    "vector": [row.qx, row.qy],
                }
                for row in project.loads
            ],
        }

    @staticmethod
    def _execution_snapshot(execution_result: ExecutionResult) -> dict[str, Any]:
        snapshot = execution_result.to_dict()
        diagnostic = execution_result.solve_result
        if isinstance(diagnostic, dict):
            snapshot["diagnostics"] = deepcopy(diagnostic)
        elif diagnostic is not None:
            mesh = getattr(diagnostic, "mesh", None)
            if mesh is not None:
                snapshot["mesh"] = {
                    "exists": True,
                    "nodeCount": len(mesh.nodes),
                    "elementCount": len(mesh.elements),
                }
        return snapshot

    @staticmethod
    def _geometry_type(name: str, geometry: Any) -> str:
        normalized_name = str(name).casefold()
        if "circle" in normalized_name and len(geometry.edges) == 64:
            return "circle"
        if len(geometry.points) == 4 and len(geometry.edges) == 4:
            return "rectangle"
        return "polygon"

    def buildReviewContext(
        self,
        plan: SimulationPlan,
        project: EngineeringProject,
        execution_result: ExecutionResult,
    ) -> dict[str, Any]:
        return self.build_review_context(plan, project, execution_result)

    def parseReviewResult(
        self,
        response: dict[str, Any],
        plan: SimulationPlan,
    ) -> ReviewResult:
        return self.parse_review_result(response, plan)
