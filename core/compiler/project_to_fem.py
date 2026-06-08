from __future__ import annotations

from core.compiler.bc_mapper import map_boundary_condition_to_constraints
from core.compiler.compiled_bundle import CompiledFemBundle
from core.compiler.gravity_load_mapper import map_gravity_load_to_nodal_loads
from core.compiler.load_mapper import map_edge_uniform_load_to_nodal_loads
from core.compiler.load_mapper import map_nodal_concentrated_load_to_nodal_loads
from core.compiler.section_mapper import map_section_to_solver_material
from core.engineering.engineering_project import EngineeringProject
from core.engineering.mesh_model import MeshModel
from core.engineering.part import Part
from core.engineering.section import SectionDefinition
from core.fem.element import Element
from core.fem.fem_model import FEMModel
from core.fem.node import Node


def compile_project_to_fem(
    project: EngineeringProject,
    mesh: MeshModel,
    step_id: str,
) -> CompiledFemBundle:
    project.validate_references()
    mesh.validate()

    step = project.get_analysis_step_by_id(step_id)
    if step is None:
        raise ValueError(f"Analysis step {step_id!r} does not exist")
    if step.step_type != "static_linear":
        raise ValueError("Only static_linear analysis steps are supported")
    if not project.parts:
        raise ValueError("EngineeringProject must contain at least one Part")

    warnings: list[str] = []
    if len(project.parts) > 1:
        warnings.append("Only the first Part is compiled in the current compiler stage")
    part = project.parts[0]
    section_mapping: dict[str, int] = {}
    section_by_id: dict[str, SectionDefinition] = {}

    mesh_node_to_fem_node_id = {node.id: node.id for node in mesh.nodes}
    mesh_element_to_fem_element_id = {element.id: element.id for element in mesh.elements}
    element_unit_weights: dict[int, float] = {}
    element_thicknesses: dict[int, float] = {}

    fem_model = FEMModel()
    for mesh_node in mesh.nodes:
        fem_model.add_node(
            Node(
                id=mesh_node_to_fem_node_id[mesh_node.id],
                x=mesh_node.x,
                y=mesh_node.y,
            )
        )

    for mesh_element in mesh.elements:
        section = _section_for_mesh_element(project, part, mesh_element.source_face_id)
        material = project.get_material_by_id(section.material_id)
        if material is None:
            raise ValueError(f"Section {section.id!r} references unknown material {section.material_id!r}")
        if section.id not in section_mapping:
            solver_material, new_mapping = map_section_to_solver_material(
                section=section,
                materials=project.materials,
                solver_material_id=len(section_mapping) + 1,
            )
            fem_model.add_material(solver_material)
            section_mapping.update(new_mapping)
            section_by_id[section.id] = section
        fem_model.add_element(
            Element(
                id=mesh_element_to_fem_element_id[mesh_element.id],
                node_ids=[
                    mesh_node_to_fem_node_id[node_id] for node_id in mesh_element.node_ids
                ],
                material_id=section_mapping[section.id],
                element_type=mesh_element.element_type,
            )
        )
        element_unit_weights[mesh_element.id] = float(material.unit_weight)
        element_thicknesses[mesh_element.id] = float(section.thickness)

    next_constraint_id = 1
    for boundary_condition in project.boundary_conditions:
        if boundary_condition.step_id != step_id:
            continue
        constraints, next_constraint_id = map_boundary_condition_to_constraints(
            boundary_condition=boundary_condition,
            mesh=mesh,
            mesh_node_to_fem_node_id=mesh_node_to_fem_node_id,
            start_constraint_id=next_constraint_id,
        )
        for constraint in constraints:
            fem_model.add_constraint(constraint)

    next_load_id = 1
    for load in project.loads:
        if load.step_id != step_id:
            continue
        if load.load_type == "edge_uniform":
            thickness = _thickness_for_edge_load(
                project=project,
                part=part,
                mesh=mesh,
                edge_id=load.target_id,
                section_by_id=section_by_id,
            )
            loads, next_load_id = map_edge_uniform_load_to_nodal_loads(
                load=load,
                mesh=mesh,
                mesh_node_to_fem_node_id=mesh_node_to_fem_node_id,
                thickness=thickness,
                start_load_id=next_load_id,
            )
        elif load.load_type == "nodal_concentrated":
            loads, next_load_id = map_nodal_concentrated_load_to_nodal_loads(
                load=load,
                mesh=mesh,
                mesh_node_to_fem_node_id=mesh_node_to_fem_node_id,
                start_load_id=next_load_id,
            )
        else:
            raise ValueError(f"Unsupported load_type {load.load_type!r}")
        for fem_load in loads:
            fem_model.add_load(fem_load)

    if _gravity_enabled(project):
        gravity_loads, next_load_id, gravity_stats = map_gravity_load_to_nodal_loads(
            mesh=mesh,
            mesh_node_to_fem_node_id=mesh_node_to_fem_node_id,
            element_unit_weights=element_unit_weights,
            element_thicknesses=element_thicknesses,
            start_load_id=next_load_id,
            direction_x=_gravity_direction(project)[0],
            direction_y=_gravity_direction(project)[1],
        )
        for fem_load in gravity_loads:
            fem_model.add_load(fem_load)
        if gravity_stats["active_element_count"] <= 0.0:
            warnings.append("已启用自重，但所有材料容重为 0。")
        else:
            warnings.append(
                "已启用自重："
                f"Fx={gravity_stats['total_fx']:.6g}, Fy={gravity_stats['total_fy']:.6g}"
            )

    geometry_edge_to_fem_node_ids = {
        edge_id: [mesh_node_to_fem_node_id[node_id] for node_id in node_ids]
        for edge_id, node_ids in mesh.geometry_edge_to_mesh_node_ids.items()
    }
    geometry_edge_to_fem_element_edges = {
        edge_id: [
            (mesh_element_to_fem_element_id[element_id], local_a, local_b)
            for element_id, local_a, local_b in element_edges
        ]
        for edge_id, element_edges in mesh.geometry_edge_to_mesh_element_edges.items()
    }

    return CompiledFemBundle(
        fem_model=fem_model,
        step_id=step_id,
        mesh_node_to_fem_node_id=mesh_node_to_fem_node_id,
        mesh_element_to_fem_element_id=mesh_element_to_fem_element_id,
        section_to_solver_material_id=section_mapping,
        geometry_edge_to_fem_node_ids=geometry_edge_to_fem_node_ids,
        geometry_edge_to_fem_element_edges=geometry_edge_to_fem_element_edges,
        warnings=warnings,
    )


