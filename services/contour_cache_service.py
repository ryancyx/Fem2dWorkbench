from __future__ import annotations

import json
import shutil
import tempfile
import time
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import matplotlib.tri as mtri
import numpy as np


IMAGE_WIDTH = 1200
IMAGE_HEIGHT = 800
PALETTE_NAME = "jet"


def create_contour_cache_dir(session_id: str) -> Path:
    root = Path(tempfile.gettempdir()) / "Fem2dWorkbench" / "contour_cache" / session_id
    root.mkdir(parents=True, exist_ok=True)
    return root


def clear_contour_cache_dir(path: str | Path | None) -> None:
    if not path:
        return
    cache_path = Path(path)
    try:
        if cache_path.exists():
            shutil.rmtree(cache_path)
    except OSError:
        return


def cleanup_old_cache_dirs(max_age_hours: float = 24.0) -> None:
    base_dir = Path(tempfile.gettempdir()) / "Fem2dWorkbench" / "contour_cache"
    if not base_dir.exists():
        return
    cutoff = time.time() - max_age_hours * 3600.0
    for child in base_dir.iterdir():
        try:
            if child.is_dir() and child.stat().st_mtime < cutoff:
                shutil.rmtree(child, ignore_errors=True)
        except OSError:
            continue


def build_contour_image_cache_json(image_map: dict[str, dict[str, str]]) -> str:
    return json.dumps(image_map, ensure_ascii=False)


def generate_contour_images(
    *,
    output_dir: str | Path,
    deformation_data: dict[str, Any],
    displacement_data: dict[str, Any],
    stress_exact_data: dict[str, Any],
    stress_smooth_data: dict[str, Any],
) -> dict[str, dict[str, str]]:
    cache_dir = Path(output_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)
    image_map: dict[str, dict[str, str]] = {
        "deformation_preview": {},
        "displacement": {},
        "stress_exact": {},
        "stress_smooth": {},
    }

    for show_mesh in (True, False):
        for show_deformed in (True, False):
            key = _variant_key(show_mesh, show_deformed)
            image_map["deformation_preview"][key] = str(
                _render_deformation(cache_dir, deformation_data, show_mesh, show_deformed)
            )
            image_map["displacement"][key] = str(
                _render_scalar_contour(
                    cache_dir,
                    "displacement",
                    displacement_data,
                    show_mesh,
                    show_deformed,
                    mode="smooth",
                    title="Displacement Contour",
                    legend_label="|u|",
                    unit_label="",
                )
            )
            image_map["stress_exact"][key] = str(
                _render_scalar_contour(
                    cache_dir,
                    "stress_exact",
                    stress_exact_data,
                    show_mesh,
                    show_deformed,
                    mode="exact",
                    title="Stress Contour | Exact",
                    legend_label="Von Mises",
                    unit_label="Pa",
                )
            )
            image_map["stress_smooth"][key] = str(
                _render_scalar_contour(
                    cache_dir,
                    "stress_smooth",
                    stress_smooth_data,
                    show_mesh,
                    show_deformed,
                    mode="smooth",
                    title="Stress Contour | Smoothed",
                    legend_label="Von Mises",
                    unit_label="Pa",
                )
            )

    return image_map


def _render_deformation(cache_dir: Path, data: dict[str, Any], show_mesh: bool, show_deformed: bool) -> Path:
    node_rows = data.get("nodes", [])
    elements = data.get("elements", [])
    factor = float((data.get("summary") or {}).get("default_scale_factor", 1.0) or 1.0)
    x, y, triangles, _, _, _ = _mesh_arrays(node_rows, elements, show_deformed=False)
    dx, dy, _, _, _, _ = _mesh_arrays(node_rows, elements, show_deformed=show_deformed, factor=factor)

    fig, ax = _new_figure()
    try:
        if show_mesh:
            ax.triplot(mtri.Triangulation(x, y, triangles), color="#94A3B8", linewidth=0.8)
        if show_deformed:
            ax.triplot(mtri.Triangulation(dx, dy, triangles), color="#7C3AED", linewidth=1.2)
        else:
            ax.triplot(mtri.Triangulation(x, y, triangles), color="#475569", linewidth=1.1)
        ax.set_title("Deformation Preview", fontsize=14)
        ax.text(
            0.02,
            0.02,
            f"Max |u| = {float((data.get('summary') or {}).get('max_displacement', 0.0) or 0.0):.4e}\n"
            f"Scale factor = {factor:.3f}",
            transform=ax.transAxes,
            fontsize=10,
            color="#334155",
            verticalalignment="bottom",
        )
        _finish_axes(ax)
        file_path = cache_dir / f"deformation_preview_{_variant_key(show_mesh, show_deformed)}.png"
        fig.savefig(file_path, dpi=100, bbox_inches="tight", facecolor="#F8FAFC")
        return file_path
    finally:
        plt.close(fig)


