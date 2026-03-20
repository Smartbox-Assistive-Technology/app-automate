from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

from app_automate.builder.models import (
    CropBox,
    MappingAnchor,
    MappingElement,
    MappingResult,
)
from app_automate.builder.training import mapping_result_to_profile
from app_automate.config.models import ActionType, LayoutMode


def test_mapping_result_to_profile_crops_and_validates_anchors(tmp_path: Path) -> None:
    screenshot = Image.new("RGB", (300, 200), "black")
    draw = ImageDraw.Draw(screenshot)
    draw.rectangle((10, 10, 89, 39), fill="red")
    draw.rectangle((40, 16, 56, 28), fill="white")
    draw.rectangle((64, 18, 74, 26), fill="green")
    draw.rectangle((220, 150, 279, 189), fill="blue")
    draw.rectangle((238, 160, 252, 176), fill="yellow")
    draw.rectangle((260, 164, 270, 174), fill="white")
    screenshot_path = tmp_path / "screenshot.png"
    screenshot.save(screenshot_path)

    mapping = MappingResult(
        app_name="Synthetic App",
        primary_anchor=MappingAnchor(
            id="primary",
            crop_box=CropBox(x=10, y=10, width=80, height=30),
        ),
        secondary_anchor=MappingAnchor(
            id="secondary",
            crop_box=CropBox(x=220, y=150, width=60, height=40),
        ),
        elements=[
            MappingElement(
                id="action_btn",
                label="Action",
                x=250,
                y=170,
                layout=LayoutMode.BOTTOM_RIGHT,
                action=ActionType.CLICK,
            )
        ],
    )

    profile = mapping_result_to_profile(
        mapping,
        screenshot_path=screenshot_path,
        output_dir=tmp_path,
        confidence_threshold=0.8,
    )

    assert profile.profile_id == "synthetic-app"
    assert (tmp_path / "anchor_primary.png").exists()
    assert (tmp_path / "anchor_secondary.png").exists()
    assert profile.elements["action_btn"].rel_x == 30.0
    assert profile.elements["action_btn"].rel_y == 20.0


def test_mapping_result_rejects_non_unique_anchor(tmp_path: Path) -> None:
    screenshot = Image.new("RGB", (240, 160), "black")
    draw = ImageDraw.Draw(screenshot)
    draw.rectangle((10, 10, 49, 49), fill="red")
    draw.rectangle((22, 18, 32, 30), fill="white")
    draw.rectangle((120, 10, 159, 49), fill="red")
    draw.rectangle((132, 18, 142, 30), fill="white")
    screenshot_path = tmp_path / "screenshot.png"
    screenshot.save(screenshot_path)

    mapping = MappingResult(
        app_name="Repeated Anchor",
        primary_anchor=MappingAnchor(
            id="primary_anchor",
            crop_box=CropBox(x=10, y=10, width=40, height=40),
        ),
        elements=[
            MappingElement(
                id="action_btn",
                label="Action",
                x=20,
                y=20,
                layout=LayoutMode.FIXED_FROM_PRIMARY,
                action=ActionType.CLICK,
            )
        ],
    )

    try:
        mapping_result_to_profile(
            mapping,
            screenshot_path=screenshot_path,
            output_dir=tmp_path,
            confidence_threshold=0.8,
        )
    except (RuntimeError, ValueError) as exc:
        assert "not unique enough" in str(exc) or "template confidence" in str(exc)
    else:
        raise AssertionError("expected non-unique anchor validation to fail")


