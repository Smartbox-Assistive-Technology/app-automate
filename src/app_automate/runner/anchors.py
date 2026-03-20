from __future__ import annotations

from pathlib import Path

from app_automate.vision.matching import MatchResult, match_template


def locate_anchor(
    template_path: Path,
    screenshot_path: Path,
    *,
    threshold: float = 0.8,
) -> MatchResult:
    return match_template(screenshot_path, template_path, threshold=threshold)
