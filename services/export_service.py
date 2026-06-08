from __future__ import annotations

import csv
import json
from pathlib import Path

from services.result_service import (
    build_deformation_plot_data,
    build_displacement_contour_data,
    build_element_result_rows,
    build_node_displacement_rows,
    build_result_summary,
    build_stress_contour_data,
)
from services.solve_service import WorkbenchSolveResult


def export_node_displacements_csv(
    solution: WorkbenchSolveResult,
    file_path: str | Path,
) -> None:
    path = Path(file_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = ["node_id", "x", "y", "ux", "uy", "u_magnitude"]

    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        for row in build_node_displacement_rows(solution):
            writer.writerow(row.to_dict())


def export_element_results_csv(
    solution: WorkbenchSolveResult,
    file_path: str | Path,
) -> None:
    path = Path(file_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "element_id",
        "node_ids",
        "source_face_id",
        "strain_x",
        "strain_y",
        "strain_xy",
        "stress_x",
        "stress_y",
        "stress_xy",
        "von_mises",
    ]

    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        for row in build_element_result_rows(solution):
            row_data = row.to_dict()
            row_data["node_ids"] = " ".join(str(node_id) for node_id in row.node_ids)
            writer.writerow(row_data)


def export_result_summary_txt(
    solution: WorkbenchSolveResult,
    file_path: str | Path,
) -> None:
    path = Path(file_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    summary = build_result_summary(solution)

    lines = [
        f"node_count: {summary.node_count}",
        f"element_count: {summary.element_count}",
        f"max_displacement: {summary.max_displacement}",
        f"max_displacement_node_id: {summary.max_displacement_node_id}",
        f"max_von_mises: {summary.max_von_mises}",
        f"max_von_mises_element_id: {summary.max_von_mises_element_id}",
        f"warning_count: {summary.warning_count}",
        f"gravity_enabled: {bool(solution.project.metadata.get('gravity_enabled', False))}",
        f"gravity_direction_x: {float(solution.project.metadata.get('gravity_direction_x', 0.0) or 0.0)}",
        f"gravity_direction_y: {float(solution.project.metadata.get('gravity_direction_y', -1.0) or -1.0)}",
    ]
    if solution.warnings:
        lines.append("warnings:")
        lines.extend(f"- {warning}" for warning in solution.warnings)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def export_deformation_plot_data_json(
    solution: WorkbenchSolveResult,
    file_path: str | Path,
) -> None:
    path = Path(file_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(build_deformation_plot_data(solution), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def export_displacement_contour_data_json(
    solution: WorkbenchSolveResult,
    file_path: str | Path,
) -> None:
    path = Path(file_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(build_displacement_contour_data(solution), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def export_stress_contour_data_json(
    solution: WorkbenchSolveResult,
    file_path: str | Path,
) -> None:
    path = Path(file_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(build_stress_contour_data(solution), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def export_von_mises_contour_data_json(
    solution: WorkbenchSolveResult,
    file_path: str | Path,
) -> None:
    export_stress_contour_data_json(solution, file_path)
