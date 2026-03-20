from __future__ import annotations


def build_mapping_prompt(
    *,
    app_name: str | None,
    image_width: int,
    image_height: int,
    grid_size: int,
) -> str:
    app_line = f"Target app: {app_name}\n" if app_name else ""
    return (
        "You are identifying a stable interaction map for an application UI.\n\n"
        f"{app_line}"
        f"Image size: {image_width}x{image_height}\n"
        f"Grid size: {grid_size}px\n\n"
        "Tasks:\n"
        "1. Identify visible interactable elements that a user could click.\n"
        "2. For each element, return its id, label, aliases, absolute click point x/y, "
        "layout mode, and action.\n"
        "3. Propose one stable primary anchor and 2-3 alternate primary anchor "
        "candidates.\n"
        "4. Propose an optional secondary anchor only when needed, plus 1-2 alternate "
        "secondary anchor candidates.\n"
        "5. For each anchor, return a crop_box with absolute x/y/width/height.\n"
        "6. If both window-level controls and content tiles are visible, prefer "
        "window-level controls, title bars, mode switchers, toolbar icons, or other "
        "persistent chrome as anchors. Do not use content tiles as anchors unless "
        "there "
        "is no better stable choice.\n"
        "7. Anchor ids and element ids must be semantic snake_case names, not "
        "grid IDs.\n"
        "8. Prefer anchors that are visually unique, tight crops, and likely to remain "
        "stable while the app is resized. Prefer window chrome, logos, toolbar icons, "
        "or other fixed visuals over content tiles or repeated buttons.\n"
        "9. Anchor crop_box values must be tight around a single distinctive visual "
        "region, not a full-width toolbar or title bar. In most cases an anchor should "
        "be far smaller than 20 percent of the image width and 15 percent of the image "
        "height.\n"
        "10. Use only these layout values: fixed_from_primary, top_right, "
        "bottom_right, "
        "center_scaled.\n"
        "11. Use only click as the action.\n"
        "12. Set secondary_anchor to null unless at least one element uses top_right, "
        "bottom_right, or center_scaled.\n"
        "13. A bad anchor causes the profile to be rejected, so choose the tightest "
        "stable anchors you can.\n\n"
        "Return JSON matching the provided schema and do not wrap it in markdown."
    )
