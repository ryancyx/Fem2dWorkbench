from __future__ import annotations

import numpy as np
from numpy.typing import NDArray

FloatArray = NDArray[np.float64]


def _as_coord_array(coords: list[list[float]] | list[tuple[float, float]] | FloatArray) -> FloatArray:
    """将输入统一转换为 shape=(3, 2) 的 float64 数组。"""
    arr = np.asarray(coords, dtype=np.float64)

    if arr.shape != (3, 2):
        raise ValueError(
            "coords 必须是 3 个二维节点坐标，形状应为 (3, 2)，例如 [[x1, y1], [x2, y2], [x3, y3]]。"
        )

    return arr


def triangle_area(coords: list[list[float]] | list[tuple[float, float]] | FloatArray) -> float:
    """
    计算三节点三角形单元面积。
    要求节点按逆时针顺序输入，否则会得到非正面积并报错。
    """
    arr = _as_coord_array(coords)

    x1, y1 = arr[0]
    x2, y2 = arr[1]
    x3, y3 = arr[2]

    area = 0.5 * ((x2 - x1) * (y3 - y1) - (x3 - x1) * (y2 - y1))

    if area <= 0.0:
        raise ValueError(
            "三角形单元面积 <= 0。请检查：1）三个点是否共线；2）节点顺序是否为逆时针。"
        )

    return float(area)


def compute_b_c(coords: list[list[float]] | list[tuple[float, float]] | FloatArray) -> tuple[FloatArray, FloatArray]:
    """
    计算 CST 单元的 b, c 系数。
    b = [b_i, b_j, b_k]
    c = [c_i, c_j, c_k]
    """
    arr = _as_coord_array(coords)

    x_i, y_i = arr[0]
    x_j, y_j = arr[1]
    x_k, y_k = arr[2]

    b = np.array(
        [
            y_j - y_k,
            y_k - y_i,
            y_i - y_j,
        ],
        dtype=np.float64,
    )

    c = np.array(
        [
            x_k - x_j,
            x_i - x_k,
            x_j - x_i,
        ],
        dtype=np.float64,
    )

    return b, c


def constitutive_matrix(E: float, nu: float, plane_mode: str = "stress") -> FloatArray:
    """
    构造二维线弹性材料矩阵 D。
    支持:
    - plane_mode="stress"  : 平面应力
    - plane_mode="strain"  : 平面应变
    """
    if E <= 0.0:
        raise ValueError("弹性模量 E 必须大于 0。")

    if not (-1.0 < nu < 0.5):
        raise ValueError("泊松比 nu 必须满足 -1 < nu < 0.5。")

    mode = str(plane_mode).strip().lower()

    if mode in {"stress", "plane_stress"}:
        factor = E / (1.0 - nu ** 2)
        D = factor * np.array(
            [
                [1.0, nu, 0.0],
                [nu, 1.0, 0.0],
                [0.0, 0.0, (1.0 - nu) / 2.0],
            ],
            dtype=np.float64,
        )
        return D

    if mode in {"strain", "plane_strain"}:
        factor = E / ((1.0 + nu) * (1.0 - 2.0 * nu))
        D = factor * np.array(
            [
                [1.0 - nu, nu, 0.0],
                [nu, 1.0 - nu, 0.0],
                [0.0, 0.0, (1.0 - 2.0 * nu) / 2.0],
            ],
            dtype=np.float64,
        )
        return D

    raise ValueError(f"不支持的 plane_mode: {plane_mode!r}。可选值为 'stress' 或 'strain'。")


def strain_displacement_matrix(coords: list[list[float]] | list[tuple[float, float]] | FloatArray) -> FloatArray:
    """
    计算三节点线性三角形单元（CST）的应变矩阵 B。
    返回形状为 (3, 6) 的常数矩阵。
    """
    area = triangle_area(coords)
    b, c = compute_b_c(coords)

    B = (1.0 / (2.0 * area)) * np.array(
        [
            [b[0], 0.0,  b[1], 0.0,  b[2], 0.0],
            [0.0,  c[0], 0.0,  c[1], 0.0,  c[2]],
            [c[0], b[0], c[1], b[1], c[2], b[2]],
        ],
        dtype=np.float64,
    )

    return B


def element_stiffness(
    coords: list[list[float]] | list[tuple[float, float]] | FloatArray,
    E: float,
    nu: float,
    thickness: float,
    plane_mode: str = "stress",
) -> FloatArray:
    """
    计算 CST 单元刚度矩阵 Ke。
    """
    if thickness <= 0.0:
        raise ValueError("单元厚度 thickness 必须大于 0。")

    area = triangle_area(coords)
    B = strain_displacement_matrix(coords)
    D = constitutive_matrix(E, nu, plane_mode)

    Ke = thickness * area * (B.T @ D @ B)
    return Ke
