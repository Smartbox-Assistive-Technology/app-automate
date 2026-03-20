from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

from app_automate.runner.runtime import ResolvedCommand, RuntimeContext


def draw_point_overlay(
    image_path: Path,
    output_path: Path,
    *,
    x: float,
    y: float,
    label: str,
) -> Path:
    image = Image.open(image_path).convert("RGB")
    draw = ImageDraw.Draw(image)
    radius = 12
    draw.ellipse(
        (x - radius, y - radius, x + radius, y + radius),
        outline="lime",
        width=3,
    )
    draw.text((x + 16, y - 10), label, fill="lime")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    image.save(output_path)
    return output_path


def draw_runtime_overlay(
    image_path: Path,
    output_path: Path,
    *,
    context: RuntimeContext,
    result: ResolvedCommand,
) -> Path:
    image = Image.open(image_path).convert("RGB")
    draw = ImageDraw.Draw(image)

    _draw_marker(
        draw,
        x=context.live_primary[0],
        y=context.live_primary[1],
        label=f"primary ({context.primary_confidence or 0:.3f})",
        color="cyan",
    )
    if context.live_secondary is not None:
        _draw_marker(
            draw,
            x=context.live_secondary[0],
            y=context.live_secondary[1],
            label=f"secondary ({context.secondary_confidence or 0:.3f})",
            color="orange",
        )
    _draw_marker(
        draw,
        x=result.x,
        y=result.y,
        label=f"target: {result.label}",
        color="lime",
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    image.save(output_path)
    return output_path


def crop_window_overlay(
    image_path: Path,
    output_path: Path,
    *,
    context: RuntimeContext,
) -> Path:
    image = Image.open(image_path).convert("RGB")
    left, top, right, bottom = infer_window_bounds(context)
    crop = image.crop((left, top, right, bottom))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    crop.save(output_path)
    return output_path


def infer_window_bounds(context: RuntimeContext) -> tuple[int, int, int, int]:
    baseline = context.profile.baseline
    primary = context.profile.anchors.primary

    left = context.live_primary[0] - primary.x
    top = context.live_primary[1] - primary.y

    if context.profile.anchors.secondary is None or context.live_secondary is None:
        return (
            round(left),
            round(top),
            round(left + baseline.width),
            round(top + baseline.height),
        )

    secondary = context.profile.anchors.secondary
    right = context.live_secondary[0] + (baseline.width - secondary.x)
    bottom = context.live_secondary[1] + (baseline.height - secondary.y)
    return round(left), round(top), round(right), round(bottom)


def _draw_marker(
    draw: ImageDraw.ImageDraw,
    *,
    x: float,
    y: float,
    label: str,
    color: str,
) -> None:
    radius = 12
    draw.ellipse(
        (x - radius, y - radius, x + radius, y + radius),
        outline=color,
        width=3,
    )
    draw.text((x + 16, y - 10), label, fill=color)
