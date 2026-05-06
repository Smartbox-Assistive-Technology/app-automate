"""Draw a car in MS Paint using app-automate semantic profiles.

Usage:
    uv run --no-project python demos/paint_car.py

This script:
1. Opens MS Paint (or finds an existing window)
2. Builds a semantic profile from the live UIA tree
3. Uses the profile to click tools/colors and draw a car

The car is drawn using coordinate-based drag commands against the
canvas element found via UIA.
"""

from __future__ import annotations

import math
import subprocess
import time
from pathlib import Path

PROFILE_DIR = Path("examples/profiles/paint-demo")


def main() -> None:
    _ensure_paint_open()
    print("Bringing Paint to foreground...")
    from app_automate.builder.window_capture import activate_app

    activate_app("Paint")
    time.sleep(0.5)
    profile = _build_profile()
    _draw_car(profile)
    print("\nDone! Check your Paint window.")


def _ensure_paint_open() -> None:
    result = subprocess.run(
        ["tasklist", "/fo", "csv", "/nh"],
        capture_output=True,
        text=True,
    )
    for line in result.stdout.strip().split("\n"):
        if "mspaint" in line.lower():
            print("Paint is already open.")
            return
    print("Opening Paint...")
    subprocess.Popen(["mspaint.exe"])
    time.sleep(2)


def _build_profile() -> Path:
    from app_automate.builder.semantic_profile import build_semantic_profile

    print("Building semantic profile from Paint UIA tree...")
    path = build_semantic_profile(
        app_name="Paint",
        backend="uia",
        output_dir=PROFILE_DIR,
    )
    print(f"Profile saved to: {path}")
    return path


def _find_canvas(profile: object) -> tuple[str, dict[str, int]]:
    from app_automate.accessibility import windows_uia
    from app_automate.config.models import AppProfile

    assert isinstance(profile, AppProfile)

    all_elements = windows_uia.list_app_ui_elements(
        profile.app_name, max_depth=15, actionable_only=False
    )

    for el in all_elements:
        label = el.label.lower()
        if "canvas" in label:
            return el.path, _el_rect(el)

    toolbar_bottom = 0
    for el in all_elements:
        if el.class_name == "GroupControl" and el.label and "brush" in el.label.lower():
            toolbar_bottom = max(toolbar_bottom, (el.y or 0) + (el.height or 0))
        if el.class_name in ("MenuBarControl", "GroupControl") and (el.y or 0) < 200:
            toolbar_bottom = max(toolbar_bottom, (el.y or 0) + (el.height or 0))

    candidates = []
    for el in all_elements:
        if el.class_name != "PaneControl":
            continue
        if el.y is None or el.height is None or el.width is None:
            continue
        if el.y >= toolbar_bottom and el.height > 400 and el.width > 400:
            candidates.append(el)

    if candidates:
        best = max(candidates, key=lambda e: (e.height or 0) * (e.width or 0))
        return best.path, _el_rect(best)

    raise RuntimeError("Could not find Paint canvas in UIA tree")


def _el_rect(el: object) -> dict[str, int]:
    return {
        "x": getattr(el, "x", 0) or 0,
        "y": getattr(el, "y", 0) or 0,
        "width": getattr(el, "width", 0) or 0,
        "height": getattr(el, "height", 0) or 0,
    }


def _draw_car(profile_path: Path) -> None:
    from app_automate.config.validation import load_profile

    profile = load_profile(profile_path)
    elements = profile.semantic_elements
    print(f"\nProfile has {len(elements)} elements:")
    for eid, el in sorted(elements.items()):
        print(f"  {eid}: {el.label} [{el.action.value}]")

    print("\nLocating canvas...")
    canvas_path, canvas_rect = _find_canvas(profile)
    print(
        f"  Canvas: {canvas_path} at ({canvas_rect['x']}, {canvas_rect['y']}) "
        f"{canvas_rect['width']}x{canvas_rect['height']}"
    )

    print("Drawing a car...")
    _click_tool(profile, "brush", "pencil", "pen")
    _draw_car_shape(canvas_rect)


def _click_tool(profile: object, *tool_names: str) -> None:
    from app_automate.config.models import AppProfile
    from app_automate.runner.runtime import execute_semantic_command

    assert isinstance(profile, AppProfile)
    for name in tool_names:
        for eid, el in profile.semantic_elements.items():
            if name.lower() in el.label.lower():
                try:
                    execute_semantic_command(eid, profile)
                    print(f"  Selected tool: {el.label}")
                    return
                except Exception:
                    continue


def _draw_car_shape(canvas_rect: dict[str, int]) -> None:
    from app_automate.adapters.windows_input import WindowsInputAdapter

    adapter = WindowsInputAdapter()

    canvas_x = canvas_rect["x"] + canvas_rect["width"] / 2.0
    canvas_y = canvas_rect["y"] + canvas_rect["height"] / 2.0
    print(f"  Canvas center: ({canvas_x:.0f}, {canvas_y:.0f})")

    ox, oy = canvas_x, canvas_y
    scale = 1.0

    body_lines = [
        ((-150, 20), (150, 20)),
        ((150, 20), (150, -20)),
        ((150, -20), (100, -50)),
        ((100, -50), (-80, -50)),
        ((-80, -50), (-150, -20)),
        ((-150, -20), (-150, 20)),
    ]

    roof_lines = [
        ((-60, -50), (-30, -80)),
        ((-30, -80), (70, -80)),
        ((70, -80), (100, -50)),
    ]

    print("  Drawing body...")
    for (sx, sy), (ex, ey) in body_lines:
        adapter.drag(
            ox + sx * scale,
            oy + sy * scale,
            ox + ex * scale,
            oy + ey * scale,
        )
        time.sleep(0.1)

    print("  Drawing roof...")
    for (sx, sy), (ex, ey) in roof_lines:
        adapter.drag(
            ox + sx * scale,
            oy + sy * scale,
            ox + ex * scale,
            oy + ey * scale,
        )
        time.sleep(0.1)

    print("  Drawing wheels (circles)...")
    for cx_off, cy_off, r in [(-80, 20, 30), (80, 20, 30)]:
        wcx = ox + cx_off * scale
        wcy = oy + cy_off * scale
        radius = r * scale
        steps = 20
        points = []
        for i in range(steps + 1):
            angle = 2 * math.pi * i / steps
            px = wcx + radius * math.cos(angle)
            py = wcy + radius * math.sin(angle)
            points.append((px, py))

        adapter.click(points[0][0], points[0][1])
        time.sleep(0.05)
        for i in range(len(points) - 1):
            adapter.drag(
                points[i][0],
                points[i][1],
                points[i + 1][0],
                points[i + 1][1],
            )
            time.sleep(0.05)


if __name__ == "__main__":
    main()
