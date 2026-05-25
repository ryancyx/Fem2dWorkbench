from core.fem.fem_model import FEMModel
from core.solver.solver import (
    SolverResult,
    solve_linear_static,
)


def solve_static_linear(model: FEMModel) -> SolverResult:
    """
    Fem2dWorkbench 求解器统一入口。

    当前阶段：
    - 线弹性
    - 小变形
    - 二维静力问题
    - CST 三节点单元
    """
    return solve_linear_static(model)