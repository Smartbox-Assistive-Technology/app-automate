from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw


def render_grid_overlay(
    image_path: Path,
    output_path: Path,
    *,
    grid_size: int = 120,
) -> Path:
    image = Image.open(image_path).convert("RGB")
    draw = ImageDraw.Draw(image)
    width, height = image.size

    for x in range(0, width, grid_size):
        draw.line((x, 0, x, height), fill=(255, 0, 0), width=1)
    for y in range(0, height, grid_size):
        draw.line((0, y, width, y), fill=(255, 0, 0), width=1)

    for row, y in enumerate(range(0, height, grid_size), start=1):
        for col, x in enumerate(range(0, width, grid_size), start=1):
            cell_id = f"R{row}C{col}"
            draw.rectangle((x + 4, y + 4, x + 72, y + 24), fill=(255, 255, 255))
            draw.text((x + 8, y + 6), cell_id, fill=(0, 0, 0))

    output_path.parent.mkdir(parents=True, exist_ok=True)
    image.save(output_path)
    return output_path