def test_mapping_prefers_high_quality_alternate_anchor(tmp_path: Path) -> None:
    screenshot = Image.new("RGB", (280, 180), "black")
    draw = ImageDraw.Draw(screenshot)
    draw.rectangle((10, 10, 49, 49), fill="red")
    draw.rectangle((22, 18, 32, 30), fill="white")
    draw.rectangle((120, 10, 159, 49), fill="red")
    draw.rectangle((132, 18, 142, 30), fill="white")
    draw.rectangle((200, 20, 259, 59), fill="navy")
    draw.rectangle((214, 30, 224, 38), fill="yellow")
    draw.rectangle((236, 32, 248, 46), fill="white")
    screenshot_path = tmp_path / "screenshot.png"
    screenshot.save(screenshot_path)

    mapping = MappingResult(
        app_name="Candidate Ranking App",
        primary_anchor=MappingAnchor(
            id="repeated_tile",
            crop_box=CropBox(x=10, y=10, width=40, height=40),
        ),
        primary_anchor_candidates=[
            MappingAnchor(
                id="window_badge",
                crop_box=CropBox(x=200, y=20, width=60, height=40),
            )
        ],
        elements=[
            MappingElement(
                id="action_btn",
                label="Action",
                x=230,
                y=80,
                layout=LayoutMode.FIXED_FROM_PRIMARY,
                action=ActionType.CLICK,
            )
        ],
    )

    profile = mapping_result_to_profile(
        mapping,
        screenshot_path=screenshot_path,
        output_dir=tmp_path,
        confidence_threshold=0.8,
    )

    assert profile.anchors.primary.id == "window_badge"
    assert profile.anchors.primary.x == 200
    assert profile.anchors.primary.y == 20


def test_mapping_result_ignores_optional_secondary_anchor(tmp_path: Path) -> None:
    screenshot = Image.new("RGB", (300, 200), "black")
    draw = ImageDraw.Draw(screenshot)
    draw.rectangle((10, 10, 89, 39), fill="red")
    draw.rectangle((40, 16, 56, 28), fill="white")
    draw.rectangle((64, 18, 74, 26), fill="green")
    draw.rectangle((160, 120, 199, 159), fill="blue")
    draw.rectangle((230, 120, 269, 159), fill="blue")
    screenshot_path = tmp_path / "screenshot.png"
    screenshot.save(screenshot_path)

    mapping = MappingResult(
        app_name="Fixed Layout App",
        primary_anchor=MappingAnchor(
            id="window_logo",
            crop_box=CropBox(x=10, y=10, width=80, height=30),
        ),
        secondary_anchor=MappingAnchor(
            id="repeated_tile",
            crop_box=CropBox(x=160, y=120, width=40, height=40),
        ),
        elements=[
            MappingElement(
                id="action_btn",
                label="Action",
                x=120,
                y=80,
                layout=LayoutMode.FIXED_FROM_PRIMARY,
                action=ActionType.CLICK,
            )
        ],
    )

    profile = mapping_result_to_profile(
        mapping,
        screenshot_path=screenshot_path,
        output_dir=tmp_path,
        confidence_threshold=0.8,
    )

    assert profile.anchors.secondary is None
    assert not (tmp_path / "anchor_secondary.png").exists()


def test_mapping_result_requires_secondary_anchor_for_scaled_layout(
    tmp_path: Path,
) -> None:
    screenshot = Image.new("RGB", (300, 200), "black")
    draw = ImageDraw.Draw(screenshot)
    draw.rectangle((10, 10, 89, 39), fill="red")
    draw.rectangle((40, 16, 56, 28), fill="white")
    draw.rectangle((64, 18, 74, 26), fill="green")
    screenshot_path = tmp_path / "screenshot.png"
    screenshot.save(screenshot_path)

    mapping = MappingResult(
        app_name="Scaled Layout App",
        primary_anchor=MappingAnchor(
            id="window_logo",
            crop_box=CropBox(x=10, y=10, width=80, height=30),
        ),
        elements=[
            MappingElement(
                id="capture_btn",
                label="Capture",
                x=120,
                y=80,
                layout=LayoutMode.CENTER_SCALED,
                action=ActionType.CLICK,
            )
        ],
    )

    try:
        mapping_result_to_profile(
            mapping,
            screenshot_path=screenshot_path,
            output_dir=tmp_path,
            confidence_threshold=0.8,
        )
    except RuntimeError as exc:
        assert "secondary anchor is required" in str(exc)
    else:
        raise AssertionError("expected missing secondary anchor to fail")
