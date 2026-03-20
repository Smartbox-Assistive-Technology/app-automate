from __future__ import annotations

import platform
import subprocess
import time
from pathlib import Path

from PIL import Image


def capture_app_window(app_name: str, output_path: Path) -> Path:
    from app_automate.vision.screenshots import capture_main_display

    _activate_app(app_name)
    time.sleep(0.4)
    left, top, width, height = front_window_bounds(app_name)
    full_screen_path = output_path.parent / "screen.png"
    capture_main_display(full_screen_path)
    image = Image.open(full_screen_path)
    crop = image.crop((left, top, left + width, top + height))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    crop.save(output_path)
    return output_path


def front_window_bounds(app_name: str) -> tuple[int, int, int, int]:
    if platform.system() != "Darwin":
        raise RuntimeError("automatic app-window capture is currently macOS-only")

    position_raw = _osascript(
        'tell application "System Events" to tell process '
        f'"{app_name}" to get position of front window'
    )
    size_raw = _osascript(
        'tell application "System Events" to tell process '
        f'"{app_name}" to get size of front window'
    )
    left, top = _parse_pair(position_raw)
    width, height = _parse_pair(size_raw)
    return left, top, width, height


def _osascript(script: str) -> str:
    result = subprocess.run(
        ["osascript", "-e", script],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip())
    return result.stdout.strip()


def _activate_app(app_name: str) -> None:
    _osascript(f'tell application "{app_name}" to activate')


def _parse_pair(value: str) -> tuple[int, int]:
    parts = [part.strip() for part in value.split(",")]
    if len(parts) != 2:
        raise RuntimeError(f"unexpected window bounds response: {value}")
    return int(parts[0]), int(parts[1])
