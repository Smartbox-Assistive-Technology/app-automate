from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw
from pydantic import BaseModel, Field

from app_automate.builder.anchor_crop import crop_anchor
from app_automate.builder.capture import ensure_screenshot
from app_automate.builder.grid import render_grid_overlay
from app_automate.builder.llm_mapper import prepare_mapping_request, run_mapping_llm
from app_automate.builder.models import CropBox, MappingAnchor, MappingResult
from app_automate.config.models import (
    AnchorDefinition,
    Anchors,
    AppProfile,
    Baseline,
    ElementDefinition,
    LayoutMode,
)
from app_automate.config.settings import load_settings
from app_automate.config.validation import save_profile
from app_automate.vision.matching import match_template, match_template_stats


class AnchorCandidateReview(BaseModel):
    anchor_id: str
    crop_box: CropBox
    confidence: float
    second_best_confidence: float
    uniqueness_gap: float
    candidate_count: int
    texture_score: float
    edge_density: float
    quality_score: float
    valid: bool
    reason: str = ""


class AnchorReviewReport(BaseModel):
    primary_candidates: list[AnchorCandidateReview] = Field(default_factory=list)
    selected_primary: AnchorCandidateReview
    secondary_candidates: list[AnchorCandidateReview] = Field(default_factory=list)
    selected_secondary: AnchorCandidateReview | None = None


@dataclass(slots=True)
class TrainingBundle:
    screenshot_path: Path
    grid_path: Path
    prompt_path: Path
    llm_output_path: Path | None = None
    profile_path: Path | None = None
    review_path: Path | None = None
    review_image_path: Path | None = None


def create_training_bundle(
    *,
    output_dir: Path,
    screenshot_path: Path | None = None,
    app_name: str | None = None,
    settings_path: Path | None = None,
    grid_size: int | None = None,
    run_llm: bool = True,
) -> TrainingBundle:
    output_dir.mkdir(parents=True, exist_ok=True)
    for path in output_dir.glob("mapping_output.attempt-*.json"):
        path.unlink(missing_ok=True)
    for path in output_dir.glob("mapping_error.attempt-*.txt"):
        path.unlink(missing_ok=True)
    (output_dir / "anchor_primary.png").unlink(missing_ok=True)
    (output_dir / "anchor_secondary.png").unlink(missing_ok=True)
    (output_dir / "anchor_review.json").unlink(missing_ok=True)
    (output_dir / "anchor_review.png").unlink(missing_ok=True)
    (output_dir / "mapping_output.json").unlink(missing_ok=True)
    (output_dir / "mapping_error.txt").unlink(missing_ok=True)
    (output_dir / "profile.json").unlink(missing_ok=True)
    settings = load_settings(settings_path)
    effective_grid_size = grid_size or settings.builder.grid_size

    screenshot = ensure_screenshot(
        output_dir,
        screenshot_path=screenshot_path,
        app_name=app_name,
    )
    with Image.open(screenshot) as image:
        image_width, image_height = image.size

    grid_path = render_grid_overlay(
        screenshot,
        output_dir / "grid.png",
        grid_size=effective_grid_size,
    )
    prompt_path = output_dir / "mapping_request.json"
    prompt_path.write_text(
        json.dumps(
            prepare_mapping_request(
                grid_path,
                app_name=app_name,
                image_width=image_width,
                image_height=image_height,
                grid_size=effective_grid_size,
            ),
            indent=2,
        )
    )

    bundle = TrainingBundle(
        screenshot_path=screenshot,
        grid_path=grid_path,
        prompt_path=prompt_path,
    )
    if not run_llm:
        return bundle

    mapping_result, raw_output, profile, review_report = _generate_profile_with_retries(
        grid_path=grid_path,
        screenshot_path=screenshot,
        output_dir=output_dir,
        app_name=app_name,
        settings=settings,
        grid_size=effective_grid_size,
    )
    llm_output_path = output_dir / "mapping_output.json"
    llm_output_path.write_text(raw_output)
    profile_path = output_dir / "profile.json"
    save_profile(profile, profile_path)
    review_path = output_dir / "anchor_review.json"
    review_path.write_text(json.dumps(review_report.model_dump(mode="json"), indent=2))
    review_image_path = output_dir / "anchor_review.png"
    _write_anchor_review_overlay(
        screenshot_path=screenshot,
        output_path=review_image_path,
        report=review_report,
    )

    bundle.llm_output_path = llm_output_path
    bundle.profile_path = profile_path
    bundle.review_path = review_path
    bundle.review_image_path = review_image_path
    return bundle


