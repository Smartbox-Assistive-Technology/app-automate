from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class UIElement:
    path: str
    class_name: str
    role: str | None
    subrole: str | None
    description: str | None
    title: str | None
    name: str | None
    x: int | None
    y: int | None
    width: int | None
    height: int | None
    enabled: bool | None
    depth: int
    child_count: int
    automation_id: str | None = None

    @property
    def label(self) -> str:
        for value in (self.title, self.name, self.description):
            if value:
                return value
        return self.class_name

    @property
    def actionable(self) -> bool:
        return False

    @property
    def has_bounds(self) -> bool:
        return (
            self.x is not None
            and self.y is not None
            and self.width is not None
            and self.height is not None
            and self.width > 0
            and self.height > 0
        )

    def as_dict(self) -> dict[str, object]:
        return {
            "path": self.path,
            "class_name": self.class_name,
            "role": self.role,
            "subrole": self.subrole,
            "description": self.description,
            "title": self.title,
            "name": self.name,
            "label": self.label,
            "automation_id": self.automation_id,
            "x": self.x,
            "y": self.y,
            "width": self.width,
            "height": self.height,
            "has_bounds": self.has_bounds,
            "enabled": self.enabled,
            "depth": self.depth,
            "child_count": self.child_count,
            "actionable": self.actionable,
        }
