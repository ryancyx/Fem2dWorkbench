from __future__ import annotations

from typing import Final


CONTOUR_COLOR_STOPS: Final[list[tuple[float, str]]] = [
    (0.00, "#000080"),
    (0.15, "#0000FF"),
    (0.30, "#00FFFF"),
    (0.45, "#00FF00"),
    (0.60, "#FFFF00"),
    (0.75, "#FF9900"),
    (1.00, "#FF0000"),
]


def clamp01(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def normalize_scalar(value: float, min_value: float, max_value: float) -> float:
    min_value = float(min_value)
    max_value = float(max_value)
    if abs(max_value - min_value) <= 1.0e-12:
        return 0.5
    return clamp01((float(value) - min_value) / (max_value - min_value))


def interpolate_hex_color(color_a: str, color_b: str, t: float) -> str:
    t = clamp01(t)
    a_r, a_g, a_b = _parse_hex_color(color_a)
    b_r, b_g, b_b = _parse_hex_color(color_b)
    red = round(a_r + (b_r - a_r) * t)
    green = round(a_g + (b_g - a_g) * t)
    blue = round(a_b + (b_b - a_b) * t)
    return f"#{red:02X}{green:02X}{blue:02X}"


def contour_hex_color(value: float, min_value: float, max_value: float) -> str:
    ratio = normalize_scalar(value, min_value, max_value)
    for index in range(len(CONTOUR_COLOR_STOPS) - 1):
        left_ratio, left_color = CONTOUR_COLOR_STOPS[index]
        right_ratio, right_color = CONTOUR_COLOR_STOPS[index + 1]
        if ratio <= right_ratio or index == len(CONTOUR_COLOR_STOPS) - 2:
            local_span = max(right_ratio - left_ratio, 1.0e-12)
            local_t = (ratio - left_ratio) / local_span
            return interpolate_hex_color(left_color, right_color, local_t)
    return CONTOUR_COLOR_STOPS[-1][1]


def _parse_hex_color(color: str) -> tuple[int, int, int]:
    text = str(color).strip()
    if len(text) != 7 or not text.startswith("#"):
        raise ValueError(f"Unsupported hex color format: {color!r}")
    return (
        int(text[1:3], 16),
        int(text[3:5], 16),
        int(text[5:7], 16),
    )
