import math

from core.engineering.analysis_step import AnalysisStep
from core.engineering.boundary_condition_definition import BoundaryConditionDefinition
from core.engineering.engineering_project import EngineeringProject
from core.engineering.geometry import GeometryModel
from core.engineering.load_definition import LoadDefinition
from core.engineering.material_definition import MaterialDefinition
from core.engineering.part import Part
from core.engineering.section import SectionDefinition
from core.io.project_json import load_project_from_json, save_project_to_json
from core.meshing.rectangular_mesher import generate_rectangular_tri_mesh


def build_stage3_reference_project() -> EngineeringProject:
    project = EngineeringProject(name="stage3_rectangle_mesh_demo")

    project.add_material(
        MaterialDefinition(
            id="1",
            name="steel",
            young_modulus=210e9,
            poisson_ratio=0.3,
            color="#8FB7D8",
        )
    )

    project.add_section(
        SectionDefinition(
            id="1",
            name="steel_plate_section",
            material_id="1",
            thickness=0.01,
            plane_mode="stress",
        )
    )

    geometry = GeometryModel.create_rectangle(
        width=2.0,
        height=1.0,
        origin_x=0.0,
        origin_y=0.0,
    )

    project.add_part(
        Part(
            id="1",
            name="rectangle_plate",
            geometry=geometry,
            section_id="1",
        )
    )

    project.add_analysis_step(
        AnalysisStep(
            id="1",
            name="static_step_1",
            step_type="static_linear",
        )
    )

    project.add_boundary_condition(
        BoundaryConditionDefinition(
            id="1",
            name="fix_left_edge",
            step_id="1",
            target_type="geometry_edge",
            target_id="left",
            ux_fixed=True,
            uy_fixed=True,
        )
    )

    project.add_load(
        LoadDefinition(
            id="1",
            name="right_edge_downward_uniform_load",
            step_id="1",
            target_type="geometry_edge",
            target_id="right",
            qx=0.0,
            qy=-1000.0,
            load_type="edge_uniform",
        )
    )

    project.validate_references()
    return project


def triangle_signed_area(p1, p2, p3) -> float:
    return 0.5 * (
        (p2.x - p1.x) * (p3.y - p1.y)
        - (p3.x - p1.x) * (p2.y - p1.y)
    )


def test_stage3_project_json_then_generate_rectangular_mesh(tmp_path):
    """
    阶段 3 截止集成测试：

    EngineeringProject
        -> JSON 保存/读取
        -> 读取 Part.geometry
        -> generate_rectangular_tri_mesh()
        -> MeshModel 结构检查

    注意：
    这里还不进入 compile_project_to_fem()，
    因为 compiler 是阶段 4 的内容。
    """
    project = build_stage3_reference_project()

    file_path = tmp_path / "stage3_rectangle_mesh_demo.f2dw.json"
    save_project_to_json(project, file_path)

    restored_project = load_project_from_json(file_path)
    restored_project.validate_references()

    assert restored_project.to_dict() == project.to_dict()

    part = restored_project.get_part_by_id("1")
    assert part is not None

    nx = 4
    ny = 2
    mesh = generate_rectangular_tri_mesh(
        geometry=part.geometry,
        nx=nx,
        ny=ny,
    )

    assert len(mesh.nodes) == (nx + 1) * (ny + 1)
    assert len(mesh.elements) == 2 * nx * ny

    assert set(mesh.geometry_edge_to_mesh_node_ids.keys()) == {
        "bottom",
        "right",
        "top",
        "left",
    }

    assert len(mesh.geometry_edge_to_mesh_node_ids["bottom"]) == nx + 1
    assert len(mesh.geometry_edge_to_mesh_node_ids["top"]) == nx + 1
    assert len(mesh.geometry_edge_to_mesh_node_ids["left"]) == ny + 1
    assert len(mesh.geometry_edge_to_mesh_node_ids["right"]) == ny + 1

    assert set(mesh.geometry_edge_to_mesh_element_edges.keys()) == {
        "bottom",
        "right",
        "top",
        "left",
    }

    assert len(mesh.geometry_edge_to_mesh_element_edges["bottom"]) == nx
    assert len(mesh.geometry_edge_to_mesh_element_edges["top"]) == nx
    assert len(mesh.geometry_edge_to_mesh_element_edges["left"]) == ny
    assert len(mesh.geometry_edge_to_mesh_element_edges["right"]) == ny

    for element in mesh.elements:
        assert element.element_type == "CST"
        assert len(element.node_ids) == 3

        n1 = mesh.get_node_by_id(element.node_ids[0])
        n2 = mesh.get_node_by_id(element.node_ids[1])
        n3 = mesh.get_node_by_id(element.node_ids[2])

        assert n1 is not None
        assert n2 is not None
        assert n3 is not None

        area = triangle_signed_area(n1, n2, n3)
        assert area > 0.0

    for edge_id, element_edges in mesh.geometry_edge_to_mesh_element_edges.items():
        assert edge_id in {"bottom", "right", "top", "left"}

        for element_id, local_a, local_b in element_edges:
            element = mesh.get_element_by_id(element_id)

            assert element is not None
            assert local_a in (0, 1, 2)
            assert local_b in (0, 1, 2)
            assert local_a != local_b


def test_stage3_mesh_to_dict_from_dict_keeps_basic_structure():
    """
    验证 MeshModel 自身可以序列化/反序列化。

    这里不强行要求 tuple/list 细节完全一致，
    只检查关键结构是否保留。
    """
    geometry = GeometryModel.create_rectangle(width=2.0, height=1.0)
    mesh = generate_rectangular_tri_mesh(
        geometry=geometry,
        nx=3,
        ny=2,
    )

    restored = type(mesh).from_dict(mesh.to_dict())

    assert len(restored.nodes) == len(mesh.nodes)
    assert len(restored.elements) == len(mesh.elements)

    assert set(restored.geometry_edge_to_mesh_node_ids.keys()) == {
        "bottom",
        "right",
        "top",
        "left",
    }

    assert set(restored.geometry_edge_to_mesh_element_edges.keys()) == {
        "bottom",
        "right",
        "top",
        "left",
    }

    for original_node, restored_node in zip(mesh.nodes, restored.nodes):
        assert restored_node.id == original_node.id
        assert math.isclose(restored_node.x, original_node.x)
        assert math.isclose(restored_node.y, original_node.y)

    for original_element, restored_element in zip(mesh.elements, restored.elements):
        assert restored_element.id == original_element.id
        assert restored_element.node_ids == original_element.node_ids
        assert restored_element.element_type == original_element.element_type
        assert restored_element.source_face_id == original_element.source_face_id