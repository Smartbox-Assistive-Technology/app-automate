from __future__ import annotations

import json
from pathlib import Path

from app_automate.config.models import AppProfile


def load_profile(path: Path) -> AppProfile:
    data = json.loads(path.read_text())
    return AppProfile.model_validate(data)


def save_profile(profile: AppProfile, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(profile.model_dump_json(indent=2))
