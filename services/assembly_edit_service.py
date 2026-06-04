from __future__ import annotations

from core.engineering.assembly import PartInstance
from core.engineering.engineering_project import EngineeringProject


def ensure_default_instance(project: EngineeringProject) -> EngineeringProject:
    """Compatibility no-op: assemblies now start empty until the user creates instances."""
    get_active_instance_id(project)
    return project


def list_instances(project: EngineeringProject) -> list[dict]:
    active_instance_id = get_active_instance_id(project)
    rows = []
    for instance in project.assembly.instances:
        part = project.get_part_by_id(instance.part_id)
        rows.append(
            {
                "id": instance.id,
                "name": instance.name,
                "part_id": instance.part_id,
                "part_name": part.name if part is not None else "",
                "tx": instance.translation_x,
                "ty": instance.translation_y,
                "rotation": instance.rotation_degrees,
                "is_active": instance.id == active_instance_id,
            }
        )
    return rows


def get_active_instance_id(project: EngineeringProject) -> str:
    active_instance_id = str(project.metadata.get("active_instance_id", ""))
    if active_instance_id and _get_instance(project, active_instance_id) is not None:
        return active_instance_id
    if not project.assembly.instances:
        project.metadata["active_instance_id"] = ""
        return ""
    instance = project.assembly.instances[0]
    project.metadata["active_instance_id"] = instance.id
    return instance.id


def set_active_instance(project: EngineeringProject, instance_id: str) -> EngineeringProject:
    instance = _require_instance(project, instance_id)
    project.metadata["active_instance_id"] = instance.id
    project.metadata["active_part_id"] = instance.part_id
    return project


def create_unique_instance_id(project: EngineeringProject, base_id: str = "inst") -> str:
    existing_ids = {instance.id for instance in project.assembly.instances}
    index = 1
    while True:
        candidate = f"{base_id}_{index}"
        if candidate not in existing_ids:
            return candidate
        index += 1


def add_instance(
    project: EngineeringProject,
    part_id: str,
    name: str = "",
    tx: float = 0.0,
    ty: float = 0.0,
    make_active: bool = True,
) -> EngineeringProject:
    if project.get_part_by_id(part_id) is None:
        raise ValueError(f"Unknown part id: {part_id}")
    instance_name = name.strip() if name else ""
    if not instance_name:
        instance_name = f"实例 {len(project.assembly.instances) + 1}"
    instance = PartInstance(
        id=create_unique_instance_id(project),
        name=instance_name,
        part_id=part_id,
        translation_x=float(tx),
        translation_y=float(ty),
        rotation_degrees=0.0,
    )
    project.assembly.instances.append(instance)
    if make_active:
        project.metadata["active_instance_id"] = instance.id
        project.metadata["active_part_id"] = instance.part_id
    project.validate_references()
    return project


def rename_instance(project: EngineeringProject, instance_id: str, new_name: str) -> EngineeringProject:
    instance = _require_instance(project, instance_id)
    name = new_name.strip() if new_name else ""
    if not name:
        raise ValueError("new_name must not be empty")
    instance.name = name
    return project


def move_instance(project: EngineeringProject, instance_id: str, tx: float, ty: float) -> EngineeringProject:
    instance = _require_instance(project, instance_id)
    instance.translation_x = float(tx)
    instance.translation_y = float(ty)
    return project


def move_instance_by_delta(
    project: EngineeringProject,
    instance_id: str,
    dx: float,
    dy: float,
) -> EngineeringProject:
    instance = _require_instance(project, instance_id)
    instance.translation_x += float(dx)
    instance.translation_y += float(dy)
    return project


def move_instance_reference_point_to(
    project: EngineeringProject,
    instance_id: str,
    local_x: float,
    local_y: float,
    target_x: float,
    target_y: float,
) -> EngineeringProject:
    instance = _require_instance(project, instance_id)
    instance.translation_x = float(target_x) - float(local_x)
    instance.translation_y = float(target_y) - float(local_y)
    return project


def delete_instance(project: EngineeringProject, instance_id: str) -> EngineeringProject:
    _require_instance(project, instance_id)
    project.assembly.instances = [
        instance for instance in project.assembly.instances if instance.id != instance_id
    ]
    if project.metadata.get("active_instance_id") == instance_id:
        if project.assembly.instances:
            instance = project.assembly.instances[0]
            project.metadata["active_instance_id"] = instance.id
            project.metadata["active_part_id"] = instance.part_id
        else:
            project.metadata["active_instance_id"] = ""
    project.validate_references()
    return project


def get_active_instance_transform(project: EngineeringProject) -> tuple[float, float]:
    active_instance_id = get_active_instance_id(project)
    if not active_instance_id:
        return 0.0, 0.0
    instance = _require_instance(project, active_instance_id)
    return instance.translation_x, instance.translation_y


def _get_instance(project: EngineeringProject, instance_id: str) -> PartInstance | None:
    for instance in project.assembly.instances:
        if instance.id == instance_id:
            return instance
    return None


def _require_instance(project: EngineeringProject, instance_id: str) -> PartInstance:
    instance = _get_instance(project, instance_id)
    if instance is None:
        raise ValueError(f"Unknown assembly instance id: {instance_id}")
    return instance