def _generate_profile_with_retries(
    *,
    grid_path: Path,
    screenshot_path: Path,
    output_dir: Path,
    app_name: str | None,
    settings: Any,
    grid_size: int,
) -> tuple[MappingResult, str, AppProfile, AnchorReviewReport]:
    feedback: str | None = None
    last_error: Exception | None = None

    for attempt in range(1, settings.llm.max_attempts + 1):
        raw_output = ""
        try:
            mapping_result, raw_output = run_mapping_llm(
                grid_path,
                app_name=app_name,
                settings=settings,
                grid_size=grid_size,
                feedback=feedback,
            )
            (output_dir / f"mapping_output.attempt-{attempt}.json").write_text(
                raw_output
            )
            if app_name is not None:
                mapping_result = mapping_result.model_copy(
                    update={"app_name": app_name}
                )
            profile, review_report = build_profile_from_mapping_result(
                mapping_result,
                screenshot_path=screenshot_path,
                output_dir=output_dir,
                confidence_threshold=settings.builder.anchor_confidence_threshold,
            )
            return mapping_result, raw_output, profile, review_report
        except Exception as exc:
            last_error = exc
            feedback = str(exc)
            (output_dir / f"mapping_error.attempt-{attempt}.txt").write_text(str(exc))
            if raw_output:
                (output_dir / f"mapping_output.attempt-{attempt}.json").write_text(
                    raw_output
                )

    error_path = output_dir / "mapping_error.txt"
    if last_error is not None:
        error_path.write_text(str(last_error))
    raise RuntimeError(
        f"LLM mapping failed after retries: {last_error}. "
        f"See {error_path} for the last error."
    ) from last_error


def build_profile_from_mapping_result(
    mapping_result: MappingResult,
    *,
    screenshot_path: Path,
    output_dir: Path,
    confidence_threshold: float,
) -> tuple[AppProfile, AnchorReviewReport]:
    with Image.open(screenshot_path) as image:
        image_width, image_height = image.size

    requires_secondary_anchor = _requires_secondary_anchor(mapping_result)
    selected_primary, primary_candidates = _select_anchor_candidate(
        role="primary",
        screenshot_path=screenshot_path,
        output_dir=output_dir,
        image_width=image_width,
        image_height=image_height,
        threshold=confidence_threshold,
        preferred_anchor=mapping_result.primary_anchor,
        alternate_anchors=mapping_result.primary_anchor_candidates,
    )
    crop_anchor_from_mapping(
        screenshot_path,
        output_dir / "anchor_primary.png",
        selected_primary,
    )

    secondary_definition = None
    selected_secondary = None
    secondary_candidates: list[AnchorCandidateReview] = []
    if requires_secondary_anchor and mapping_result.secondary_anchor is None:
        raise RuntimeError(
            "secondary anchor is required for top_right, bottom_right, "
            "or center_scaled elements"
        )
    if requires_secondary_anchor and mapping_result.secondary_anchor is not None:
        selected_secondary, secondary_candidates = _select_anchor_candidate(
            role="secondary",
            screenshot_path=screenshot_path,
            output_dir=output_dir,
            image_width=image_width,
            image_height=image_height,
            threshold=confidence_threshold,
            preferred_anchor=mapping_result.secondary_anchor,
            alternate_anchors=mapping_result.secondary_anchor_candidates,
        )
        crop_anchor_from_mapping(
            screenshot_path,
            output_dir / "anchor_secondary.png",
            selected_secondary,
        )
        secondary_definition = AnchorDefinition(
            id=selected_secondary.id,
            path="anchor_secondary.png",
            x=selected_secondary.crop_box.x,
            y=selected_secondary.crop_box.y,
            confidence_threshold=confidence_threshold,
        )
    else:
        (output_dir / "anchor_secondary.png").unlink(missing_ok=True)

    primary_box = selected_primary.crop_box
    elements = {
        element.id: ElementDefinition(
            label=element.label,
            aliases=element.aliases,
            rel_x=_rel_x(element, selected_primary, selected_secondary),
            rel_y=_rel_y(element, selected_primary, selected_secondary),
            layout=element.layout,
            action=element.action,
        )
        for element in mapping_result.elements
    }

    profile = AppProfile(
        profile_id=_slugify(mapping_result.app_name),
        app_name=mapping_result.app_name,
        notes=mapping_result.notes,
        baseline=Baseline(width=image_width, height=image_height),
        anchors=Anchors(
            primary=AnchorDefinition(
                id=selected_primary.id,
                path="anchor_primary.png",
                x=primary_box.x,
                y=primary_box.y,
                confidence_threshold=confidence_threshold,
            ),
            secondary=secondary_definition,
        ),
        elements=elements,
    )
    report = AnchorReviewReport(
        primary_candidates=primary_candidates,
        selected_primary=_selected_candidate(
            primary_candidates,
            anchor_id=selected_primary.id,
            crop_box=selected_primary.crop_box,
        ),
        secondary_candidates=secondary_candidates,
        selected_secondary=(
            _selected_candidate(
                secondary_candidates,
                anchor_id=selected_secondary.id,
                crop_box=selected_secondary.crop_box,
            )
            if selected_secondary is not None
            else None
        ),
    )
    return profile, report


