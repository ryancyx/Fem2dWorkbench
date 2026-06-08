from __future__ import annotations

from pathlib import Path
import re

from core.physics.constants import GRAVITY_ACCELERATION


def test_stage18_gravity_constant_is_10() -> None:
    assert GRAVITY_ACCELERATION == 10.0


def test_stage18_no_scattered_legacy_gravity_constants() -> None:
    root = Path(__file__).resolve().parents[2]
    allowed_files = {root / "core" / "physics" / "constants.py"}
    legacy_pattern = re.compile(r"9\.8(1)?")
    offenders: list[str] = []
    for path in root.rglob("*"):
        if path.is_dir():
            if path.name in {".git", ".pytest_cache", "__pycache__"}:
                continue
            continue
        if path.suffix not in {".py", ".qml"}:
            continue
        if path in allowed_files:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        if legacy_pattern.search(text):
            offenders.append(str(path.relative_to(root)))
    assert offenders == []
