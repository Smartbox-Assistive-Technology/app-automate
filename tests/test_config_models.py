from __future__ import annotations

from pathlib import Path

from app_automate.config.validation import load_profile


def test_example_profile_loads() -> None:
    profile = load_profile(Path("examples/profiles/camera-demo/profile.json"))
    assert profile.profile_id == "camera-demo"
    assert "shutter_btn" in profile.elements


def test_photo_booth_profile_loads() -> None:
    profile = load_profile(Path("examples/profiles/photo-booth/profile.json"))
    assert profile.profile_id == "photo-booth"
    assert "effects_btn" in profile.elements
