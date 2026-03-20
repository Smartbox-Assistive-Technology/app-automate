from __future__ import annotations

import tempfile
import uuid
from pathlib import Path

from PIL import Image


def capture_main_display(output_path: Path) -> Path:
    import mss

    with mss.mss() as sct:
        monitor = sct.monitors[1]
        raw = sct.grab(monitor)
        image = Image.frombytes("RGB", raw.size, raw.rgb)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        image.save(output_path)
    return output_path


def capture_main_display_temp(prefix: str = "app-automate-screen-") -> Path:
    temp_dir = Path(tempfile.gettempdir())
    return capture_main_display(temp_dir / f"{prefix}{uuid.uuid4().hex}.png")
