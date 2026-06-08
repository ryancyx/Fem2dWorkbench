from __future__ import annotations

from pathlib import Path
import json

import pytest

from services.export_service import export_stress_contour_data_json
from services.project_factory_service import create_rectangle_plate_project
from services.result_service import build_stress_contour_data
from services.solve_service import solve_workbench_project


def test_stage18_stress_contour_data_exact_and_smoothed_values(tmp_path: Path) -> None:
    project = create_rectangle_plate_project(
        width=2.0,
        height=1.0,
        young_modulus=210e9,
        poisson_ratio=0.3,
        thickness=0.01,
        qy=-1000.0,
    )
    solution = solve_workbench_project(
        project=project,
        part_id="part_rectangle",
        step_id="step_static",
        nx=4,
        ny=2,
    )
    data = build_stress_contour_data(solution)
    assert data["nodes"]
    assert data["elements"]
    assert data["title"] == "Von Mises 应力云图"
    assert data["scalar_label"] == "Von Mises"
    assert data["unit_label"] == "Pa"

    first_element = data["elements"][0]
    assert "von_mises" in first_element
    assert "element_von_mises" in first_element
    assert "nodal_smoothed_von_mises" in first_element
    assert len(first_element["nodal_smoothed_von_mises"]) == 3
    assert first_element["von_mises"] == first_element["element_von_mises"]

    element_values = [row["element_von_mises"] for row in data["elements"]]
    assert data["min_von_mises"] == min(element_values)
    assert data["max_von_mises"] == max(element_values)

    node_to_expected: dict[int, list[float]] = {}
    for element in data["elements"]:
        for node_id in element["node_ids"]:
            node_to_expected.setdefault(node_id, []).append(element["element_von_mises"])
    node_rows = {row["id"]: row for row in data["nodes"]}
    for node_id, values in node_to_expected.items():
        assert node_rows[node_id]["smoothed_von_mises"] == pytest.approx(sum(values) / len(values))

    output_file = tmp_path / "stress_contour_data.json"
    export_stress_contour_data_json(solution, output_file)
    assert output_file.exists()
    exported = json.loads(output_file.read_text(encoding="utf-8"))
    assert exported["elements"]
