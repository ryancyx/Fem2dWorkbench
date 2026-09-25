from __future__ import annotations

import json
from pathlib import Path
import sys

from core.engineering.geometry import GeometryModel
from core.meshing.quality_sketch_mesher import generate_quality_sketch_tri_mesh


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) != 2:
        raise ValueError("Expected request and result file paths")
    request_path = Path(args[0])
    result_path = Path(args[1])
    request = json.loads(request_path.read_text(encoding="utf-8"))
    geometry = GeometryModel.from_dict(request["geometry"])
    mesh = generate_quality_sketch_tri_mesh(
        geometry=geometry,
        target_size=float(request["target_size"]),
        max_area=(
            None
            if request.get("max_area") is None
            else float(request["max_area"])
        ),
        min_angle=float(request["min_angle"]),
    )
    result_path.write_text(json.dumps(mesh.to_dict()), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
