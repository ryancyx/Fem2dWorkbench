from __future__ import annotations

from dataclasses import dataclass

from numpy.typing import NDArray
import numpy as np

from core.fem.fem_model import FEMModel
from core.solver.assembler import (
    assemble_global_load_vector,
    assemble_global_stiffness,
    build_node_id_to_index_map,
)
from core.solver.boundary_conditions import apply_displacement_constraints
from core.solver.linear_solver import solve_linear_system
from core.solver.postprocess import (
    ElementResult,
    compute_all_element_results,
    extract_node_displacements,
)

FloatArray = NDArray[np.float64]


@dataclass(slots=True)
class SolverResult:
    """
    求解器总结果。
    """
    global_stiffness: FloatArray
    global_load: FloatArray
    constrained_stiffness: FloatArray
    constrained_load: FloatArray
    displacement: FloatArray
    node_displacements: dict[int, tuple[float, float]]
    element_results: list[ElementResult]


def solve_linear_static(model: FEMModel) -> SolverResult:
    """
    线弹性、小变形、二维静力问题求解主流程。

    当前支持：
    - 三节点 CST 单元
    - 节点集中载荷
    - 位移边界条件
    """
    if len(model.nodes) == 0:
        raise ValueError("模型没有节点，无法求解。")

    if len(model.elements) == 0:
        raise ValueError("模型没有单元，无法求解。")

    node_id_to_index = build_node_id_to_index_map(model)

    # 1. 整体组装
    K = assemble_global_stiffness(model)
    F = assemble_global_load_vector(model)

    # 2. 施加位移边界条件
    K_bc, F_bc = apply_displacement_constraints(
        K=K,
        F=F,
        model=model,
        node_id_to_index=node_id_to_index,
    )

    # 3. 求解整体位移
    displacement = solve_linear_system(K_bc, F_bc)

    # 4. 后处理
    node_displacements = extract_node_displacements(model, displacement)
    element_results = compute_all_element_results(model, displacement)

    return SolverResult(
        global_stiffness=K,
        global_load=F,
        constrained_stiffness=K_bc,
        constrained_load=F_bc,
        displacement=displacement,
        node_displacements=node_displacements,
        element_results=element_results,
    )