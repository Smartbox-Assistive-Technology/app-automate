from __future__ import annotations

import json
from pathlib import Path

from PIL import Image, ImageDraw

from app_automate.config.validation import load_profile
from app_automate.runner.runtime import detect_runtime_context, dry_run_command


def test_detect_runtime_context_from_screenshot(tmp_path: Path) -> None:
    screen = Image.new("RGB", (240, 160), "black")
    draw = ImageDraw.Draw(screen)
    draw.rectangle((30, 20, 79, 39), fill="red")
    draw.rectangle((42, 24, 54, 35), fill="white")
    draw.rectangle((180, 120, 219, 149), fill="blue")
    draw.rectangle((190, 128, 207, 140), fill="yellow")

    screenshot_path = tmp_path / "screen.png"
    screen.save(screenshot_path)

    primary_anchor = screen.crop((30, 20, 80, 40))
    primary_anchor.save(tmp_path / "anchor_primary.png")
    secondary_anchor = screen.crop((180, 120, 220, 150))
    secondary_anchor.save(tmp_path / "anchor_secondary.png")

    profile_data = {
        "profile_id": "synthetic",
        "app_name": "Synthetic App",
        "platform_hint": "macos",
        "notes": "",
        "baseline": {"width": 200, "height": 140},
        "anchors": {
            "primary": {
                "id": "primary",
                "path": "anchor_primary.png",
                "x": 10,
                "y": 10,
                "confidence_threshold": 0.8,
            },
            "secondary": {
                "id": "secondary",
                "path": "anchor_secondary.png",
                "x": 160,
                "y": 110,
                "confidence_threshold": 0.8,
            },
        },
        "elements": {
            "action_btn": {
                "label": "Action",
                "aliases": ["go"],
                "rel_x": 60,
                "rel_y": 40,
                "layout": "center_scaled",
                "action": "click",
            }
        },
    }

    profile_path = tmp_path / "profile.json"
    profile_path.write_text(json.dumps(profile_data))
    profile = load_profile(profile_path)

    context = detect_runtime_context(
        profile=profile,
        profile_dir=tmp_path,
        screenshot_path=screenshot_path,
    )

    assert context.live_primary == (30.0, 20.0)
    assert context.live_secondary == (180.0, 120.0)

    resolved = dry_run_command("go", context)
    assert resolved.x == 90.0
    assert resolved.y == 60.0
