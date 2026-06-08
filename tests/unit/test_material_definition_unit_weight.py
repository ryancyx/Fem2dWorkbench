from __future__ import annotations

import pytest

from core.engineering.material_definition import MaterialDefinition


def test_material_definition_unit_weight_roundtrip() -> None:
    material = MaterialDefinition(
        id="mat1",
        name="steel",
        young_modulus=210e9,
        poisson_ratio=0.3,
        color="#8FB7D8",
        unit_weight=78500.0,
    )

    data = material.to_dict()

    assert data["unit_weight"] == 78500.0
    restored = MaterialDefinition.from_dict(data)
    assert restored.unit_weight == pytest.approx(78500.0)


def test_material_definition_missing_unit_weight_defaults_to_zero() -> None:
    restored = MaterialDefinition.from_dict(
        {
            "id": "mat1",
            "name": "legacy",
            "young_modulus": 1.0,
            "poisson_ratio": 0.25,
            "color": "#808080",
        }
    )

    assert restored.unit_weight == 0.0


def test_material_definition_negative_unit_weight_is_rejected() -> None:
    with pytest.raises(ValueError, match="unit_weight"):
        MaterialDefinition(
            id="mat1",
            name="bad",
            young_modulus=1.0,
            poisson_ratio=0.25,
            unit_weight=-1.0,
        )