def rebuild_profile_with_anchor_overrides(
    *,
    screenshot_path: Path,
    output_dir: Path,
    settings_path: Path | None,
    primary_crop: CropBox | None,
    secondary_crop: CropBox | None,
) -> tuple[Path, Path, Path]:
    settings = load_settings(settings_path)
    llm_output_path = output_dir / "mapping_output.json"
    if not llm_output_path.exists():
        raise FileNotFoundError(f"missing mapping output: {llm_output_path}")

    mapping_result = MappingResult.model_validate_json(llm_output_path.read_text())
    if primary_crop is not None:
        mapping_result = mapping_result.model_copy(
            update={
                "primary_anchor": mapping_result.primary_anchor.model_copy(
                    update={"crop_box": primary_crop}
                )
            }
        )
    if secondary_crop is not None:
        if mapping_result.secondary_anchor is None:
            raise RuntimeError("mapping output does not contain a secondary anchor")
        mapping_result = mapping_result.model_copy(
            update={
                "secondary_anchor": mapping_result.secondary_anchor.model_copy(
                    update={"crop_box": secondary_crop}
                )
            }
        )

    profile, review_report = build_profile_from_mapping_result(
        mapping_result,
        screenshot_path=screenshot_path,
        output_dir=output_dir,
        confidence_threshold=settings.builder.anchor_confidence_threshold,
    )
    review_path = output_dir / "anchor_review.json"
    review_path.write_text(json.dumps(review_report.model_dump(mode="json"), indent=2))
    review_image_path = output_dir / "anchor_review.png"
    _write_anchor_review_overlay(
        screenshot_path=screenshot_path,
        output_path=review_image_path,
        report=review_report,
    )
    profile_path = output_dir / "profile.json"
    save_profile(profile, profile_path)
    return profile_path, review_path, review_image_path


def mapping_result_to_profile(
    mapping_result: MappingResult,
    *,
    screenshot_path: Path,
    output_dir: Path,
    confidence_threshold: float,
) -> AppProfile:
    profile, _ = build_profile_from_mapping_result(
        mapping_result,
        screenshot_path=screenshot_path,
        output_dir=output_dir,
        confidence_threshold=confidence_threshold,
    )
    return profile


def crop_anchor_from_mapping(
    screenshot_path: Path,
    output_path: Path,
    anchor: MappingAnchor,
) -> Path:
    crop_box = anchor.crop_box
    return crop_anchor(
        screenshot_path,
        output_path,
        x=crop_box.x,
        y=crop_box.y,
        width=crop_box.width,
        height=crop_box.height,
    )


