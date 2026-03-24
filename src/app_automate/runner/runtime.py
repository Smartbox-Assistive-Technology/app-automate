from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from app_automate.config.models import Anchors, AppProfile, ElementDefinition
from app_automate.runner.resolver import resolve_element_position
from app_automate.runner.transform import compute_transform_from_anchors


@dataclass(slots=True)
class RuntimeContext:
    profile: AppProfile
    live_primary: tuple[float, float]
    live_secondary: tuple[float, float] | None = None
    screenshot_path: Path | None = None
    primary_confidence: float | None = None
    secondary_confidence: float | None = None
    active_state_id: str | None = None
    anchors: Anchors | None = None
    elements: dict[str, ElementDefinition] | None = None


class ResolvedCommand(BaseModel):
    element_id: str
    label: str
    action: str
    x: float
    y: float
    layout: str
    state_id: str | None = None


class AnchorDetectionResult(BaseModel):
    screenshot_path: str
    primary: dict[str, float]
    secondary: dict[str, float] | None = None
    detected_state: str | None = None


class StateMatchResult(BaseModel):
    state_id: str
    matched: bool
    region_results: list[dict[str, Any]]


def detect_active_state(
    *,
    profile: AppProfile,
    profile_dir: Path,
    screenshot_path: Path,
) -> tuple[str | None, dict[str, StateMatchResult]]:
    from app_automate.runner.anchors import locate_anchor

    if not profile.states:
        return None, {}

    state_matches: dict[str, StateMatchResult] = {}

    for state_id, state in profile.states.items():
        if state.signature is None:
            state_matches[state_id] = StateMatchResult(
                state_id=state_id,
                matched=False,
                region_results=[],
            )
            continue

        region_results: list[dict[str, Any]] = []
        all_required_matched = True
        any_region_checked = False

        for region in state.signature.check_regions:
            template_path = profile_dir / region.path
            if not template_path.exists():
                region_results.append(
                    {
                        "path": region.path,
                        "matched": False,
                        "confidence": 0.0,
                        "error": "template not found",
                    }
                )
                if region.required:
                    all_required_matched = False
                continue

            any_region_checked = True
            try:
                match = locate_anchor(
                    template_path,
                    screenshot_path,
                    threshold=region.confidence_threshold,
                )
                match_x = getattr(match, "x", 0)
                match_y = getattr(match, "y", 0)
                match_conf = getattr(match, "confidence", 0.0)
                expected_x = abs(float(match_x) - region.x) < 5
                expected_y = abs(float(match_y) - region.y) < 5
                matched = expected_x and expected_y

                region_results.append(
                    {
                        "path": region.path,
                        "matched": matched,
                        "confidence": match_conf,
                        "expected": (region.x, region.y),
                        "actual": (float(match_x), float(match_y)),
                    }
                )

                if region.required and not matched:
                    all_required_matched = False
            except Exception as exc:
                region_results.append(
                    {
                        "path": region.path,
                        "matched": False,
                        "error": str(exc),
                    }
                )
                if region.required:
                    all_required_matched = False

        state_matched = any_region_checked and all_required_matched
        state_matches[state_id] = StateMatchResult(
            state_id=state_id,
            matched=state_matched,
            region_results=region_results,
        )

    for state_id, result in state_matches.items():
        if result.matched:
            return state_id, state_matches

    return profile.default_state, state_matches


def detect_runtime_context(
    *,
    profile: AppProfile,
    profile_dir: Path,
    screenshot_path: Path | None = None,
    state_id: str | None = None,
) -> RuntimeContext:
    from app_automate.runner.anchors import locate_anchor
    from app_automate.vision.screenshots import capture_main_display_temp

    active_screenshot = screenshot_path or capture_main_display_temp()

    detected_state_id = state_id
    if profile.states and detected_state_id is None:
        detected_state_id, _ = detect_active_state(
            profile=profile,
            profile_dir=profile_dir,
            screenshot_path=active_screenshot,
        )

    if profile.states and detected_state_id:
        active_state = profile.states.get(detected_state_id)
        if active_state is None:
            raise ValueError(f"state '{detected_state_id}' not found in profile")
        anchors = active_state.anchors
        elements = active_state.elements
    elif profile.anchors is not None:
        anchors = profile.anchors
        elements = profile.elements
    else:
        raise ValueError("profile has no valid anchors configuration")

    primary_template = profile_dir / anchors.primary.path
    primary_match = locate_anchor(
        primary_template,
        active_screenshot,
        threshold=anchors.primary.confidence_threshold,
    )

    secondary_match = None
    if anchors.secondary is not None:
        secondary_template = profile_dir / anchors.secondary.path
        secondary_match = locate_anchor(
            secondary_template,
            active_screenshot,
            threshold=anchors.secondary.confidence_threshold,
        )

    primary_x = getattr(primary_match, "x", 0)
    primary_y = getattr(primary_match, "y", 0)
    primary_conf = getattr(primary_match, "confidence", 0.0)
    secondary_x = 0
    secondary_y = 0
    secondary_conf = 0.0
    if secondary_match is not None:
        secondary_x = getattr(secondary_match, "x", 0)
        secondary_y = getattr(secondary_match, "y", 0)
        secondary_conf = getattr(secondary_match, "confidence", 0.0)

    return RuntimeContext(
        profile=profile,
        live_primary=(float(primary_x), float(primary_y)),
        live_secondary=(
            (float(secondary_x), float(secondary_y))
            if secondary_match is not None
            else None
        ),
        screenshot_path=active_screenshot,
        primary_confidence=primary_conf,
        secondary_confidence=(secondary_conf if secondary_match is not None else None),
        active_state_id=detected_state_id,
        anchors=anchors,
        elements=elements,
    )


def summarize_detected_anchors(context: RuntimeContext) -> AnchorDetectionResult:
    payload = {
        "x": context.live_primary[0],
        "y": context.live_primary[1],
        "confidence": context.primary_confidence or 0.0,
    }
    secondary = None
    if context.live_secondary is not None:
        secondary = {
            "x": context.live_secondary[0],
            "y": context.live_secondary[1],
            "confidence": context.secondary_confidence or 0.0,
        }
    return AnchorDetectionResult(
        screenshot_path=str(context.screenshot_path) if context.screenshot_path else "",
        primary=payload,
        secondary=secondary,
        detected_state=context.active_state_id,
    )


def resolve_element_id(command: str, context: RuntimeContext) -> str:
    normalized = command.strip().casefold()
    elements = context.elements or context.profile.elements
    for element_id, element in elements.items():
        candidates = [element.label, *element.aliases, element_id]
        if any(normalized == candidate.casefold() for candidate in candidates):
            return element_id
    raise KeyError(f"no element matches command: {command}")


def dry_run_command(command: str, context: RuntimeContext) -> ResolvedCommand:
    element_id = resolve_element_id(command, context)
    elements = context.elements or context.profile.elements
    element = elements[element_id]
    anchors = context.anchors or context.profile.anchors
    if anchors is None:
        raise ValueError("no anchors available for transform")
    transform = compute_transform_from_anchors(
        anchors,
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
        state_id=context.active_state_id,
    )
