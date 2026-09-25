from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any

from agent.review_models import RepairProposal


_RESULT_TYPES = {"displacement", "stress", "strain", "von_mises"}
_PLANE_MODES = {"stress", "strain"}
_TARGETED_COLLECTIONS = {
    "point_constraint": "point_constraints",
    "edge_constraint": "edge_constraints",
    "point_load": "point_loads",
    "edge_load": "edge_loads",
}


def _positive_number(value: Any, field_name: str) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field_name} must be a number") from exc
    if number <= 0.0:
        raise ValueError(f"{field_name} must be positive")
    return number


def _validate_target(target: Any, field_name: str) -> dict[str, Any]:
    if not isinstance(target, dict) or not target:
        raise ValueError(f"{field_name}.target must be a non-empty dictionary")
    forbidden = {"id", "point_id", "pointId", "edge_id", "edgeId"}.intersection(target)
    if forbidden:
        raise ValueError(f"{field_name}.target must use semantic selectors, not entity ids")
    selector = target.get("selector")
    coordinate = target.get("coordinate")
    if selector is None and coordinate is None:
        raise ValueError(f"{field_name}.target requires selector or coordinate")
    if selector is not None and (not isinstance(selector, str) or not selector.strip()):
        raise ValueError(f"{field_name}.target.selector must be non-empty")
    if coordinate is not None:
        if not isinstance(coordinate, (list, tuple)) or len(coordinate) != 2:
            raise ValueError(f"{field_name}.target.coordinate must contain x and y")
        float(coordinate[0])
        float(coordinate[1])
    return deepcopy(target)


def _validate_constraint(row: Any, field_name: str) -> dict[str, Any]:
    if not isinstance(row, dict):
        raise ValueError(f"{field_name} entries must be dictionaries")
    result = deepcopy(row)
    result["target"] = _validate_target(row.get("target"), field_name)
    ux = row.get("ux")
    uy = row.get("uy")
    if ux is None and uy is None:
        raise ValueError(f"{field_name} must constrain ux or uy")
    result["ux"] = None if ux is None else float(ux)
    result["uy"] = None if uy is None else float(uy)
    return result


def _validate_load(row: Any, field_name: str) -> dict[str, Any]:
    if not isinstance(row, dict):
        raise ValueError(f"{field_name} entries must be dictionaries")
    result = deepcopy(row)
    result["target"] = _validate_target(row.get("target"), field_name)
    vector = row.get("vector")
    if not isinstance(vector, (list, tuple)) or len(vector) != 2:
        raise ValueError(f"{field_name}.vector must contain exactly two components")
    result["vector"] = [float(vector[0]), float(vector[1])]
    return result