def _validate_crop_box(crop_box: CropBox, image_width: int, image_height: int) -> None:
    if crop_box.x + crop_box.width > image_width:
        raise RuntimeError("anchor crop box exceeds screenshot width")
    if crop_box.y + crop_box.height > image_height:
        raise RuntimeError("anchor crop box exceeds screenshot height")
    if crop_box.width > image_width * 0.35 or crop_box.height > image_height * 0.35:
        raise RuntimeError(
            "anchor crop box is too large; anchor must be a tighter crop"
        )


def _select_anchor_candidate(
    *,
    role: str,
    screenshot_path: Path,
    output_dir: Path,
    image_width: int,
    image_height: int,
    threshold: float,
    preferred_anchor: MappingAnchor,
    alternate_anchors: list[MappingAnchor],
) -> tuple[MappingAnchor, list[AnchorCandidateReview]]:
    candidates = _dedupe_anchor_candidates([preferred_anchor, *alternate_anchors])
    reviews: list[tuple[MappingAnchor, AnchorCandidateReview]] = []

    for index, anchor in enumerate(candidates):
        review = _evaluate_anchor_candidate(
            role=role,
            anchor=anchor,
            screenshot_path=screenshot_path,
            output_dir=output_dir,
            candidate_index=index,
            image_width=image_width,
            image_height=image_height,
            threshold=threshold,
        )
        reviews.append((anchor, review))

    ranked = sorted(
        reviews,
        key=lambda item: (
            item[1].valid,
            item[1].quality_score,
            item[1].confidence,
            item[1].uniqueness_gap,
        ),
        reverse=True,
    )
    if not ranked or not ranked[0][1].valid:
        reasons = "; ".join(
            f"{review.anchor_id}: {review.reason}" for _, review in ranked[:3]
        )
        raise RuntimeError(f"no valid {role} anchor candidates: {reasons}")
    return ranked[0][0], [review for _, review in ranked]


def _evaluate_anchor_candidate(
    *,
    role: str,
    anchor: MappingAnchor,
    screenshot_path: Path,
    output_dir: Path,
    candidate_index: int,
    image_width: int,
    image_height: int,
    threshold: float,
) -> AnchorCandidateReview:
    try:
        _validate_crop_box(anchor.crop_box, image_width, image_height)
    except Exception as exc:
        return AnchorCandidateReview(
            anchor_id=anchor.id,
            crop_box=anchor.crop_box,
            confidence=0.0,
            second_best_confidence=0.0,
            uniqueness_gap=0.0,
            candidate_count=0,
            texture_score=0.0,
            edge_density=0.0,
            quality_score=0.0,
            valid=False,
            reason=str(exc),
        )

    anchor_path = output_dir / f".anchor_eval_{role}_{candidate_index}.png"
    crop_anchor_from_mapping(screenshot_path, anchor_path, anchor)
    try:
        match = match_template(screenshot_path, anchor_path, threshold=threshold)
        stats = match_template_stats(screenshot_path, anchor_path, threshold=threshold)
    finally:
        anchor_path.unlink(missing_ok=True)

    valid = True
    reason = ""
    if match.x != anchor.crop_box.x or match.y != anchor.crop_box.y:
        valid = False
        reason = (
            f"best match moved to {match.x},{match.y}; expected "
            f"{anchor.crop_box.x},{anchor.crop_box.y}"
        )
    elif stats.candidate_count > 1:
        valid = False
        reason = (
            f"not unique enough: {stats.candidate_count} matches >= {threshold:.2f}"
        )
    elif stats.uniqueness_gap < 0.05:
        valid = False
        reason = f"uniqueness gap {stats.uniqueness_gap:.3f} is too small"

    return AnchorCandidateReview(
        anchor_id=anchor.id,
        crop_box=anchor.crop_box,
        confidence=stats.confidence,
        second_best_confidence=stats.second_best_confidence,
        uniqueness_gap=stats.uniqueness_gap,
        candidate_count=stats.candidate_count,
        texture_score=stats.texture_score,
        edge_density=stats.edge_density,
        quality_score=stats.quality_score,
        valid=valid,
        reason=reason,
    )


