from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

import pytest

from agent.simulation_plan import SimulationPlan
from services.project_factory_service import create_empty_workbench_project


@pytest.fixture
def valid_plan() -> SimulationPlan:
    return SimulationPlan(
        version=1,
        geometry={"type": "rectangle", "width": 100.0, "height": 50.0},
        material={
            "name": "Steel",
            "E": 210000.0,
            "nu": 0.3,
            "thickness": 0.01,
            "plane_mode": "stress",
        },
        edge_constraints=[
            {"target": {"selector": "left"}, "ux": 0.0, "uy": 0.0}
        ],
        edge_loads=[
            {"target": {"selector": "right"}, "vector": [100.0, 0.0]}
        ],
        mesh_size=5.0,
        requested_result="von_mises",
    )


@pytest.fixture
def empty_project():
    return create_empty_workbench_project("agent_test")


class FakeLLMClient:
    def __init__(
        self,
        response: dict[str, Any] | Callable[[str, str, dict[str, Any]], dict[str, Any]],
    ) -> None:
        self.response = response
        self.requests: list[tuple[str, str, dict[str, Any]]] = []

    def request(
        self,
        system_prompt: str,
        user_content: str,
        schema: dict[str, Any],
    ) -> dict[str, Any]:
        self.requests.append((system_prompt, user_content, schema))
        if callable(self.response):
            return self.response(system_prompt, user_content, schema)
        return self.response


@pytest.fixture
def fake_llm() -> FakeLLMClient:
    def response(_system_prompt: str, user_content: str, schema: dict[str, Any]) -> dict[str, Any]:
        content = json.loads(user_content)
        title = schema.get("title")
        if title == "GeometryAction":
            geometry = content["geometry"]
            if geometry["type"] == "rectangle":
                parameters = {
                    "width": geometry["width"],
                    "height": geometry["height"],
                    "originX": geometry.get("originX", 0.0),
                    "originY": geometry.get("originY", 0.0),
                }
            else:
                parameters = {
                    "centerX": geometry["centerX"],
                    "centerY": geometry["centerY"],
                    "radius": geometry["radius"],
                }
            return {"action": f"create_{geometry['type']}", "parameters": parameters}
        if title == "MaterialActions":
            material = content["material"]
            return {
                "actions": [
                    {
                        "action": "create_material",
                        "name": material["name"],
                        "E": material["E"],
                        "nu": material["nu"],
                        "color": material.get("color", "#808080"),
                        "unit_weight": material.get("unit_weight", 0.0),
                    },
                    {
                        "action": "assign_material",
                        "name": material["name"],
                        "thickness": material["thickness"],
                        "plane_mode": material["plane_mode"],
                    },
                ]
            }
        if title == "BCLoadActions":
            subplan = content["constraintsAndLoads"]
            actions: list[dict[str, Any]] = []
            for key, action in (
                ("pointConstraints", "add_point_constraint"),
                ("edgeConstraints", "add_edge_constraint"),
                ("pointLoads", "add_point_load"),
                ("edgeLoads", "add_edge_load"),
            ):
                actions.extend({"action": action, **row} for row in subplan[key])
            return {"actions": actions}
        raise AssertionError(f"Unexpected fake LLM schema: {title}")

    return FakeLLMClient(response)
