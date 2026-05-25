from dataclasses import dataclass, asdict


@dataclass
class Material:
    id: int
    name: str
    young_modulus: float
    poisson_ratio: float
    thickness: float
    plane_mode: str = "stress"
    color: str | None = None

    def __post_init__(self) -> None:
        if self.color is None or str(self.color).strip() == "":
            self.color = self._default_color_by_id(self.id)
        else:
            self.color = str(self.color).strip()

        if self.young_modulus <= 0:
            raise ValueError("Young modulus must be greater than zero")
        if self.thickness <= 0:
            raise ValueError("Thickness must be greater than zero")
        if not (-1.0 <= self.poisson_ratio <= 0.5):
            raise ValueError("Poisson ratio must be between -1 and 0.5")
        if self.plane_mode != "stress":
            raise ValueError("Plane mode must be stress")

    @staticmethod
    def _default_color_by_id(material_id: int) -> str:
        palette = [
            "#8FB7D8",  # 蓝灰
            "#9BC7AA",  # 绿灰
            "#D6B37A",  # 橙灰
            "#B7A1D8",  # 紫灰
            "#D69A9A",  # 红灰
            "#8FC9C5",  # 青灰
            "#C8BE84",  # 黄灰
            "#AEB8C2",  # 中性灰
        ]
        try:
            index = max(int(material_id) - 1, 0) % len(palette)
        except Exception:
            index = 0
        return palette[index]

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "Material":
        return Material(**data)
