from __future__ import annotations

from dataclasses import dataclass, field

from core.fem.fem_model import FEMModel


@dataclass(slots=True)
class CompiledFemBundle:
    fem_model: FEMModel
    step_id: str
    mesh_node_to_fem_node_id: dict[int, int]
    mesh_element_to_fem_element_id: dict[int, int]
    section_to_solver_material_id: dict[str, int]
    geometry_edge_to_fem_node_ids: dict[str, list[int]]
    geometry_edge_to_fem_element_edges: dict[str, list[tuple[int, int, int]]]
    warnings: list[str] = field(default_factory=list)
