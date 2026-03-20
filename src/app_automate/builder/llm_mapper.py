from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import llm
from PIL import Image

from app_automate.builder.models import MappingResult
from app_automate.builder.prompt import build_mapping_prompt
from app_automate.config.settings import AppSettings


def prepare_mapping_request(
    grid_image_path: Path,
    *,
    app_name: str | None,
    image_width: int,
    image_height: int,
    grid_size: int,
) -> dict[str, Any]:
    return {
        "prompt": build_mapping_prompt(
            app_name=app_name,
            image_width=image_width,
            image_height=image_height,
            grid_size=grid_size,
        ),
        "image_path": str(grid_image_path),
        "schema": MappingResult.model_json_schema(),
        "image_width": image_width,
        "image_height": image_height,
        "grid_size": grid_size,
    }


def run_mapping_llm(
    grid_image_path: Path,
    *,
    app_name: str | None,
    settings: AppSettings,
    grid_size: int,
    feedback: str | None = None,
) -> tuple[MappingResult, str]:
    if not settings.llm.api_key:
        raise RuntimeError(
            "no LLM API key configured. Add app-automate.settings.toml or .env.local"
        )

    with Image.open(grid_image_path) as image:
        image_width, image_height = image.size

    request = prepare_mapping_request(
        grid_image_path,
        app_name=app_name,
        image_width=image_width,
        image_height=image_height,
        grid_size=grid_size,
    )
    prompt = request["prompt"]
    if feedback:
        prompt = (
            f"{prompt}\n\n"
            "The previous attempt was rejected for these reasons:\n"
            f"{feedback}\n\n"
            "Try again with tighter, more unique anchors and semantic ids."
        )

    model = llm.get_model(settings.llm.model)
    setattr(model, "key", settings.llm.api_key)

    options: dict[str, Any] = {
        "temperature": settings.llm.temperature,
    }
    if settings.llm.max_tokens is not None:
        options["max_tokens"] = settings.llm.max_tokens

    response = model.prompt(
        prompt,
        attachments=[llm.Attachment(path=str(grid_image_path))],
        system=settings.llm.system_prompt,
        stream=False,
        schema=MappingResult,
        **options,
    )
    raw_text = response.text()
    return MappingResult.model_validate(json.loads(raw_text)), raw_text