@dataclass(slots=True)
class SimulationPlan:
    version: int
    geometry: dict[str, Any]
    material: dict[str, Any]
    point_constraints: list[dict[str, Any]] = field(default_factory=list)
    edge_constraints: list[dict[str, Any]] = field(default_factory=list)
    point_loads: list[dict[str, Any]] = field(default_factory=list)
    edge_loads: list[dict[str, Any]] = field(default_factory=list)
    mesh_size: float = 0.2
    requested_result: str = "von_mises"

    def __post_init__(self) -> None:
        self.version = int(self.version)
        if self.version < 1:
            raise ValueError("SimulationPlan.version must be at least 1")
        self.geometry = self._validate_geometry(self.geometry)
        self.material = self._validate_material(self.material)
        self.point_constraints = [
            _validate_constraint(item, "pointConstraints") for item in self.point_constraints
        ]
        self.edge_constraints = [
            _validate_constraint(item, "edgeConstraints") for item in self.edge_constraints
        ]
        self.point_loads = [_validate_load(item, "pointLoads") for item in self.point_loads]
        self.edge_loads = [_validate_load(item, "edgeLoads") for item in self.edge_loads]
        self.mesh_size = _positive_number(self.mesh_size, "meshSize")
        self.requested_result = str(self.requested_result).strip().lower()
        if self.requested_result not in _RESULT_TYPES:
            raise ValueError(f"requestedResult must be one of {sorted(_RESULT_TYPES)}")

    @staticmethod
    def _validate_geometry(value: Any) -> dict[str, Any]:
        if not isinstance(value, dict):
            raise ValueError("geometry must be a dictionary")
        result = deepcopy(value)
        geometry_type = str(result.get("type", "")).strip().lower()
        if geometry_type == "rectangle":
            result["width"] = _positive_number(result.get("width"), "geometry.width")
            result["height"] = _positive_number(result.get("height"), "geometry.height")
            result["originX"] = float(result.get("originX", result.get("origin_x", 0.0)))
            result["originY"] = float(result.get("originY", result.get("origin_y", 0.0)))
        elif geometry_type == "circle":
            result["centerX"] = float(result.get("centerX", result.get("center_x", 0.0)))
            result["centerY"] = float(result.get("centerY", result.get("center_y", 0.0)))
            result["radius"] = _positive_number(result.get("radius"), "geometry.radius")
        else:
            raise ValueError("geometry.type must be 'rectangle' or 'circle'")
        result["type"] = geometry_type
        return result

    @staticmethod
    def _validate_material(value: Any) -> dict[str, Any]:
        if not isinstance(value, dict):
            raise ValueError("material must be a dictionary")
        result = deepcopy(value)
        name = str(result.get("name", "")).strip()
        if not name:
            raise ValueError("material.name must not be empty")
        result["name"] = name
        result["E"] = _positive_number(result.get("E"), "material.E")
        result["nu"] = float(result.get("nu"))
        if not -1.0 < result["nu"] < 0.5:
            raise ValueError("material.nu must be between -1.0 and 0.5")
        result["thickness"] = _positive_number(result.get("thickness"), "material.thickness")
        plane_mode = str(result.get("plane_mode", result.get("planeMode", ""))).strip().lower()
        if plane_mode not in _PLANE_MODES:
            raise ValueError("material.plane_mode must be 'stress' or 'strain'")
        result["plane_mode"] = plane_mode
        result.pop("planeMode", None)
        if "unit_weight" in result:
            result["unit_weight"] = float(result["unit_weight"])
            if result["unit_weight"] < 0.0:
                raise ValueError("material.unit_weight must be non-negative")
        return result

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "geometry": deepcopy(self.geometry),
            "material": deepcopy(self.material),
            "pointConstraints": deepcopy(self.point_constraints),
            "edgeConstraints": deepcopy(self.edge_constraints),
            "pointLoads": deepcopy(self.point_loads),
            "edgeLoads": deepcopy(self.edge_loads),
            "meshSize": self.mesh_size,
            "requestedResult": self.requested_result,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SimulationPlan":
        if not isinstance(data, dict):
            raise ValueError("SimulationPlan data must be a dictionary")
        return cls(
            version=data.get("version", 1),
            geometry=data.get("geometry", {}),
            material=data.get("material", {}),
            point_constraints=data.get("pointConstraints", data.get("point_constraints", [])),
            edge_constraints=data.get("edgeConstraints", data.get("edge_constraints", [])),
            point_loads=data.get("pointLoads", data.get("point_loads", [])),
            edge_loads=data.get("edgeLoads", data.get("edge_loads", [])),
            mesh_size=data.get("meshSize", data.get("mesh_size", 0.2)),
            requested_result=data.get(
                "requestedResult", data.get("requested_result", "von_mises")
            ),
        )

    def apply_repair(self, proposal: RepairProposal) -> "SimulationPlan":
        data = self.to_dict()
        changes = deepcopy(proposal.changes)
        operation = str(changes.pop("operation")).strip()

        if operation == "set_mesh_size":
            data["meshSize"] = changes.get("meshSize", changes.get("mesh_size"))
        elif operation == "update_material":
            data["material"].update(changes)
        elif operation == "replace_geometry":
            geometry = changes.get("geometry")
            if not isinstance(geometry, dict):
                raise ValueError("replace_geometry requires a geometry dictionary")
            data["geometry"] = geometry
        elif operation.startswith("add_") or operation.startswith("update_"):
            action, _, item_type = operation.partition("_")
            collection_attribute = _TARGETED_COLLECTIONS.get(item_type)
            if collection_attribute is None:
                raise ValueError(f"Unsupported repair operation: {operation}")
            collection_key = {
                "point_constraints": "pointConstraints",
                "edge_constraints": "edgeConstraints",
                "point_loads": "pointLoads",
                "edge_loads": "edgeLoads",
            }[collection_attribute]
            item = dict(changes)
            if action == "add":
                data[collection_key].append(item)
            else:
                target = item.get("target")
                match = next(
                    (row for row in data[collection_key] if row.get("target") == target),
                    None,
                )
                if match is None:
                    raise ValueError(f"No existing target found for {operation}")
                match.update(item)
        else:
            raise ValueError(f"Unsupported repair operation: {operation}")

        data["version"] = self.version + 1
        return SimulationPlan.from_dict(data)

    def applyRepair(self, proposal: RepairProposal) -> "SimulationPlan":
        return self.apply_repair(proposal)
