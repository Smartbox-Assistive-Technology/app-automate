# app-automate

`app-automate` is an accessibility-oriented automation tool built around two phases:

1. Build an app-specific interaction profile from screenshots and a numbered grid.
2. Run commands locally using saved profiles plus computer vision.

The codebase is currently developed and validated on macOS. The core runtime is intentionally platform-neutral so Windows can become the main production platform later without replacing the profile model, transform logic, or CV matching.

## Plain-English Overview

This project is trying to make software easier to use by teaching the computer where important buttons are in a specific app.

A very simple way to think about it:
- first, the tool looks at a screenshot of an app and builds a map of where things are
- later, it uses that saved map to find the app on screen again and click the right place

So instead of asking an AI to drive the whole computer every time, we use AI once to help build a reusable map, then use faster local computer vision to do the repeated work.

## Project Status

Working today:
- strict JSON profile schema with Pydantic
- macOS accessibility inspection through `System Events` for apps that expose useful UI metadata
- training asset generation from screenshots and grid overlays
- LLM-backed profile generation through Simon Willison's `llm` library
- settings-file-based LLM configuration via `app-automate.settings.toml`
- automatic macOS front-window capture during training
- automatic anchor cropping and anchor validation during training
- retry artifacts for rejected LLM mappings
- template-matching anchor detection from a full-screen capture
- coordinate resolution for anchored and scaled controls
- debug overlay output for target validation
- real clicking through `pyautogui`

Not complete yet:
- profile creation still needs manual review/tuning
- Windows runtime adapter is not implemented
- multi-monitor and app-mode changes are only lightly tested
- anchor selection is still not strong enough for every app without retries or manual cleanup

## Prerequisites

- macOS with `Screen Recording` permission enabled for Codex or the process running this tool
- macOS with `Accessibility` permission enabled for Codex or the process running this tool
- Python managed through `uv`

Without those permissions:
- screen capture may fail or return empty images
- `click` may do nothing or fail unpredictably

## Tooling

- `uv` for packaging, dependency management, and commands
- `ruff` for linting and formatting
- `pytest` for tests

## Quick Start

```bash
uv sync
uv run ruff check .
uv run ruff format .
uv run pytest
```

To use the LLM-backed builder, create a local settings file from the example:

```bash
cp app-automate.settings.example.toml app-automate.settings.toml
```

Then add your API key and chosen model there. The real settings file is ignored by git.

Example:

```toml
[llm]
model = "gpt-4o-mini"
api_key = "sk-..."
max_attempts = 2

[builder]
grid_size = 120
anchor_confidence_threshold = 0.85
```

For local development only, `.env.local` is also supported as a fallback for `OPENAI_KEY` or `OPENAI_API_KEY`, but the intended production path is the settings file.

## Typical Workflow

1. Generate training assets from a screenshot:

```bash
uv run app-automate train --screenshot examples/profiles/photo-booth/window.png --output-dir examples/profiles/photo-booth
```

Or capture the front window of a live macOS app and run the LLM-backed builder:

```bash
uv run app-automate train --app "Photo Booth" --settings app-automate.settings.toml --output-dir examples/profiles/photo-booth-trained
```

That training run now:
- captures the app window on macOS
- renders a grid overlay
- sends the grid image to the configured LLM
- validates anchor crops and profile structure
- retries if the mapping is rejected
- saves both successful output and failed-attempt artifacts

2. Inspect a saved profile:

```bash
uv run app-automate inspect examples/profiles/photo-booth/profile.json
```

3. Check whether the runtime can find the live anchors:

```bash
uv run app-automate locate-anchors --profile examples/profiles/photo-booth/profile.json
```

4. Validate a resolved target without clicking:

```bash
uv run app-automate debug-target effects --profile examples/profiles/photo-booth/profile.json --output-dir debug-output/photo-booth
```

5. Execute a real click:

```bash
uv run app-automate click effects --profile examples/profiles/photo-booth/profile.json
```

## CLI

Common commands:

```bash
uv run app-automate ax-list --app "Pages"
uv run app-automate ax-click --app "Pages" --contains "Insert" --max-depth 2 --dry-run
uv run app-automate inspect examples/profiles/camera-demo/profile.json
uv run app-automate list-elements examples/profiles/camera-demo/profile.json
uv run app-automate dry-run record --profile examples/profiles/camera-demo/profile.json
uv run app-automate locate-anchors --profile examples/profiles/photo-booth/profile.json
uv run app-automate debug-target effects --profile examples/profiles/photo-booth/profile.json --output-dir debug-output/photo-booth
uv run app-automate click effects --profile examples/profiles/photo-booth/profile.json
uv run app-automate train --output-dir examples/profiles/new-profile
```

