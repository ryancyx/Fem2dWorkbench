from __future__ import annotations

import csv
from pathlib import Path

from services.result_service import (
    build_element_result_rows,
    build_node_displacement_rows,
    build_result_summary,
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
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
