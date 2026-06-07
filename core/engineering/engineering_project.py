from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, TypeVar

from core.engineering.analysis_step import AnalysisStep
from core.engineering.assembly import Assembly
from core.engineering.boundary_condition_definition import BoundaryConditionDefinition
from core.engineering.load_definition import LoadDefinition
from core.engineering.material_definition import MaterialDefinition
from core.engineering.part import Part
from core.engineering.section import SectionDefinition

T = TypeVar("T")


@dataclass(slots=True)
class EngineeringProject:
    name: str
    materials: list[MaterialDefinition] = field(default_factory=list)
    sections: list[SectionDefinition] = field(default_factory=list)
    parts: list[Part] = field(default_factory=list)
    assembly: Assembly = field(default_factory=Assembly)
    analysis_steps: list[AnalysisStep] = field(default_factory=list)
    loads: list[LoadDefinition] = field(default_factory=list)
    boundary_conditions: list[BoundaryConditionDefinition] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("EngineeringProject.name must not be empty")
        self._validate_unique_ids("materials", self.materials)
        self._validate_unique_ids("sections", self.sections)
        self._validate_unique_ids("parts", self.parts)
        self._validate_unique_ids("analysis_steps", self.analysis_steps)
        self._validate_unique_ids("loads", self.loads)
        self._validate_unique_ids("boundary_conditions", self.boundary_conditions)

    @staticmethod
    def _validate_unique_ids(label: str, items: list[Any]) -> None:
        ids = [item.id for item in items]
        if len(ids) != len(set(ids)):
            raise ValueError(f"EngineeringProject.{label} contains duplicate ids")

    @staticmethod
    def _get_by_id(items: list[T], item_id: str) -> T | None:
        for item in items:
            if getattr(item, "id") == item_id:
                return item
        return None

    def _add_unique(self, label: str, items: list[T], item: T) -> None:
        if self._get_by_id(items, getattr(item, "id")) is not None:
            raise ValueError(f"Duplicate {label} id: {getattr(item, 'id')!r}")
        items.append(item)

    def add_material(self, material: MaterialDefinition) -> None:
        self._add_unique("material", self.materials, material)

    def add_section(self, section: SectionDefinition) -> None:
        self._add_unique("section", self.sections, section)

    def add_part(self, part: Part) -> None:
        self._add_unique("part", self.parts, part)

    def add_analysis_step(self, analysis_step: AnalysisStep) -> None:
        self._add_unique("analysis_step", self.analysis_steps, analysis_step)

    def add_load(self, load: LoadDefinition) -> None:
        self._add_unique("load", self.loads, load)

    def add_boundary_condition(self, boundary_condition: BoundaryConditionDefinition) -> None:
        self._add_unique("boundary_condition", self.boundary_conditions, boundary_condition)

    def get_material_by_id(self, material_id: str) -> MaterialDefinition | None:
        return self._get_by_id(self.materials, material_id)

    def get_section_by_id(self, section_id: str) -> SectionDefinition | None:
        return self._get_by_id(self.sections, section_id)

    def get_part_by_id(self, part_id: str) -> Part | None:
        return self._get_by_id(self.parts, part_id)

    def get_analysis_step_by_id(self, step_id: str) -> AnalysisStep | None:
        return self._get_by_id(self.analysis_steps, step_id)

    def get_load_by_id(self, load_id: str) -> LoadDefinition | None:
        return self._get_by_id(self.loads, load_id)

    def get_boundary_condition_by_id(
        self,
        boundary_condition_id: str,
    ) -> BoundaryConditionDefinition | None:
        return self._get_by_id(self.boundary_conditions, boundary_condition_id)

    def validate_references(self) -> None:
        material_ids = {material.id for material in self.materials}
        section_ids = {section.id for section in self.sections}
        part_ids = {part.id for part in self.parts}
        step_ids = {step.id for step in self.analysis_steps}
        geometry_edge_ids = {edge.id for part in self.parts for edge in part.geometry.edges}
        geometry_point_ids = {point.id for part in self.parts for point in part.geometry.points}

        for section in self.sections:
            if section.material_id not in material_ids:
                raise ValueError(f"Section {section.id!r} references unknown material {section.material_id!r}")
        for part in self.parts:
            if part.section_id is not None and part.section_id not in section_ids:
                raise ValueError(f"Part {part.id!r} references unknown section {part.section_id!r}")
            for face in part.geometry.faces:
                if face.section_id and face.section_id not in section_ids:
                    raise ValueError(
                        f"GeometryFace {face.id!r} in Part {part.id!r} references unknown section {face.section_id!r}"
                    )
        for instance in self.assembly.instances:
            if instance.part_id not in part_ids:
                raise ValueError(f"PartInstance {instance.id!r} references unknown part {instance.part_id!r}")
        for load in self.loads:
            if load.step_id not in step_ids:
                raise ValueError(f"Load {load.id!r} references unknown analysis step {load.step_id!r}")
            if load.target_type in {"geometry_edge", "geometry_edge_segment"}:
                if load.target_id not in geometry_edge_ids:
                    raise ValueError(
                        f"Load {load.id!r} references unknown geometry edge {load.target_id!r}"
                    )
            elif load.target_type == "geometry_point":
                if load.target_id not in geometry_point_ids:
                    raise ValueError(
                        f"Load {load.id!r} references unknown geometry point {load.target_id!r}"
                    )
        for boundary_condition in self.boundary_conditions:
            if boundary_condition.step_id not in step_ids:
                raise ValueError(
                    f"BoundaryCondition {boundary_condition.id!r} references unknown analysis step "
                    f"{boundary_condition.step_id!r}"
                )
            if boundary_condition.target_type == "geometry_edge":
                if boundary_condition.target_id not in geometry_edge_ids:
                    raise ValueError(
                        f"BoundaryCondition {boundary_condition.id!r} references unknown geometry edge "
                        f"{boundary_condition.target_id!r}"
                    )
            elif boundary_condition.target_type == "geometry_point":
                if boundary_condition.target_id not in geometry_point_ids:
                    raise ValueError(
                        f"BoundaryCondition {boundary_condition.id!r} references unknown geometry point "
                        f"{boundary_condition.target_id!r}"
                    )

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "materials": [material.to_dict() for material in self.materials],
            "sections": [section.to_dict() for section in self.sections],
            "parts": [part.to_dict() for part in self.parts],
            "assembly": self.assembly.to_dict(),
            "analysis_steps": [step.to_dict() for step in self.analysis_steps],
            "loads": [load.to_dict() for load in self.loads],
            "boundary_conditions": [
                boundary_condition.to_dict() for boundary_condition in self.boundary_conditions
            ],
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "EngineeringProject":
        project = cls(
            name=str(data["name"]),
            materials=[MaterialDefinition.from_dict(item) for item in data.get("materials", [])],
            sections=[SectionDefinition.from_dict(item) for item in data.get("sections", [])],
            parts=[Part.from_dict(item) for item in data.get("parts", [])],
            assembly=Assembly.from_dict(data.get("assembly", {})),
            analysis_steps=[AnalysisStep.from_dict(item) for item in data.get("analysis_steps", [])],
            loads=[LoadDefinition.from_dict(item) for item in data.get("loads", [])],
            boundary_conditions=[
                BoundaryConditionDefinition.from_dict(item)
                for item in data.get("boundary_conditions", [])
            ],
            metadata=dict(data.get("metadata", {})),
        )
        project.validate_references()
        return project
