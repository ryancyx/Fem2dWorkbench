import numpy as np

from core.fem.constraint import Constraint
from core.fem.element import Element
from core.fem.fem_model import FEMModel
from core.fem.load import Load
from core.fem.material import Material
from core.fem.node import Node
from core.solver.solver_api import solve_static_linear


def build_single_cst_reference_model() -> FEMModel:
    """
    构造一个最小 CST 三角形单元算例。

    节点：
        1: (0, 0)
        2: (1, 0)
        3: (0, 1)

    单元：
        1-2-3，逆时针编号，面积为正。

    约束：
        node 1: ux = 0, uy = 0
        node 2: uy = 0

    载荷：
        node 3: fy = -1000

    这个约束组合用于消除二维刚体位移：
        - node 1 固定两个平动自由度
        - node 2 固定 y 向，抑制整体转动
    """
    model = FEMModel()

    model.add_node(Node(id=1, x=0.0, y=0.0))
    model.add_node(Node(id=2, x=1.0, y=0.0))
    model.add_node(Node(id=3, x=0.0, y=1.0))

    model.add_material(
        Material(
            id=1,
            name="steel",
            young_modulus=210e9,
            poisson_ratio=0.3,
            thickness=0.01,
            plane_mode="stress",
        )
    )

    model.add_element(
        Element(
            id=1,
            node_ids=[1, 2, 3],
            material_id=1,
        )
    )

    model.add_constraint(
        Constraint(
            id=1,
            node_id=1,
            ux_fixed=True,
            uy_fixed=True,
        )
    )

    model.add_constraint(
        Constraint(
            id=2,
            node_id=2,
            uy_fixed=True,
        )
    )

    model.add_load(
        Load(
            id=1,
            node_id=3,
            fx=0.0,
            fy=-1000.0,
        )
    )

    return model


def test_single_cst_static_solve_basic_result_shape():
    model = build_single_cst_reference_model()

    result = solve_static_linear(model)

    assert result.global_stiffness.shape == (6, 6)
    assert result.global_load.shape == (6,)
    assert result.constrained_stiffness.shape == (6, 6)
    assert result.constrained_load.shape == (6,)
    assert result.displacement.shape == (6,)

    assert len(result.node_displacements) == 3
    assert len(result.element_results) == 1


def test_single_cst_static_solve_values_are_finite():
    model = build_single_cst_reference_model()

    result = solve_static_linear(model)

    assert np.all(np.isfinite(result.global_stiffness))
    assert np.all(np.isfinite(result.global_load))
    assert np.all(np.isfinite(result.constrained_stiffness))
    assert np.all(np.isfinite(result.constrained_load))
    assert np.all(np.isfinite(result.displacement))


def test_single_cst_global_stiffness_is_symmetric():
    model = build_single_cst_reference_model()

    result = solve_static_linear(model)

    assert np.allclose(
        result.global_stiffness,
        result.global_stiffness.T,
        rtol=1e-10,
        atol=1e-6,
    )


def test_single_cst_constraints_are_applied_to_displacement_result():
    model = build_single_cst_reference_model()

    result = solve_static_linear(model)

    ux1, uy1 = result.node_displacements[1]
    ux2, uy2 = result.node_displacements[2]

    assert abs(ux1) < 1e-12
    assert abs(uy1) < 1e-12
    assert abs(uy2) < 1e-12


def test_single_cst_loaded_node_has_nonzero_response():
    model = build_single_cst_reference_model()

    result = solve_static_linear(model)

    ux3, uy3 = result.node_displacements[3]

    assert abs(ux3) > 0.0 or abs(uy3) > 0.0