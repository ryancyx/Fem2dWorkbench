from __future__ import annotations

from services.contour_palette_service import contour_hex_color


def test_stage18_contour_color_map_hits_expected_endpoints() -> None:
    assert contour_hex_color(0.0, 0.0, 1.0) == "#000080"
    assert contour_hex_color(1.0, 0.0, 1.0) == "#FF0000"


def test_stage18_contour_color_map_mid_value_is_green_yellow_band() -> None:
    middle = contour_hex_color(0.5, 0.0, 1.0)
    assert middle.startswith("#")
    assert middle not in {"#000080", "#FF0000"}
    green = int(middle[3:5], 16)
    assert green >= 0xCC


def test_stage18_contour_color_map_handles_degenerate_range() -> None:
    assert contour_hex_color(5.0, 5.0, 5.0).startswith("#")
