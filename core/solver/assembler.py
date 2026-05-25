from __future__ import annotations

import numpy as np
from numpy.typing import NDArray

from core.fem.fem_model import FEMModel, Element, Material, Node
from core.solver.cst_element import element_stiffness

FloatArray = NDArray[np.float64]


def build_node_id_to_index_map(model: FEMModel) -> dict[int, int]:
    """
    建立 节点ID -> 节点在 model.nodes 中顺序索引 的映射。
    例如:
    node_id=10 可能映射到 index=0
    """
    mapping: dict[int, int] = {}

    for index, node in enumerate(model.nodes):
        if node.id in mapping:
            raise ValueError(f"发现重复节点 ID: {node.id}")
        mapping[node.id] = index

    return mapping


def build_node_id_to_node_map(model: FEMModel) -> dict[int, Node]:
    """建立 节点ID -> 节点对象 的映射。"""
    mapping: dict[int, Node] = {}

    for node in model.nodes:
        if node.id in mapping:
            raise ValueError(f"发现重复节点 ID: {node.id}")
        mapping[node.id] = node

    return mapping


def build_material_id_to_material_map(model: FEMModel) -> dict[int, Material]:
    """建立 材料ID -> 材料对象 的映射。"""
    mapping: dict[int, Material] = {}

    for material in model.materials:
        if material.id in mapping:
            raise ValueError(f"发现重复材料 ID: {material.id}")
        mapping[material.id] = material

    return mapping


def get_element_coords(element: Element, node_id_to_node: dict[int, Node]) -> FloatArray:
    """
    根据单元的 node_ids 取出对应的三节点坐标，返回 shape=(3,2) 数组。
    """
    if len(element.node_ids) != 3:
        raise ValueError(
            f"当前仅支持三节点三角形单元，元素 {element.id} 的 node_ids 长度不是 3。"
        )

    coords: list[list[float]] = []

    for node_id in element.node_ids:
        node = node_id_to_node.get(node_id)
        if node is None:
            raise ValueError(f"元素 {element.id} 引用了不存在的节点 ID: {node_id}")
        coords.append([float(node.x), float(node.y)])

    return np.asarray(coords, dtype=np.float64)


def element_dof_indices(element: Element, node_id_to_index: dict[int, int]) -> list[int]:
    """
    返回单元局部自由度对应的整体自由度编号。
    三节点单元的结果长度固定为 6:
    [u_i, v_i, u_j, v_j, u_k, v_k]
    """
    if len(element.node_ids) != 3:
        raise ValueError(
            f"当前仅支持三节点三角形单元，元素 {element.id} 的 node_ids 长度不是 3。"
        )

    dof_indices: list[int] = []

    for node_id in element.node_ids:
        node_index = node_id_to_index.get(node_id)
        if node_index is None:
            raise ValueError(f"元素 {element.id} 引用了不存在的节点 ID: {node_id}")

        base = 2 * node_index
        dof_indices.extend([base, base + 1])

    return dof_indices


def assemble_global_stiffness(model: FEMModel) -> FloatArray:
    """
    组装整体刚度矩阵 K。
    """
    node_id_to_index = build_node_id_to_index_map(model)
    node_id_to_node = build_node_id_to_node_map(model)
    material_id_to_material = build_material_id_to_material_map(model)

    total_dofs = 2 * len(model.nodes)
    K = np.zeros((total_dofs, total_dofs), dtype=np.float64)

    for element in model.elements:
        element_type = str(element.element_type).strip().upper()
        if element_type != "CST":
            raise NotImplementedError(
                f"当前只支持 CST 三节点三角形单元，元素 {element.id} 的类型是 {element.element_type!r}。"
            )

        material = material_id_to_material.get(element.material_id)
        if material is None:
            raise ValueError(f"元素 {element.id} 引用了不存在的材料 ID: {element.material_id}")

        coords = get_element_coords(element, node_id_to_node)
        dofs = element_dof_indices(element, node_id_to_index)

        Ke = element_stiffness(
            coords=coords,
            E=float(material.young_modulus),
            nu=float(material.poisson_ratio),
            thickness=float(material.thickness),
            plane_mode=str(material.plane_mode),
        )

        for local_row, global_row in enumerate(dofs):
            for local_col, global_col in enumerate(dofs):
                K[global_row, global_col] += Ke[local_row, local_col]

    return K


def assemble_global_load_vector(model: FEMModel) -> FloatArray:
    """
    组装整体载荷向量 F。
    当前先只支持节点集中载荷（nodal）。
    """
    node_id_to_index = build_node_id_to_index_map(model)
    total_dofs = 2 * len(model.nodes)

    F = np.zeros(total_dofs, dtype=np.float64)

    for load in model.loads:
        load_type = str(getattr(load, "load_type", "nodal")).strip().lower()
        if load_type != "nodal":
            raise NotImplementedError(
                f"当前只支持节点集中载荷 nodal，载荷 {load.id} 的类型是 {load.load_type!r}。"
            )

        node_index = node_id_to_index.get(load.node_id)
        if node_index is None:
            raise ValueError(f"载荷 {load.id} 引用了不存在的节点 ID: {load.node_id}")

        base = 2 * node_index
        F[base] += float(getattr(load, "fx", 0.0))
        F[base + 1] += float(getattr(load, "fy", 0.0))

    return F