def _gravity_enabled(project: EngineeringProject) -> bool:
    return bool(project.metadata.get("gravity_enabled", False))


def _gravity_direction(project: EngineeringProject) -> tuple[float, float]:
    return (
        float(project.metadata.get("gravity_direction_x", 0.0) or 0.0),
        float(project.metadata.get("gravity_direction_y", -1.0) or -1.0),
    )


def _section_for_mesh_element(
    project: EngineeringProject,
    part: Part,
    face_id: str | None,
) -> SectionDefinition:
    section_id = ""
    if face_id:
        for face in part.geometry.faces:
            if face.id == face_id:
                section_id = face.section_id
                break
    if not section_id:
        section_id = part.section_id or ""
    if not section_id:
        raise ValueError(f"闭合面 {face_id or '<unknown>'} 未分配材料")
    section = project.get_section_by_id(section_id)
    if section is None:
        raise ValueError(f"闭合面 {face_id or '<unknown>'} 引用了未知截面 {section_id!r}")
    return section


def _thickness_for_edge_load(
    project: EngineeringProject,
    part: Part,
    mesh: MeshModel,
    edge_id: str,
    section_by_id: dict[str, SectionDefinition],
) -> float:
    element_edges = mesh.geometry_edge_to_mesh_element_edges.get(edge_id, [])
    thicknesses: list[float] = []
    for element_id, _, _ in element_edges:
        mesh_element = mesh.get_element_by_id(element_id)
        if mesh_element is None:
            continue
        section = _section_for_mesh_element(project, part, mesh_element.source_face_id)
        section_by_id.setdefault(section.id, section)
        thicknesses.append(section.thickness)
    if not thicknesses:
        section = _section_for_mesh_element(project, part, None)
        return section.thickness
    return sum(thicknesses) / len(thicknesses)
