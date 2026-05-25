from __future__ import annotations

from core.compiler.bc_mapper import map_boundary_condition_to_constraints
from core.compiler.compiled_bundle import CompiledFemBundle
from core.compiler.load_mapper import map_edge_uniform_load_to_nodal_loads
from core.compiler.section_mapper import map_section_to_solver_material
from core.engineering.engineering_project import EngineeringProject
from core.engineering.mesh_model import MeshModel
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
    if part.section_id is None:
        raise ValueError(f"Part {part.id!r} must reference a SectionDefinition")

    section = project.get_section_by_id(part.section_id)
    if section is None:
        raise ValueError(f"Part {part.id!r} references unknown section {part.section_id!r}")

    solver_material, section_mapping = map_section_to_solver_material(
        section=section,
        materials=project.materials,
        solver_material_id=1,
    )
    solver_material_id = section_mapping[section.id]

    mesh_node_to_fem_node_id = {node.id: node.id for node in mesh.nodes}
    mesh_element_to_fem_element_id = {element.id: element.id for element in mesh.elements}

    fem_model = FEMModel()
    for mesh_node in mesh.nodes:
        fem_model.add_node(
            Node(
                id=mesh_node_to_fem_node_id[mesh_node.id],
                x=mesh_node.x,
                y=mesh_node.y,
            )
        )

    fem_model.add_material(solver_material)

    for mesh_element in mesh.elements:
        fem_model.add_element(
            Element(
                id=mesh_element_to_fem_element_id[mesh_element.id],
                node_ids=[
                    mesh_node_to_fem_node_id[node_id] for node_id in mesh_element.node_ids
                ],
                material_id=solver_material_id,
                element_type=mesh_element.element_type,
            )
        )

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
        loads, next_load_id = map_edge_uniform_load_to_nodal_loads(
            load=load,
            mesh=mesh,
            mesh_node_to_fem_node_id=mesh_node_to_fem_node_id,
            thickness=section.thickness,
            start_load_id=next_load_id,
        )
        for fem_load in loads:
            fem_model.add_load(fem_load)

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
