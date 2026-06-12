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
from matplotlib.ticker import FuncFormatter
import numpy as np


IMAGE_WIDTH = 1200
IMAGE_HEIGHT = 800
PALETTE_NAME = "jet"

STRESS_DISPLAY_SCALE = 1.0e-3
STRESS_DISPLAY_UNIT = "kPa"

_SUPERSCRIPT_DIGITS = str.maketrans({
    "-": "⁻",
    "0": "⁰",
    "1": "¹",
    "2": "²",
    "3": "³",
    "4": "⁴",
    "5": "⁵",
    "6": "⁶",
    "7": "⁷",
    "8": "⁸",
    "9": "⁹",
})


def _format_number(value: float, *, decimals: int = 4) -> str:
    """Format chart numbers without e+/e- notation.

    Normal-size values are printed directly. Very large or very small values are
    rendered as mantissa×10ⁿ using unicode superscripts, which keeps the PNG
    labels readable while avoiding raw scientific notation.
    """
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return str(value)
    if not np.isfinite(numeric):
        return str(numeric)
    if numeric == 0.0:
        return "0"

    abs_value = abs(numeric)
    if abs_value >= 100000.0 or abs_value < 0.001:
        return _format_power10(numeric, decimals=decimals)

    if abs_value >= 1000.0:
        formatted = f"{numeric:.1f}"
    elif abs_value >= 100.0:
        formatted = f"{numeric:.2f}"
    elif abs_value >= 1.0:
        formatted = f"{numeric:.3f}"
    else:
        formatted = f"{numeric:.6f}"
    return formatted.rstrip("0").rstrip(".")


def _format_power10(value: float, *, decimals: int = 3) -> str:
    if value == 0.0:
        return "0"
    sign = "-" if value < 0.0 else ""
    abs_value = abs(value)
    exponent = int(np.floor(np.log10(abs_value)))
    mantissa = abs_value / (10.0 ** exponent)
    mantissa_text = f"{mantissa:.{decimals}g}".rstrip("0").rstrip(".")
    exponent_text = str(exponent).translate(_SUPERSCRIPT_DIGITS)
    return f"{sign}{mantissa_text}×10{exponent_text}"


def _format_min_max_text(min_value: float, max_value: float, unit_label: str) -> str:
    unit = f" {unit_label}" if unit_label else ""
    return f"Min = {_format_number(min_value)}{unit}\nMax = {_format_number(max_value)}{unit}"


def _is_stress_unit(unit_label: str) -> bool:
    return unit_label.strip().lower() in {"kpa", "kilopascal", "kilopascals"}




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
                    unit_label=STRESS_DISPLAY_UNIT,
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
                    unit_label=STRESS_DISPLAY_UNIT,
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
            f"Max |u| = {_format_number(float((data.get('summary') or {}).get('max_displacement', 0.0) or 0.0))}\n"
            f"Scale factor = {_format_number(factor, decimals=3)}",
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
    display_scale = STRESS_DISPLAY_SCALE if _is_stress_unit(unit_label) else 1.0
    values = [float(value) * display_scale for value in values]
    element_values = [float(value) * display_scale for value in element_values]
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
        colorbar.set_label(f"{legend_label} ({unit_label})".strip() if unit_label else legend_label)
        colorbar.ax.yaxis.set_major_formatter(FuncFormatter(lambda value, _pos: _format_number(value)))
        colorbar.update_ticks()
        min_value = float(data.get("min_displacement", data.get("min_von_mises", 0.0)) or 0.0) * display_scale
        max_value = float(data.get("max_displacement", data.get("max_von_mises", 0.0)) or 0.0) * display_scale
        ax.set_title(title if not unit_label else f"{title} ({unit_label})", fontsize=14)
        ax.text(
            0.02,
            0.02,
            f"{_format_min_max_text(min_value, max_value, unit_label)}\nDeformed view = {'On' if show_deformed else 'Off'}",
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
