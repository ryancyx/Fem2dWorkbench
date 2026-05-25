from __future__ import annotations

import numpy as np
from numpy.typing import NDArray

FloatArray = NDArray[np.float64]


def solve_linear_system(K: FloatArray, F: FloatArray) -> FloatArray:
    """
    求解线性方程组 K u = F。

    Parameters
    ----------
    K : ndarray
        系数矩阵，必须为方阵
    F : ndarray
        右端向量，长度必须与 K 的维度一致

    Returns
    -------
    u : ndarray
        方程组解向量
    """
    K_arr = np.asarray(K, dtype=np.float64)
    F_arr = np.asarray(F, dtype=np.float64).reshape(-1)

    if K_arr.ndim != 2 or K_arr.shape[0] != K_arr.shape[1]:
        raise ValueError("K 必须是方阵。")

    if F_arr.shape[0] != K_arr.shape[0]:
        raise ValueError("F 的长度必须与 K 的维度一致。")

    try:
        u = np.linalg.solve(K_arr, F_arr)
    except np.linalg.LinAlgError as exc:
        raise ValueError(
            "线性方程组求解失败。整体刚度矩阵可能仍然奇异，请检查约束是否足够。"
        ) from exc

    return u