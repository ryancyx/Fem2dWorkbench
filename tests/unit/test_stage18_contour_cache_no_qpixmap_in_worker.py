from __future__ import annotations

from pathlib import Path


def test_stage18_contour_cache_service_avoids_qpixmap_and_qml_grab() -> None:
    text = Path("services/contour_cache_service.py").read_text(encoding="utf-8", errors="ignore")

    assert "QPixmap" not in text
    assert "grabToImage" not in text
    assert "matplotlib.use(\"Agg\")" in text
    assert "import matplotlib.pyplot as plt" in text
