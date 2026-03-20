from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from pydantic import BaseModel

from app_automate.config.models import AppProfile
from app_automate.runner.anchors import locate_anchor
from app_automate.runner.resolver import resolve_element_position
from app_automate.runner.transform import compute_transform
from app_automate.vision.screenshots import capture_main_display_temp


@dataclass(slots=True)
class RuntimeContext:
    profile: AppProfile
    live_primary: tuple[float, float]
    live_secondary: tuple[float, float] | None = None
    screenshot_path: Path | None = None
    primary_confidence: float | None = None
    secondary_confidence: float | None = None


class ResolvedCommand(BaseModel):
    element_id: str
    label: str
    action: str
    x: float
    y: float
    layout: str


class AnchorDetectionResult(BaseModel):
    screenshot_path: str
    primary: dict[str, float]
    secondary: dict[str, float] | None = None


def detect_runtime_context(
    *,
    profile: AppProfile,
    profile_dir: Path,
    screenshot_path: Path | None = None,
) -> RuntimeContext:
    active_screenshot = screenshot_path or capture_main_display_temp()

    primary_template = profile_dir / profile.anchors.primary.path
    primary_match = locate_anchor(
        primary_template,
        active_screenshot,
        threshold=profile.anchors.primary.confidence_threshold,
    )

    secondary_match = None
    if profile.anchors.secondary is not None:
        secondary_template = profile_dir / profile.anchors.secondary.path
        secondary_match = locate_anchor(
            secondary_template,
            active_screenshot,
            threshold=profile.anchors.secondary.confidence_threshold,
        )

    return RuntimeContext(
        profile=profile,
        live_primary=(float(primary_match.x), float(primary_match.y)),
        live_secondary=(
            (float(secondary_match.x), float(secondary_match.y))
            if secondary_match is not None
            else None
        ),
        screenshot_path=active_screenshot,
        primary_confidence=primary_match.confidence,
        secondary_confidence=(
            secondary_match.confidence if secondary_match is not None else None
        ),
    )


def summarize_detected_anchors(context: RuntimeContext) -> AnchorDetectionResult:
    payload = {
        "x": context.live_primary[0],
        "y": context.live_primary[1],
        "confidence": context.primary_confidence,
    }
    secondary = None
    if context.live_secondary is not None:
        secondary = {
            "x": context.live_secondary[0],
            "y": context.live_secondary[1],
            "confidence": context.secondary_confidence,
        }
    return AnchorDetectionResult(
        screenshot_path=str(context.screenshot_path) if context.screenshot_path else "",
        primary=payload,
        secondary=secondary,
    )


def resolve_element_id(command: str, profile: AppProfile) -> str:
    normalized = command.strip().casefold()
    for element_id, element in profile.elements.items():
        candidates = [element.label, *element.aliases, element_id]
        if any(normalized == candidate.casefold() for candidate in candidates):
            return element_id
    raise KeyError(f"no element matches command: {command}")


def dry_run_command(command: str, context: RuntimeContext) -> ResolvedCommand:
    element_id = resolve_element_id(command, context.profile)
    element = context.profile.elements[element_id]
    transform = compute_transform(
        context.profile,
        live_primary=context.live_primary,
        live_secondary=context.live_secondary,
    )
    x, y = resolve_element_position(element, transform)
    return ResolvedCommand(
        element_id=element_id,
        label=element.label,
        action=element.action.value,
        x=round(x, 2),
        y=round(y, 2),
        layout=element.layout.value,
    )
