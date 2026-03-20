from __future__ import annotations

from pathlib import Path


def ensure_screenshot(
    output_dir: Path,
    screenshot_path: Path | None = None,
    app_name: str | None = None,
) -> Path:
    if screenshot_path is not None:
        return screenshot_path

    output_dir.mkdir(parents=True, exist_ok=True)
    target = output_dir / "screenshot.png"
    if app_name is not None:
        from app_automate.builder.window_capture import capture_app_window

        capture_app_window(app_name, target)
        return target
    from app_automate.vision.screenshots import capture_main_display

    capture_main_display(target)
    return target
