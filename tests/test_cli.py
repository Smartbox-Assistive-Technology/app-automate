from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from app_automate import cli
from app_automate.accessibility.macos_ax import AXElement

runner = CliRunner()


def test_list_elements_command() -> None:
    result = runner.invoke(
        cli.app,
        [
            "list-elements",
            str(Path("examples/profiles/camera-demo/profile.json")),
        ],
    )
    assert result.exit_code == 0
    assert "shutter_btn" in result.stdout


def test_inspect_command() -> None:
    result = runner.invoke(
        cli.app,
        [
            "inspect",
            str(Path("examples/profiles/camera-demo/profile.json")),
        ],
    )
    assert result.exit_code == 0
    assert "Profile: camera-demo" in result.stdout


def test_click_command_uses_action_adapter(monkeypatch) -> None:
    clicks: list[tuple[float, float]] = []

    class FakeAdapter:
        def click(self, x: float, y: float) -> None:
            clicks.append((x, y))

    monkeypatch.setattr(cli, "_create_action_adapter", lambda: FakeAdapter())

    result = runner.invoke(
        cli.app,
        [
            "click",
            "capture",
            "--profile",
            str(Path("examples/profiles/photo-booth/profile.json")),
            "--primary-x",
            "0",
            "--primary-y",
            "0",
            "--secondary-x",
            "607",
            "--secondary-y",
            "529",
        ],
    )

    assert result.exit_code == 0
    assert clicks == [(359.7, 540.7)]
    assert '"element_id": "shutter_btn"' in result.stdout


def test_locate_anchors_command_uses_detected_context(monkeypatch) -> None:
    monkeypatch.setattr(
        cli,
        "_runtime_context",
        lambda **_: cli.RuntimeContext(
            profile=cli.load_profile(
                Path("examples/profiles/photo-booth/profile.json")
            ),
            live_primary=(522.0, 207.0),
            live_secondary=(1129.0, 736.0),
            screenshot_path=Path("/tmp/synthetic-screen.png"),
            primary_confidence=0.99,
            secondary_confidence=0.98,
        ),
    )

    result = runner.invoke(
        cli.app,
        [
            "locate-anchors",
            "--profile",
            str(Path("examples/profiles/photo-booth/profile.json")),
        ],
    )

    assert result.exit_code == 0
    assert '"screenshot_path": "/tmp/synthetic-screen.png"' in result.stdout
    assert '"x": 522.0' in result.stdout


def test_debug_target_writes_overlay(monkeypatch, tmp_path: Path) -> None:
    screenshot_path = tmp_path / "screen.png"
    screenshot_path.write_bytes(b"fake")

    monkeypatch.setattr(
        cli,
        "_runtime_context",
        lambda **_: cli.RuntimeContext(
            profile=cli.load_profile(
                Path("examples/profiles/photo-booth/profile.json")
            ),
            live_primary=(522.0, 207.0),
            live_secondary=(1129.0, 736.0),
            screenshot_path=screenshot_path,
            primary_confidence=0.99,
            secondary_confidence=0.98,
        ),
    )

    written: list[Path] = []

    def fake_write_debug_outputs(*, context, result, output_dir):
        overlay = output_dir / "target-overlay.png"
        window = output_dir / "window-crop.png"
        written.extend([overlay, window])
        return overlay, window

    monkeypatch.setattr(cli, "_write_debug_outputs", fake_write_debug_outputs)

    result = runner.invoke(
        cli.app,
        [
            "debug-target",
            "effects",
            "--profile",
            str(Path("examples/profiles/photo-booth/profile.json")),
            "--output-dir",
            str(tmp_path / "debug"),
        ],
    )

    assert result.exit_code == 0
    assert len(written) == 2
    assert '"overlay_path"' in result.stdout


def test_ax_list_outputs_json(monkeypatch) -> None:
    monkeypatch.setattr(
        cli,
        "list_app_ui_elements",
        lambda *args, **kwargs: [
            AXElement(
                path="front window > UI element 1",
                class_name="button",
                role="AXButton",
                subrole=None,
                description="Style",
                title=None,
                name=None,
                x=140,
                y=10,
                width=40,
                height=40,
                enabled=True,
                depth=1,
                child_count=0,
            )
        ],
    )

    result = runner.invoke(
        cli.app,
        [
            "ax-list",
            "--app",
            "Pages",
            "--json",
        ],
    )

    assert result.exit_code == 0
    assert '"class_name": "button"' in result.stdout
    assert '"label": "Style"' in result.stdout


def test_ax_click_dry_run(monkeypatch) -> None:
    monkeypatch.setattr(
        cli,
        "find_matching_elements",
        lambda *args, **kwargs: [
            AXElement(
                path="front window > UI element 1",
                class_name="menu button",
                role="AXMenuButton",
                subrole=None,
                description="Insert",
                title=None,
                name=None,
                x=367,
                y=33,
                width=41,
                height=52,
                enabled=True,
                depth=1,
                child_count=1,
            )
        ],
    )

    result = runner.invoke(
        cli.app,
        [
            "ax-click",
            "--app",
            "Pages",
            "--contains",
            "Insert",
            "--dry-run",
        ],
    )

    assert result.exit_code == 0
    assert '"label": "Insert"' in result.stdout
    assert '"action": "click"' in result.stdout
    assert '"x": 387.5' in result.stdout


def test_ax_click_executes_drag(monkeypatch) -> None:
    calls: list[tuple[float, float, float, float]] = []

    class FakeAdapter:
        def click(self, x: float, y: float) -> None:
            raise AssertionError("unexpected click")

        def right_click(self, x: float, y: float) -> None:
            raise AssertionError("unexpected right_click")

        def double_click(self, x: float, y: float) -> None:
            raise AssertionError("unexpected double_click")

        def scroll(self, x: float, y: float, clicks: int) -> None:
            raise AssertionError("unexpected scroll")

        def drag(
            self,
            start_x: float,
            start_y: float,
            end_x: float,
            end_y: float,
            *,
            duration: float = 0.2,
            button: str = "left",
        ) -> None:
            calls.append((start_x, start_y, end_x, end_y))

    monkeypatch.setattr(
        cli,
        "find_matching_elements",
        lambda *args, **kwargs: [
            AXElement(
                path="front window > UI element 1",
                class_name="button",
                role="AXButton",
                subrole=None,
                description="Body",
                title=None,
                name=None,
                x=802,
                y=131,
                width=221,
                height=47,
                enabled=True,
                depth=1,
                child_count=0,
            )
        ],
    )
    monkeypatch.setattr(cli, "_create_action_adapter", lambda: FakeAdapter())

    result = runner.invoke(
        cli.app,
        [
            "ax-click",
            "--app",
            "Pages",
            "--contains",
            "Body",
            "--action",
            "drag",
            "--drag-dx",
            "50",
            "--drag-dy",
            "0",
            "--execute",
        ],
    )

    assert result.exit_code == 0
    assert calls == [(912.5, 154.5, 962.5, 154.5)]
    assert '"end_x": 962.5' in result.stdout
