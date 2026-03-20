from __future__ import annotations

from pathlib import Path

import numpy as np
from pydantic import BaseModel


class MatchResult(BaseModel):
    x: int
    y: int
    width: int
    height: int
    confidence: float


class MatchStats(BaseModel):
    confidence: float
    candidate_count: int
    second_best_confidence: float
    uniqueness_gap: float
    texture_score: float
    edge_density: float
    quality_score: float


def match_template(
    screenshot_path: Path,
    template_path: Path,
    *,
    threshold: float = 0.8,
) -> MatchResult:
    cv2 = _import_cv2()
    screenshot = cv2.imread(str(screenshot_path))
    template = cv2.imread(str(template_path))
    if screenshot is None or template is None:
        raise FileNotFoundError("unable to load screenshot or template image")

    result = cv2.matchTemplate(screenshot, template, cv2.TM_CCOEFF_NORMED)
    _, confidence, _, max_loc = cv2.minMaxLoc(result)
    if confidence < threshold:
        raise ValueError(
            f"template confidence {confidence:.3f} below threshold {threshold:.3f}"
        )

    height, width = template.shape[:2]
    return MatchResult(
        x=max_loc[0],
        y=max_loc[1],
        width=width,
        height=height,
        confidence=round(float(confidence), 4),
    )


def match_template_stats(
    screenshot_path: Path,
    template_path: Path,
    *,
    threshold: float,
) -> MatchStats:
    cv2 = _import_cv2()
    screenshot = cv2.imread(str(screenshot_path))
    template = cv2.imread(str(template_path))
    if screenshot is None or template is None:
        raise FileNotFoundError("unable to load screenshot or template image")

    result = cv2.matchTemplate(screenshot, template, cv2.TM_CCOEFF_NORMED)
    _, confidence, _, max_loc = cv2.minMaxLoc(result)
    mask = (result >= threshold).astype("uint8")
    candidate_count, _ = cv2.connectedComponents(mask)
    second_best_confidence = _second_best_confidence(result, max_loc, template.shape)
    uniqueness_gap = float(confidence) - second_best_confidence
    texture_score = _texture_score(template)
    edge_density = _edge_density(template)
    quality_score = _quality_score(
        confidence=float(confidence),
        uniqueness_gap=uniqueness_gap,
        texture_score=texture_score,
        edge_density=edge_density,
        candidate_count=max(candidate_count - 1, 0),
    )
    return MatchStats(
        confidence=round(float(confidence), 4),
        candidate_count=max(candidate_count - 1, 0),
        second_best_confidence=round(second_best_confidence, 4),
        uniqueness_gap=round(uniqueness_gap, 4),
        texture_score=round(texture_score, 4),
        edge_density=round(edge_density, 4),
        quality_score=round(quality_score, 2),
    )


def _second_best_confidence(
    result: np.ndarray,
    max_loc: tuple[int, int],
    template_shape: tuple[int, int, int],
) -> float:
    cv2 = _import_cv2()
    result_copy = result.copy()
    template_height, template_width = template_shape[:2]
    left = max(max_loc[0] - max(template_width // 2, 1), 0)
    top = max(max_loc[1] - max(template_height // 2, 1), 0)
    right = min(max_loc[0] + max(template_width // 2, 1) + 1, result_copy.shape[1])
    bottom = min(max_loc[1] + max(template_height // 2, 1) + 1, result_copy.shape[0])
    result_copy[top:bottom, left:right] = -1.0
    _, second_best_confidence, _, _ = cv2.minMaxLoc(result_copy)
    return max(float(second_best_confidence), 0.0)


def _texture_score(template: np.ndarray) -> float:
    cv2 = _import_cv2()
    gray = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY)
    return min(float(np.std(gray)) / 64.0, 1.0)


def _edge_density(template: np.ndarray) -> float:
    cv2 = _import_cv2()
    gray = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(gray, 100, 200)
    return min(float(np.mean(edges > 0)) / 0.2, 1.0)


def _quality_score(
    *,
    confidence: float,
    uniqueness_gap: float,
    texture_score: float,
    edge_density: float,
    candidate_count: int,
) -> float:
    base = (
        (confidence * 0.45)
        + (max(uniqueness_gap, 0.0) * 0.35)
        + (texture_score * 0.10)
        + (edge_density * 0.10)
    ) * 100.0
    repeated_penalty = max(candidate_count - 1, 0) * 15.0
    return max(base - repeated_penalty, 0.0)


def _import_cv2():
    import cv2

    return cv2
