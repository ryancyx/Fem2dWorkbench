from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

from core.fem.fem_model import FEMModel, Element, Material
from core.solver.assembler import (
    build_material_id_to_material_map,
    build_node_id_to_index_map,
    build_node_id_to_node_map,
    element_dof_indices,
    get_element_coords,
)
from core.solver.cst_element import constitutive_matrix, strain_displacement_matrix

FloatArray = NDArray[np.float64]


@dataclass(slots=True)
class ElementResult:
    """
    单个单元的后处理结果。
    """
    element_id: int
    displacement_vector: FloatArray
    strain: FloatArray
    stress: FloatArray


def extract_element_displacement_vector(
    global_displacement: FloatArray,
    element: Element,
    node_id_to_index: dict[int, int],
) -> FloatArray:
    """
    从整体位移向量中提取某个单元的局部位移向量 u_e。

    返回顺序固定为:
    [u_i, v_i, u_j, v_j, u_k, v_k]
    """
    u = np.asarray(global_displacement, dtype=np.float64).reshape(-1)
    dofs = element_dof_indices(element, node_id_to_index)
    return u[dofs].copy()


def compute_element_result(
    element: Element,
    material: Material,
    global_displacement: FloatArray,
    node_id_to_index: dict[int, int],
    node_id_to_node: dict[int, object],
) -> ElementResult:
    """
    计算单个单元的局部位移、应变、应力。
    """
    element_type = str(element.element_type).strip().upper()
    if element_type != "CST":
        raise NotImplementedError(
            f"当前只支持 CST 三节点三角形单元，元素 {element.id} 的类型是 {element.element_type!r}。"
        )

    coords = get_element_coords(element, node_id_to_node)
    u_e = extract_element_displacement_vector(global_displacement, element, node_id_to_index)

    B = strain_displacement_matrix(coords)
    D = constitutive_matrix(
        E=float(material.young_modulus),
        nu=float(material.poisson_ratio),
        plane_mode=str(material.plane_mode),
    )

    strain = B @ u_e
    stress = D @ strain

    return ElementResult(
        element_id=int(element.id),
        displacement_vector=u_e,
        strain=strain,
        stress=stress,
    )


def compute_all_element_results(model: FEMModel, global_displacement: FloatArray) -> list[ElementResult]:
    """
    计算模型中所有单元的后处理结果。
    """
    node_id_to_index = build_node_id_to_index_map(model)
    node_id_to_node = build_node_id_to_node_map(model)
    material_id_to_material = build_material_id_to_material_map(model)

    results: list[ElementResult] = []

    for element in model.elements:
        material = material_id_to_material.get(element.material_id)
        if material is None:
            raise ValueError(f"元素 {element.id} 引用了不存在的材料 ID: {element.material_id}")

        result = compute_element_result(
            element=element,
            material=material,
            global_displacement=global_displacement,
            node_id_to_index=node_id_to_index,
            node_id_to_node=node_id_to_node,
        )
        results.append(result)

    return results


def extract_node_displacements(
    model: FEMModel,
    global_displacement: FloatArray,
) -> dict[int, tuple[float, float]]:
    """
    将整体位移向量转换为:
    {node_id: (ux, uy)}
    """
    u = np.asarray(global_displacement, dtype=np.float64).reshape(-1)
    node_id_to_index = build_node_id_to_index_map(model)

    node_displacements: dict[int, tuple[float, float]] = {}

    for node in model.nodes:
        index = node_id_to_index[node.id]
        ux = float(u[2 * index])
        uy = float(u[2 * index + 1])
        node_displacements[node.id] = (ux, uy)

    return node_displacements