from __future__ import annotations

from app_automate.config.models import AppProfile


def profile_json_schema() -> dict[str, object]:
    return AppProfile.model_json_schema()
