from __future__ import annotations

import platform
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


class CheckRegion(BaseModel):
    path: str
    x: float
    y: float
    confidence_threshold: float = Field(default=0.9, ge=0.0, le=1.0)
    required: bool = True


class StateSignature(BaseModel):
    check_regions: list[CheckRegion] = Field(default_factory=list)
    description: str = ""


class AppState(BaseModel):
    id: str
    signature: StateSignature | None = None
    anchors: Anchors
    elements: dict[str, ElementDefinition]

    @model_validator(mode="after")
    def validate_secondary_anchor(self) -> "AppState":
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


class AppProfile(BaseModel):
    model_config = ConfigDict(extra="forbid")

    profile_id: str
    app_name: str
    platform_hint: str = "windows" if platform.system() == "Windows" else "macos"
    notes: str = ""
    baseline: Baseline
    anchors: Anchors | None = None
    elements: dict[str, ElementDefinition] = Field(default_factory=dict)
    states: dict[str, AppState] = Field(default_factory=dict)
    default_state: str = "default"

    @model_validator(mode="after")
    def validate_profile_structure(self) -> "AppProfile":
        has_legacy_elements = bool(self.elements)
        has_states = bool(self.states)

        if not has_legacy_elements and not has_states:
            raise ValueError("profile must have either elements or states defined")

        if has_legacy_elements and self.anchors is None:
            raise ValueError(
                "profile with top-level elements must have anchors defined"
            )

        if has_legacy_elements and has_states:
            raise ValueError(
                "profile cannot have both top-level elements and states; "
                "migrate to states-only"
            )

        if has_states and self.default_state not in self.states:
            raise ValueError(
                f"default_state '{self.default_state}' not found in states"
            )

        return self

    @model_validator(mode="after")
    def validate_secondary_anchor(self) -> "AppProfile":
        if self.anchors is not None:
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

    def get_state(self, state_id: str | None = None) -> AppState | None:
        if not self.states:
            return None
        target = state_id or self.default_state
        return self.states.get(target)

    def get_active_state(
        self, state_matches: dict[str, bool] | None = None
    ) -> AppState | None:
        if not self.states:
            return None
        if state_matches is None:
            return self.states.get(self.default_state)
        for state_id, matches in state_matches.items():
            if matches and state_id in self.states:
                return self.states[state_id]
        return self.states.get(self.default_state)
