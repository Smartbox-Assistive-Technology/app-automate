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


def _click_tool(profile: object, name: str) -> None:
    from app_automate.accessibility import windows_uia
    from app_automate.adapters.windows_input import WindowsInputAdapter
    from app_automate.config.models import AppProfile

    assert isinstance(profile, AppProfile)
    name_lower = name.lower()

    exact_match = None
    partial_matches = []
    for eid, el in profile.semantic_elements.items():
        if el.label.lower() == name_lower:
            exact_match = el
            break
        if name_lower in el.label.lower():
            partial_matches.append(el)

    target_el = exact_match or (partial_matches[0] if partial_matches else None)
    if not target_el:
        print(f"  WARNING: Could not find tool matching: {name}")
        return

    print(f"  Trying: {target_el.label} (role={target_el.role})")
    matches = windows_uia.find_matching_elements(
        profile.app_name,
        contains=target_el.label,
        max_depth=15,
        actionable_only=False,
    )
    if not matches:
        print("    Not found via UIA")
        return
    target = matches[0]
    cx = (target.x or 0) + (target.width or 0) / 2.0
    cy = (target.y or 0) + (target.height or 0) / 2.0
    print(f"    Clicking at ({cx:.0f}, {cy:.0f})")
    adapter = WindowsInputAdapter()
    adapter.click(cx, cy)
    time.sleep(0.3)
    print(f"  Selected: {target_el.label}")


def _draw_car(profile_path: Path) -> None:
    from app_automate.adapters.windows_input import WindowsInputAdapter
    from app_automate.config.validation import load_profile

    profile = load_profile(profile_path)
    print(f"\nProfile has {len(profile.semantic_elements)} elements:")

    print("\nLocating canvas...")
    canvas_path, canvas_rect = _find_canvas(profile)
    print(
        f"  Canvas: {canvas_path} at ({canvas_rect['x']}, {canvas_rect['y']}) "
        f"{canvas_rect['width']}x{canvas_rect['height']}"
    )

    adapter = WindowsInputAdapter()
    ox = canvas_rect["x"] + canvas_rect["width"] / 2.0
    oy = canvas_rect["y"] + canvas_rect["height"] / 2.0
    scale = 1.0

    print("\nDrawing a car...")

    # Step 1: Draw closed body outline with brush
    print("  Step 1: Draw body outline with brush...")
    _click_tool(profile, "Brushes")
    time.sleep(1.0)

    body_lines = [
        ((-150, 20), (-150, -20)),
        ((-150, -20), (-80, -50)),
        ((-80, -50), (100, -50)),
        ((100, -50), (150, -20)),
        ((150, -20), (150, 20)),
        ((150, 20), (-150, 20)),
    ]

    roof_lines = [
        ((-60, -50), (-30, -80)),
        ((-30, -80), (70, -80)),
        ((70, -80), (100, -50)),
    ]

    for (sx, sy), (ex, ey) in body_lines:
        adapter.drag(
            ox + sx * scale,
            oy + sy * scale,
            ox + ex * scale,
            oy + ey * scale,
        )
        time.sleep(0.15)

    for (sx, sy), (ex, ey) in roof_lines:
        adapter.drag(
            ox + sx * scale,
            oy + sy * scale,
            ox + ex * scale,
            oy + ey * scale,
        )
        time.sleep(0.15)

    # Step 2: Fill body with red before adding wheels
    print("  Step 2: Fill body with red...")
    _click_tool(profile, "Fill")
    time.sleep(1.0)

    _click_tool(profile, "Red")
    time.sleep(1.0)

    fill_x = ox - 10 * scale
    fill_y = oy - 10 * scale
    print(f"    Fill clicking at ({fill_x:.0f}, {fill_y:.0f})")
    adapter.click(fill_x, fill_y)
    time.sleep(0.5)

    # Step 3: Draw wheels with oval shape
    print("  Step 3: Draw wheels with oval shape...")
    _click_tool(profile, "Oval")
    time.sleep(1.0)

    adapter.click(ox, oy)
    time.sleep(0.3)

    for cx_off, cy_off, r in [(-100, 25, 35), (100, 25, 35)]:
        wcx = ox + cx_off * scale
        wcy = oy + cy_off * scale
        radius = r * scale
        adapter.drag(
            wcx - radius,
            wcy - radius,
            wcx + radius,
            wcy + radius,
            duration=0.5,
        )
        time.sleep(0.5)

    # Step 4: Redraw bottom line over wheels
    print("  Step 4: Redraw bottom line over wheels...")
    _click_tool(profile, "Brushes")
    time.sleep(1.0)

    bottom_x1 = ox + (-150) * scale
    bottom_y1 = oy + 20 * scale
    bottom_x2 = ox + 150 * scale
    bottom_y2 = oy + 20 * scale
    print(
        f"    Bottom line ({bottom_x1:.0f},{bottom_y1:.0f})"
        f" -> ({bottom_x2:.0f},{bottom_y2:.0f})"
    )
    adapter.drag(bottom_x1, bottom_y1, bottom_x2, bottom_y2)
    time.sleep(0.3)


if __name__ == "__main__":
    main()
