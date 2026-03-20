from __future__ import annotations

from pathlib import Path

from PIL import Image


def crop_anchor(
    image_path: Path,
    output_path: Path,
    *,
    x: int,
    y: int,
    width: int,
    height: int,
) -> Path:
    image = Image.open(image_path)
    crop = image.crop((x, y, x + width, y + height))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    crop.save(output_path)
    return output_path
