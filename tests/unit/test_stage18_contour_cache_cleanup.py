from __future__ import annotations

import os
import time
from pathlib import Path

from services.contour_cache_service import (
    cleanup_old_cache_dirs,
    clear_contour_cache_dir,
    create_contour_cache_dir,
)


def test_stage18_contour_cache_cleanup_functions() -> None:
    cache_dir = create_contour_cache_dir("pytest_cleanup")
    sample = cache_dir / "sample.txt"
    sample.write_text("cache", encoding="utf-8")
    assert cache_dir.exists()

    clear_contour_cache_dir(cache_dir)
    assert not cache_dir.exists()


def test_stage18_contour_cache_cleanup_keeps_user_exports(tmp_path: Path) -> None:
    user_export_dir = tmp_path / "exports"
    user_export_dir.mkdir()
    exported = user_export_dir / "user.png"
    exported.write_text("keep", encoding="utf-8")

    cache_dir = create_contour_cache_dir("pytest_keep_user_exports")
    (cache_dir / "cache.txt").write_text("cache", encoding="utf-8")
    clear_contour_cache_dir(cache_dir)

    assert exported.exists()


def test_stage18_cleanup_old_cache_dirs() -> None:
    old_dir = create_contour_cache_dir("pytest_old_cache")
    (old_dir / "old.txt").write_text("cache", encoding="utf-8")
    old_time = time.time() - 48 * 3600
    os.utime(old_dir, (old_time, old_time))
    cleanup_old_cache_dirs(max_age_hours=1.0)
    assert not old_dir.exists()
