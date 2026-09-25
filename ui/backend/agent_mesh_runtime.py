from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile

from core.engineering.geometry import GeometryModel
from core.engineering.mesh_model import MeshModel


def generate_agent_mesh_isolated(
    geometry: GeometryModel,
    target_size: float = 0.2,
    max_area: float | None = None,
    min_angle: float = 25.0,
) -> MeshModel:
    """Generate an Agent mesh in a child process whose main thread owns Gmsh.

    The Agent workflow itself may therefore run in the ordinary Qt worker thread
    without asking Gmsh to install signal handlers outside a process main thread.
    Only plain JSON geometry/mesh data crosses the process boundary.
    """
    request = {
        "geometry": geometry.to_dict(),
        "target_size": float(target_size),
        "max_area": None if max_area is None else float(max_area),
        "min_angle": float(min_angle),
    }
    project_root = Path(__file__).resolve().parents[2]
    with tempfile.TemporaryDirectory(prefix="fem2d_agent_mesh_") as temp_dir:
        temp_path = Path(temp_dir)
        request_path = temp_path / "request.json"
        result_path = temp_path / "result.json"
        request_path.write_text(json.dumps(request), encoding="utf-8")
        completed = subprocess.run(
            [
                sys.executable,
                "-m",
                "ui.backend.agent_mesh_worker",
                str(request_path),
                str(result_path),
            ],
            capture_output=True,
            text=True,
            timeout=180,
            check=False,
            cwd=str(project_root),
        )
        if completed.returncode != 0:
            detail = (completed.stderr or completed.stdout or "unknown error").strip()
            raise RuntimeError(f"Agent Gmsh process failed: {detail}")
        if not result_path.exists():
            raise RuntimeError("Agent Gmsh process did not produce a mesh result")
        result = json.loads(result_path.read_text(encoding="utf-8"))
    if not isinstance(result, dict):
        raise RuntimeError("Agent Gmsh process returned an invalid mesh payload")
    return MeshModel.from_dict(result)
