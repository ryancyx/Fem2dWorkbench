def test_import_fem_core():
    from core.fem.fem_model import FEMModel
    from core.solver import cst_element
    from core.solver import assembler
    from core.solver import solver
    from core.solver import postprocess

    assert FEMModel is not None
    assert cst_element is not None
    assert assembler is not None
    assert solver is not None
    assert postprocess is not None
    