from dataclasses import dataclass, field

from core.fem.node import Node
from core.fem.element import Element
from core.fem.material import Material
from core.fem.constraint import Constraint
from core.fem.load import Load


@dataclass
class FEMModel:
    nodes: list[Node] = field(default_factory=list)
    elements: list[Element] = field(default_factory=list)
    materials: list[Material] = field(default_factory=list)
    constraints: list[Constraint] = field(default_factory=list)
    loads: list[Load] = field(default_factory=list)

    def add_node(self, node: Node) -> None:
        if self.get_node_by_id(node.id) is not None:
            raise ValueError(f"节点 id {node.id} 已存在")
        self.nodes.append(node)

    def add_element(self, element: Element) -> None:
        if self.get_element_by_id(element.id) is not None:
            raise ValueError(f"单元 id {element.id} 已存在")
        self.elements.append(element)

    def add_material(self, material: Material) -> None:
        if self.get_material_by_id(material.id) is not None:
            raise ValueError(f"材料 id {material.id} 已存在")
        self.materials.append(material)

    def add_constraint(self, constraint: Constraint) -> None:
        if self.get_constraint_by_id(constraint.id) is not None:
            raise ValueError(f"约束 id {constraint.id} 已存在")
        self.constraints.append(constraint)

    def add_load(self, load: Load) -> None:
        if self.get_load_by_id(load.id) is not None:
            raise ValueError(f"载荷 id {load.id} 已存在")
        self.loads.append(load)

    def get_node_by_id(self, node_id: int) -> Node | None:
        for node in self.nodes:
            if node.id == node_id:
                return node
        return None

    def get_element_by_id(self, element_id: int) -> Element | None:
        for element in self.elements:
            if element.id == element_id:
                return element
        return None

    def get_material_by_id(self, material_id: int) -> Material | None:
        for material in self.materials:
            if material.id == material_id:
                return material
        return None

    def get_constraint_by_id(self, constraint_id: int) -> Constraint | None:
        for constraint in self.constraints:
            if constraint.id == constraint_id:
                return constraint
        return None

    def get_load_by_id(self, load_id: int) -> Load | None:
        for load in self.loads:
            if load.id == load_id:
                return load
        return None

    def to_dict(self) -> dict:
        return {
            "nodes": [node.to_dict() for node in self.nodes],
            "elements": [element.to_dict() for element in self.elements],
            "materials": [material.to_dict() for material in self.materials],
            "constraints": [constraint.to_dict() for constraint in self.constraints],
            "loads": [load.to_dict() for load in self.loads],
        }

    @classmethod
    def from_dict(cls, data: dict) -> "FEMModel":
        model = cls()
        model.nodes = [Node.from_dict(item) for item in data.get("nodes", [])]
        model.elements = [Element.from_dict(item) for item in data.get("elements", [])]
        model.materials = [Material.from_dict(item) for item in data.get("materials", [])]
        model.constraints = [Constraint.from_dict(item) for item in data.get("constraints", [])]
        model.loads = [Load.from_dict(item) for item in data.get("loads", [])]
        return model
