from __future__ import annotations

from pathlib import Path
import json

from services.export_service import export_displacement_contour_data_json
from services.project_factory_service import create_rectangle_plate_project
from services.result_service import build_displacement_contour_data
from services.solve_service import solve_workbench_project


def test_stage18_displacement_contour_data_and_export(tmp_path: Path) -> None:
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
    data = build_displacement_contour_data(solution)
    assert data["nodes"]
    assert data["elements"]
    first_node = data["nodes"][0]
    assert {"ux", "uy", "u"} <= set(first_node)
    displacement_values = [row["u"] for row in data["nodes"]]
    assert data["min_displacement"] == min(displacement_values)
    assert data["max_displacement"] == max(displacement_values)

    output_file = tmp_path / "displacement_contour_data.json"
    export_displacement_contour_data_json(solution, output_file)
    assert output_file.exists()
    exported = json.loads(output_file.read_text(encoding="utf-8"))
    assert exported["nodes"]
