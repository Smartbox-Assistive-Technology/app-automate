from __future__ import annotations

import tomllib
from pathlib import Path

from pydantic import BaseModel, Field

DEFAULT_SETTINGS_PATH = Path("app-automate.settings.toml")
DEFAULT_ENV_LOCAL_PATH = Path(".env.local")


class LLMSettings(BaseModel):
    model: str = "gpt-4o-mini"
    api_key: str | None = None
    system_prompt: str | None = None
    temperature: float = Field(default=0.0, ge=0.0, le=2.0)
    max_tokens: int | None = Field(default=None, gt=0)
    max_attempts: int = Field(default=2, ge=1, le=5)


class BuilderSettings(BaseModel):
    grid_size: int = Field(default=120, ge=40)
    anchor_confidence_threshold: float = Field(default=0.85, ge=0.0, le=1.0)


class AppSettings(BaseModel):
    llm: LLMSettings = LLMSettings()
    builder: BuilderSettings = BuilderSettings()


def load_settings(settings_path: Path | None = None) -> AppSettings:
    if settings_path is not None:
        if not settings_path.exists():
            raise FileNotFoundError(f"settings file not found: {settings_path}")
        return AppSettings.model_validate(_load_toml(settings_path))

    if DEFAULT_SETTINGS_PATH.exists():
        return AppSettings.model_validate(_load_toml(DEFAULT_SETTINGS_PATH))

    if DEFAULT_ENV_LOCAL_PATH.exists():
        return AppSettings(
            llm=LLMSettings(
                api_key=_load_env_key(DEFAULT_ENV_LOCAL_PATH),
            )
        )

    return AppSettings()


def _load_toml(path: Path) -> dict[str, object]:
    with path.open("rb") as handle:
        return tomllib.load(handle)


def _load_env_key(path: Path) -> str | None:
    for raw_line in path.read_text().splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        normalized = key.strip()
        if normalized in {"OPENAI_KEY", "OPENAI_API_KEY"}:
            return value.strip().strip("\"'")
    return None
