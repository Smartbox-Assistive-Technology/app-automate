from __future__ import annotations

from app_automate.config.models import ElementDefinition, LayoutMode
from app_automate.runner.transform import Transform


def resolve_element_position(
    element: ElementDefinition,
    transform: Transform,
) -> tuple[float, float]:
    if element.layout is LayoutMode.FIXED_FROM_PRIMARY:
        return (
            transform.primary[0] + element.rel_x,
            transform.primary[1] + element.rel_y,
        )

    if transform.secondary is None:
        raise ValueError(f"{element.layout.value} requires a secondary anchor")

    if element.layout is LayoutMode.TOP_RIGHT:
        return (
            transform.secondary[0] + element.rel_x,
            transform.primary[1] + element.rel_y,
        )

    if element.layout is LayoutMode.BOTTOM_RIGHT:
        return (
            transform.secondary[0] + element.rel_x,
            transform.secondary[1] + element.rel_y,
        )

    if element.layout is LayoutMode.CENTER_SCALED:
        return (
            transform.primary[0] + (element.rel_x * transform.scale_x),
            transform.primary[1] + (element.rel_y * transform.scale_y),
        )

    raise ValueError(f"unsupported layout mode: {element.layout.value}")
