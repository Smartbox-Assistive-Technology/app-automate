from __future__ import annotations

from dataclasses import dataclass

from app_automate.config.models import Anchors, AppProfile


@dataclass(slots=True)
class Transform:
    primary: tuple[float, float]
    secondary: tuple[float, float] | None
    scale_x: float
    scale_y: float


def compute_transform(
    profile: AppProfile,
    *,
    live_primary: tuple[float, float],
    live_secondary: tuple[float, float] | None,
) -> Transform:
    if profile.anchors is None:
        raise ValueError("profile has no anchors defined for legacy transform")
    return compute_transform_from_anchors(
        anchors=profile.anchors,
        live_primary=live_primary,
        live_secondary=live_secondary,
    )


def compute_transform_from_anchors(
    anchors: Anchors,
    *,
    live_primary: tuple[float, float],
    live_secondary: tuple[float, float] | None,
) -> Transform:
    baseline_primary = (anchors.primary.x, anchors.primary.y)

    if anchors.secondary is None or live_secondary is None:
        return Transform(
            primary=live_primary,
            secondary=live_secondary,
            scale_x=1.0,
            scale_y=1.0,
        )

    baseline_secondary = (
        anchors.secondary.x,
        anchors.secondary.y,
    )
    baseline_dx = baseline_secondary[0] - baseline_primary[0]
    baseline_dy = baseline_secondary[1] - baseline_primary[1]
    live_dx = live_secondary[0] - live_primary[0]
    live_dy = live_secondary[1] - live_primary[1]

    scale_x = live_dx / baseline_dx if baseline_dx else 1.0
    scale_y = live_dy / baseline_dy if baseline_dy else 1.0
    return Transform(
        primary=live_primary,
        secondary=live_secondary,
        scale_x=scale_x,
        scale_y=scale_y,
    )