Useful debugging options:
- `--screenshot` to run detection against a saved full-screen image
- `--primary-x/--primary-y` and `--secondary-x/--secondary-y` to bypass live anchor detection and force known coordinates
- `--settings` on `train` to use a local settings file instead of environment variables
- `--app` on `train` to capture the front window of a live macOS app automatically
- `ax-list --actionable-only` to show only accessible interactive controls on macOS
- `ax-click --dry-run` to resolve an accessible control before executing input

## Profile Anatomy

The main example profile is [profile.json](/Users/willwade/GitHub/app-automate/examples/profiles/photo-booth/profile.json).

Key fields:
- `baseline`: the reference window size used when the profile was created
- `anchors.primary`: the main visual anchor and its baseline position
- `anchors.secondary`: an optional second anchor for scaling and edge-anchored controls
- `elements[*].rel_x` / `rel_y`: element coordinates relative to the profile’s anchor system
- `elements[*].layout`: how the element should behave when the window moves or resizes

Example:

```json
{
  "baseline": { "width": 720, "height": 572 },
  "anchors": {
    "primary": { "id": "titlebar_top_left", "path": "anchor_primary.png", "x": 0, "y": 0 },
    "secondary": { "id": "effects_button_bottom_right", "path": "anchor_secondary.png", "x": 607, "y": 529 }
  },
  "elements": {
    "effects_btn": {
      "label": "Effects",
      "rel_x": 48.5,
      "rel_y": 16,
      "layout": "bottom_right",
      "action": "click"
    }
  }
}
```

## Layout Modes

- `fixed_from_primary`: fixed offset from the detected primary anchor
- `top_right`: x from the detected secondary anchor, y from the detected primary origin
- `bottom_right`: fixed offset from the detected secondary anchor
- `center_scaled`: offset from the primary anchor, scaled using the primary/secondary anchor delta

## Current Limitations

- macOS accessibility inspection currently uses `System Events` UI scripting rather than lower-level AX bindings.
- macOS semantic actions currently resolve element bounds semantically, then execute input through `pyautogui`.
- Some macOS apps expose useful accessibility labels and bounds; others expose very little.
- LLM-backed builder output still requires manual inspection and adjustment.
- The builder can now reject weak mappings, but it still does not rank anchors intelligently before asking the user to review them.
- Resizing works best for controls anchored to corners or edges.
- Fully scaled controls depend on the app resizing proportionally.
- Switching app modes can invalidate a profile even if the window frame remains stable.
- Multi-display support exists through `mss`, but the validation matrix is still small.
- The current live input path uses `pyautogui`, which should work on Windows for basic input, but we do not yet have a Windows-specific adapter or a strong Windows validation matrix.
- Automatic app-window capture during training is currently macOS-only.
- Prompt quality still needs improvement for generic repeated UIs such as tiled galleries or repeated controls.

## Troubleshooting

If anchor detection fails:
- run `locate-anchors` first
- check the anchor confidence values
- verify that the stored anchor images match the same coordinate system as runtime capture
- rebuild the anchor crops if the app theme or window chrome changed

If `train` fails:
- inspect `mapping_error.txt` in the output directory
- inspect any `mapping_output.attempt-N.json` files to see what the model proposed
- check whether the model chose a repeated tile or an over-large crop as an anchor
- try retraining from a cleaner app state with fewer repeated controls on screen

If a click lands in the wrong place:
- run `debug-target` and inspect the generated overlay image
- compare the detected anchors with the visible window corners
- check whether the control uses the correct `layout`
- confirm the app is in the same mode the profile was trained against

If macOS capture or clicking fails:
- re-check `Screen Recording` and `Accessibility` permissions
- verify the app is visible on screen and not minimized

## Coordinate Notes

Runtime capture uses `mss`, which reports logical display coordinates on this Mac. That keeps anchor detection aligned with `pyautogui` click coordinates on Retina displays. Profile assets and runtime capture need to stay in the same coordinate system.

## Additional Docs

- [Architecture](/Users/willwade/GitHub/app-automate/docs/architecture.md)
- [MVP Roadmap](/Users/willwade/GitHub/app-automate/docs/mvp-roadmap.md)
- [New App Guide](/Users/willwade/GitHub/app-automate/docs/new-app-guide.md)
