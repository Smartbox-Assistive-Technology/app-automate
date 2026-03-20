from __future__ import annotations

from pathlib import Path

from app_automate.config.validation import load_profile
from app_automate.runner.runtime import RuntimeContext, dry_run_command
from app_automate.runner.transform import compute_transform


def test_transform_scales_between_two_anchors() -> None:
    profile = load_profile(Path("examples/profiles/camera-demo/profile.json"))
    transform = compute_transform(
        profile,
        live_primary=(100.0, 150.0),
        live_secondary=(2540.0, 1570.0),
    )
    assert transform.scale_x == 2.0
    assert transform.scale_y == 2.0


def test_dry_run_resolves_alias() -> None:
    profile = load_profile(Path("examples/profiles/camera-demo/profile.json"))
    resolved = dry_run_command(
        "record",
        RuntimeContext(
            profile=profile,
            live_primary=(100.0, 150.0),
            live_secondary=(1320.0, 860.0),
        ),
    )
    assert resolved.element_id == "shutter_btn"
    assert resolved.x == 550.0
    assert resolved.y == 350.0
