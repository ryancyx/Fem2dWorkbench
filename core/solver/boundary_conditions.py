from __future__ import annotations

import numpy as np
from numpy.typing import NDArray

from core.fem.fem_model import FEMModel

FloatArray = NDArray[np.float64]


def _apply_single_dof_constraint_inplace(
    K: FloatArray,
    F: FloatArray,
    dof_index: int,
    prescribed_value: float,
) -> None:
    """
    对单个自由度施加位移约束（原地修改 K 和 F）。

    使用“对角元素改 1 法”：
    1. 先修正载荷向量
    2. 再将该自由度对应的行列清零
    3. 对角元置 1
    4. 右端项置为指定位移值
    """
    F[:] = F - K[:, dof_index] * prescribed_value
    K[:, dof_index] = 0.0
    K[dof_index, :] = 0.0
    K[dof_index, dof_index] = 1.0
    F[dof_index] = prescribed_value


def apply_displacement_constraints(
    K: FloatArray,
    F: FloatArray,
    model: FEMModel,
    node_id_to_index: dict[int, int],
) -> tuple[FloatArray, FloatArray]:
    """
    对整体方程 K u = F 施加位移边界条件。

    Parameters
    ----------
    K : ndarray
        原整体刚度矩阵
    F : ndarray
        原整体载荷向量
    model : FEMModel
        FEM 模型，内部包含 constraints
    node_id_to_index : dict[int, int]
        节点 ID 到节点顺序索引的映射

    Returns
    -------
    (K_bc, F_bc) : tuple[ndarray, ndarray]
        施加边界条件后的刚度矩阵和载荷向量
    """
    K_mod = np.asarray(K, dtype=np.float64).copy()
    F_mod = np.asarray(F, dtype=np.float64).reshape(-1).copy()

    if K_mod.ndim != 2 or K_mod.shape[0] != K_mod.shape[1]:
        raise ValueError("K 必须是方阵。")

    if F_mod.shape[0] != K_mod.shape[0]:
        raise ValueError("F 的长度必须与 K 的维度一致。")

    applied_dofs: dict[int, float] = {}

    for constraint in model.constraints:
        node_index = node_id_to_index.get(constraint.node_id)
        if node_index is None:
            raise ValueError(f"约束 {constraint.id} 引用了不存在的节点 ID: {constraint.node_id}")

        # x 方向位移约束
        if bool(getattr(constraint, "ux_fixed", False)):
            dof_index = 2 * node_index
            prescribed_value = float(getattr(constraint, "ux_value", 0.0))

            old_value = applied_dofs.get(dof_index)
            if old_value is not None:
                if not np.isclose(old_value, prescribed_value):
                    raise ValueError(
                        f"自由度 {dof_index} 被重复施加了相互冲突的位移约束："
                        f"{old_value} 和 {prescribed_value}"
                    )
            else:
                _apply_single_dof_constraint_inplace(K_mod, F_mod, dof_index, prescribed_value)
                applied_dofs[dof_index] = prescribed_value

        # y 方向位移约束
        if bool(getattr(constraint, "uy_fixed", False)):
            dof_index = 2 * node_index + 1
            prescribed_value = float(getattr(constraint, "uy_value", 0.0))

            old_value = applied_dofs.get(dof_index)
            if old_value is not None:
                if not np.isclose(old_value, prescribed_value):
                    raise ValueError(
                        f"自由度 {dof_index} 被重复施加了相互冲突的位移约束："
                        f"{old_value} 和 {prescribed_value}"
                    )
            else:
                _apply_single_dof_constraint_inplace(K_mod, F_mod, dof_index, prescribed_value)
                applied_dofs[dof_index] = prescribed_value

    return K_mod, F_mod
