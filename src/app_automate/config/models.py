from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, model_validator


class LayoutMode(str, Enum):
    FIXED_FROM_PRIMARY = "fixed_from_primary"
    TOP_RIGHT = "top_right"
    BOTTOM_RIGHT = "bottom_right"
    CENTER_SCALED = "center_scaled"


class ActionType(str, Enum):
    CLICK = "click"


class Baseline(BaseModel):
    width: int = Field(gt=0)
    height: int = Field(gt=0)


class AnchorDefinition(BaseModel):
    id: str
    path: str
    x: float
    y: float
    confidence_threshold: float = Field(default=0.85, ge=0.0, le=1.0)


class Anchors(BaseModel):
    primary: AnchorDefinition
    secondary: AnchorDefinition | None = None


class ElementDefinition(BaseModel):
    label: str
    aliases: list[str] = Field(default_factory=list)
    rel_x: float
    rel_y: float
    layout: LayoutMode
    action: ActionType = ActionType.CLICK


class AppProfile(BaseModel):
    model_config = ConfigDict(extra="forbid")

    profile_id: str
    app_name: str
    platform_hint: str = "macos"
    notes: str = ""
    baseline: Baseline
    anchors: Anchors
    elements: dict[str, ElementDefinition]

    @model_validator(mode="after")
    def validate_secondary_anchor(self) -> "AppProfile":
        uses_scaled_or_corner = any(
            element.layout
            in {
                LayoutMode.CENTER_SCALED,
                LayoutMode.TOP_RIGHT,
                LayoutMode.BOTTOM_RIGHT,
            }
            for element in self.elements.values()
        )
        if uses_scaled_or_corner and self.anchors.secondary is None:
            raise ValueError(
                "secondary anchor is required when using center_scaled, top_right, "
                "or bottom_right layouts"
            )
        return self
