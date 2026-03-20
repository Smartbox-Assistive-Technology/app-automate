from __future__ import annotations

from pathlib import Path


def locate_anchor(
    template_path: Path,
    screenshot_path: Path,
    *,
    threshold: float = 0.8,
) -> object:
    from app_automate.vision.matching import match_template

    return match_template(screenshot_path, template_path, threshold=threshold)
