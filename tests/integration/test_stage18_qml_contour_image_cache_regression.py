from __future__ import annotations

from pathlib import Path


def test_stage18_qml_contour_image_cache_regression() -> None:
    qml_text = Path("ui/qml/MainWorkbench.qml").read_text(encoding="utf-8", errors="ignore")

    assert "bridge.contourImageCacheJson" in qml_text
    assert "bridge.contourImageCacheValid" in qml_text
    assert "function contourImageCacheMap()" in qml_text
    assert "function contourVariantKey(showMesh, showDeformed)" in qml_text
    assert "function deformationPreviewImageSource()" in qml_text
    assert "function displacementContourImageSource()" in qml_text
    assert "function stressContourImageSource()" in qml_text
    assert "source: root.deformationPreviewImageSource()" in qml_text
    assert "source: root.displacementContourImageSource()" in qml_text
    assert "source: root.stressContourImageSource()" in qml_text
    assert "ensureContourImageCacheAvailable()" in qml_text
    assert "requestPaint()" not in qml_text[qml_text.index("id: stressContourDialog"):qml_text.index("function parseMaterialIdFromOption")]
