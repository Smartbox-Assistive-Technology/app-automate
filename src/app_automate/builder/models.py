from __future__ import annotations

import re

from pydantic import BaseModel, Field, model_validator

from app_automate.config.models import ActionType, LayoutMode

GRID_ID_RE = re.compile(r"^r\d+c\d+$", re.IGNORECASE)
SNAKE_CASE_RE = re.compile(r"^[a-z][a-z0-9_]*$")
GENERIC_APP_NAMES = {"interaction map", "application", "app", "ui", "interface"}


class CropBox(BaseModel):
    x: int = Field(ge=0)
    y: int = Field(ge=0)
    width: int = Field(gt=0)
    height: int = Field(gt=0)


class MappingAnchor(BaseModel):
    id: str
    crop_box: CropBox

    @model_validator(mode="after")
    def validate_id(self) -> "MappingAnchor":
        if GRID_ID_RE.match(self.id) or not SNAKE_CASE_RE.match(self.id):
            raise ValueError("anchor ids must be semantic snake_case names")
        return self


class MappingElement(BaseModel):
    id: str
    label: str
    aliases: list[str] = Field(default_factory=list)
    x: float = Field(ge=0)
    y: float = Field(ge=0)
    layout: LayoutMode
    action: ActionType = ActionType.CLICK

    @model_validator(mode="after")
    def validate_id(self) -> "MappingElement":
        if GRID_ID_RE.match(self.id) or not SNAKE_CASE_RE.match(self.id):
            raise ValueError("element ids must be semantic snake_case names")
        return self


class CheckRegionMapping(BaseModel):
    id: str
    crop_box: CropBox
    required: bool = True

    @model_validator(mode="after")
    def validate_id(self) -> "CheckRegionMapping":
        if not SNAKE_CASE_RE.match(self.id):
            raise ValueError("check region ids must be snake_case names")
        return self


class StateSignatureMapping(BaseModel):
    description: str = ""
    check_regions: list[CheckRegionMapping] = Field(default_factory=list)


class StateMapping(BaseModel):
    id: str
    description: str = ""
    signature: StateSignatureMapping | None = None
    primary_anchor: MappingAnchor
    primary_anchor_candidates: list[MappingAnchor] = Field(default_factory=list)
    secondary_anchor: MappingAnchor | None = None
    secondary_anchor_candidates: list[MappingAnchor] = Field(default_factory=list)
    elements: list[MappingElement]

    @model_validator(mode="after")
    def validate_unique_ids(self) -> "StateMapping":
        if (
            self.secondary_anchor is not None
            and self.primary_anchor.id == self.secondary_anchor.id
        ):
            raise ValueError(
                "primary and secondary anchor ids must differ within a state"
            )
        ids = [element.id for element in self.elements]
        if len(ids) != len(set(ids)):
            raise ValueError("element ids must be unique within a state")
        return self


class MappingResult(BaseModel):
    app_name: str
    notes: str = ""
    primary_anchor: MappingAnchor
    primary_anchor_candidates: list[MappingAnchor] = Field(default_factory=list)
    secondary_anchor: MappingAnchor | None = None
    secondary_anchor_candidates: list[MappingAnchor] = Field(default_factory=list)
    elements: list[MappingElement]
    states: list[StateMapping] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_unique_ids(self) -> "MappingResult":
        if self.app_name.strip().lower() in GENERIC_APP_NAMES:
            raise ValueError("app_name is too generic")
        if (
            self.secondary_anchor is not None
            and self.primary_anchor.id == self.secondary_anchor.id
        ):
            raise ValueError("primary and secondary anchor ids must differ")
        ids = [element.id for element in self.elements]
        if len(ids) != len(set(ids)):
            raise ValueError("element ids must be unique")
        state_ids = [state.id for state in self.states]
        if len(state_ids) != len(set(state_ids)):
            raise ValueError("state ids must be unique")
        if self.states and self.elements:
            raise ValueError("profile cannot have both top-level elements and states")
        return self