def _render_scalar_contour(
    cache_dir: Path,
    prefix: str,
    data: dict[str, Any],
    show_mesh: bool,
    show_deformed: bool,
    *,
    mode: str,
    title: str,
    legend_label: str,
    unit_label: str,
) -> Path:
    node_rows = data.get("nodes", [])
    elements = data.get("elements", [])
    factor = float(data.get("default_scale_factor", 1.0) or 1.0)
    x, y, triangles, _, values, element_values = _mesh_arrays(
        node_rows,
        elements,
        show_deformed=show_deformed,
        factor=factor,
        mode=mode,
    )
    triangulation = mtri.Triangulation(x, y, triangles)
    fig, ax = _new_figure()
    try:
        if mode == "exact":
            mappable = ax.tripcolor(
                triangulation,
                facecolors=np.asarray(element_values, dtype=float),
                cmap=PALETTE_NAME,
                shading="flat",
            )
        else:
            mappable = ax.tripcolor(
                triangulation,
                np.asarray(values, dtype=float),
                cmap=PALETTE_NAME,
                shading="gouraud",
            )
        if show_mesh:
            ax.triplot(triangulation, color=(0.1, 0.15, 0.2, 0.28), linewidth=0.6)
        colorbar = fig.colorbar(mappable, ax=ax, fraction=0.046, pad=0.04)
        colorbar.set_label(f"{legend_label} {unit_label}".strip())
        min_value = float(data.get("min_displacement", data.get("min_von_mises", 0.0)) or 0.0)
        max_value = float(data.get("max_displacement", data.get("max_von_mises", 0.0)) or 0.0)
        ax.set_title(title, fontsize=14)
        ax.text(
            0.02,
            0.02,
            f"Min = {min_value:.4e}\nMax = {max_value:.4e}\nDeformed view = {'On' if show_deformed else 'Off'}",
            transform=ax.transAxes,
            fontsize=10,
            color="#334155",
            verticalalignment="bottom",
        )
        _finish_axes(ax)
        file_path = cache_dir / f"{prefix}_{_variant_key(show_mesh, show_deformed)}.png"
        fig.savefig(file_path, dpi=100, bbox_inches="tight", facecolor="#F8FAFC")
        return file_path
    finally:
        plt.close(fig)


def _mesh_arrays(
    node_rows: list[dict[str, Any]],
    elements: list[dict[str, Any]],
    *,
    show_deformed: bool,
    factor: float = 1.0,
    mode: str = "smooth",
):
    node_id_key = "node_id" if node_rows and "node_id" in node_rows[0] else "id"
    node_map = {int(node[node_id_key]): node for node in node_rows}
    node_ids = sorted(node_map.keys())
    index_map = {node_id: index for index, node_id in enumerate(node_ids)}

    x = []
    y = []
    values = []
    for node_id in node_ids:
        node = node_map[node_id]
        px = float(node["x"])
        py = float(node["y"])
        if show_deformed:
            px += float(node.get("ux", 0.0)) * factor
            py += float(node.get("uy", 0.0)) * factor
        x.append(px)
        y.append(py)
        if "u" in node:
            values.append(float(node["u"]))
        elif "smoothed_von_mises" in node:
            values.append(float(node["smoothed_von_mises"]))
        else:
            values.append(0.0)

    triangles = []
    element_values = []
    for element in elements:
        triangles.append([index_map[int(node_id)] for node_id in element["node_ids"]])
        if mode == "exact":
            element_values.append(float(element.get("von_mises", 0.0)))

    return np.asarray(x), np.asarray(y), np.asarray(triangles), node_ids, values, element_values


def _new_figure():
    fig, ax = plt.subplots(figsize=(IMAGE_WIDTH / 100.0, IMAGE_HEIGHT / 100.0), dpi=100)
    fig.patch.set_facecolor("#F8FAFC")
    ax.set_facecolor("#F8FAFC")
    return fig, ax


def _finish_axes(ax) -> None:
    ax.set_aspect("equal", adjustable="box")
    ax.grid(False)
    ax.tick_params(labelsize=9, colors="#64748B")
    for spine in ax.spines.values():
        spine.set_color("#CBD5E1")


def _variant_key(show_mesh: bool, show_deformed: bool) -> str:
    return f"grid_{'on' if show_mesh else 'off'}_deformed_{'on' if show_deformed else 'off'}"
