from __future__ import annotations

from pathlib import Path

from app_automate.config.settings import AppSettings, load_settings


def test_load_settings_from_toml(tmp_path: Path) -> None:
    settings_path = tmp_path / "app-automate.settings.toml"
    settings_path.write_text(
        """
[llm]
model = "gpt-4o-mini"
api_key = "abc123"
temperature = 0.2

[builder]
grid_size = 160
anchor_confidence_threshold = 0.9
""".strip()
    )

    settings = load_settings(settings_path)

    assert settings.llm.api_key == "abc123"
    assert settings.builder.grid_size == 160
    assert settings.builder.anchor_confidence_threshold == 0.9


def test_load_settings_falls_back_to_env_local(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".env.local").write_text("OPENAI_KEY=test-key\n")

    settings = load_settings()

    assert isinstance(settings, AppSettings)
    assert settings.llm.api_key == "test-key"