def _dedupe_anchor_candidates(
    anchors: list[MappingAnchor],
) -> list[MappingAnchor]:
    seen: set[tuple[str, int, int, int, int]] = set()
    deduped: list[MappingAnchor] = []
    for anchor in anchors:
        key = (
            anchor.id,
            anchor.crop_box.x,
            anchor.crop_box.y,
            anchor.crop_box.width,
            anchor.crop_box.height,
        )
        if key in seen:
            continue
        seen.add(key)
        deduped.append(anchor)
    return deduped


def _selected_candidate(
    candidates: list[AnchorCandidateReview],
    *,
    anchor_id: str,
    crop_box: CropBox,
) -> AnchorCandidateReview:
    for candidate in candidates:
        if candidate.anchor_id != anchor_id:
            continue
        if candidate.crop_box == crop_box:
            return candidate
    raise RuntimeError(f"selected anchor not found in review candidates: {anchor_id}")


def _write_anchor_review_overlay(
    *,
    screenshot_path: Path,
    output_path: Path,
    report: AnchorReviewReport,
) -> Path:
    image = Image.open(screenshot_path).convert("RGB")
    draw = ImageDraw.Draw(image)
    _draw_anchor_candidates(
        draw,
        report.primary_candidates,
        selected=report.selected_primary,
        prefix="P",
        outline="cyan",
    )
    if report.selected_secondary is not None:
        _draw_anchor_candidates(
            draw,
            report.secondary_candidates,
            selected=report.selected_secondary,
            prefix="S",
            outline="orange",
        )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    image.save(output_path)
    return output_path


def _draw_anchor_candidates(
    draw: ImageDraw.ImageDraw,
    candidates: list[AnchorCandidateReview],
    *,
    selected: AnchorCandidateReview,
    prefix: str,
    outline: str,
) -> None:
    for index, candidate in enumerate(candidates, start=1):
        crop_box = candidate.crop_box
        color = "lime" if candidate == selected else outline
        draw.rectangle(
            (
                crop_box.x,
                crop_box.y,
                crop_box.x + crop_box.width,
                crop_box.y + crop_box.height,
            ),
            outline=color,
            width=3,
        )
        status = "*" if candidate == selected else ""
        label = (
            f"{prefix}{index}{status} {candidate.anchor_id} "
            f"{candidate.quality_score:.1f}"
        )
        draw.text((crop_box.x + 4, max(crop_box.y - 14, 0)), label, fill=color)


def _requires_secondary_anchor(mapping_result: MappingResult) -> bool:
    return any(
        element.layout
        in {
            LayoutMode.TOP_RIGHT,
            LayoutMode.BOTTOM_RIGHT,
            LayoutMode.CENTER_SCALED,
        }
        for element in mapping_result.elements
    )


def _rel_x(
    element: Any,
    primary_anchor: MappingAnchor,
    secondary_anchor: MappingAnchor | None,
) -> float:
    if element.layout.name in {"FIXED_FROM_PRIMARY", "CENTER_SCALED"}:
        return round(element.x - primary_anchor.crop_box.x, 2)
    if secondary_anchor is None:
        raise RuntimeError(f"{element.id} requires a secondary anchor")
    return round(element.x - secondary_anchor.crop_box.x, 2)


def _rel_y(
    element: Any,
    primary_anchor: MappingAnchor,
    secondary_anchor: MappingAnchor | None,
) -> float:
    if element.layout.name in {"FIXED_FROM_PRIMARY", "CENTER_SCALED"}:
        return round(element.y - primary_anchor.crop_box.y, 2)
    if secondary_anchor is None:
        raise RuntimeError(f"{element.id} requires a secondary anchor")
    if element.layout.name == "TOP_RIGHT":
        return round(element.y - primary_anchor.crop_box.y, 2)
    return round(element.y - secondary_anchor.crop_box.y, 2)


def _slugify(value: str) -> str:
    return "-".join(value.lower().split())
