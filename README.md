# app-automate

`app-automate` discovers interactive elements in desktop applications and drives them through platform accessibility APIs, browser DevTools, or visual profile matching.

Three backend strategies, picked per-app:

| Backend | How it works | Best for |
|---------|-------------|----------|
| **UIA** | Windows UI Automation tree | Native Windows apps (Calculator, classic Outlook) |
| **CDP** | Chrome DevTools Protocol via Playwright | WebView2 apps (new Outlook, Teams) |
| **CV** | Screenshot + LLM-built profile + template matching | Anything else; cross-platform fallback |

Use `probe <app>` to auto-detect the right backend.

## Quick Start

```bash
uv sync
uv run ruff check .
uv run ruff format .
uv run pytest
```

For the LLM-backed visual profile builder, copy and edit the settings file:

```bash
cp app-automate.settings.example.toml app-automate.settings.toml
```

```toml
[llm]
model = "gpt-4o-mini"
api_key = "sk-..."
max_attempts = 2

[builder]
grid_size = 120
anchor_confidence_threshold = 0.85
```

## Workflow

### 1. Discover which backend to use

```bash
uv run --no-project app-automate probe "Calculator"
```

Returns a recommendation (`uia`, `cdp`, or `cv`) with element counts and reasoning.

### 2. Interact directly (UIA or CDP)

No profile needed — these backends query the live app:

```bash
# Windows native app
uv run --no-project app-automate uia-list --app "Calculator" --actionable-only
uv run --no-project app-automate uia-click --app "Calculator" --contains "Close" --execute

# WebView2 app — enable CDP first
uv run --no-project app-automate cdp-setup --app "Outlook"
uv run --no-project app-automate cdp-list --actionable-only
uv run --no-project app-automate cdp-click --contains "New email" --exact --execute
uv run --no-project app-automate cdp-type --contains "To" --exact --text "user@example.com" --execute
```

### 3. Build a visual profile (CV path)

For apps where accessibility APIs don't reach, build a profile from a screenshot:

```bash
# Capture the front window and build a profile
uv run --no-project app-automate train --app "Photo Booth" --settings app-automate.settings.toml --output-dir examples/profiles/photo-booth

# Or from an existing screenshot
uv run --no-project app-automate train --screenshot window.png --output-dir examples/profiles/my-app
```

Then run commands against the saved profile:

```bash
uv run --no-project app-automate inspect examples/profiles/photo-booth/profile.json
uv run --no-project app-automate locate-anchors --profile examples/profiles/photo-booth/profile.json
uv run --no-project app-automate dry-run effects --profile examples/profiles/photo-booth/profile.json
uv run --no-project app-automate click effects --profile examples/profiles/photo-booth/profile.json
```

## CLI Reference

### Probe and Discovery

| Command | Description |
|---------|-------------|
| `probe <app>` | Detect best backend (UIA / CDP / CV) for an app |

### UIA (Windows native apps)

| Command | Description |
|---------|-------------|
| `uia-list --app <name>` | List UI elements via Windows UI Automation |
| `uia-click --app <name> --contains <text>` | Click a matched element |
| `uia-type --app <name> --contains <text> --text <text>` | Type into a matched element |

### CDP (WebView2 apps)

| Command | Description |
|---------|-------------|
| `cdp-setup --app <name>` | Enable CDP debugging and restart the app |
| `cdp-list` | List interactive elements via Chrome DevTools Protocol |
| `cdp-click --contains <text>` | Click a matched element |
| `cdp-type --contains <text> --text <text>` | Type into a matched field |

### macOS Accessibility

| Command | Description |
|---------|-------------|
| `ax-list --app <name>` | List UI elements via macOS System Events |
| `ax-click --app <name> --contains <text>` | Click a matched element |

### Visual Profiles (CV)

| Command | Description |
|---------|-------------|
| `train --app <name>` | Capture window, generate grid, build profile via LLM |
| `inspect <profile>` | Describe a saved profile |
| `list-elements <profile>` | List elements in a profile |
| `locate-anchors --profile <path>` | Check live anchor detection |
| `dry-run <command> --profile <path>` | Resolve a target without clicking |
| `click <command> --profile <path>` | Execute a click on a resolved target |
| `debug-target <command> --profile <path>` | Generate annotated debug overlay |

### Common Options

- `--exact` / `--substring` — exact vs substring matching for `--contains` (CDP commands)
- `--dry-run` / `--execute` — preview vs real input (UIA, CDP, macOS)
- `--actionable-only` / `--all` — filter to interactive controls
- `--json` / `--table` — output format for list commands
- `--index <n>` — select among multiple matches (1-based)
- `--app <name>` — capture or target a specific app window
- `--port <n>` — CDP port (default 9222)

## Profile Anatomy

Profiles are JSON files describing an app's visual layout relative to anchor images.

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

Key fields:
- `baseline`: reference window size used when the profile was created
- `anchors.primary` / `anchors.secondary`: visual anchor images and baseline positions
- `elements[*].rel_x` / `rel_y`: element coordinates relative to the anchor system
- `elements[*].layout`: how the element behaves when the window moves or resizes

### Layout Modes

- `fixed_from_primary`: fixed offset from the detected primary anchor
- `top_right`: x from secondary anchor, y from primary
- `bottom_right`: fixed offset from the detected secondary anchor
- `center_scaled`: offset from primary, scaled using primary/secondary delta

## Multi-State Profiles

Apps change appearance across states. Multi-state profiles handle this with per-state signatures:

```json
{
  "profile_id": "camera-app",
  "app_name": "Camera App",
  "baseline": { "width": 800, "height": 600 },
  "default_state": "idle",
  "states": {
    "idle": {
      "id": "idle",
      "signature": { "check_regions": [{ "path": "check_no_camera.png", "x": 50, "y": 100, "required": true }] },
      "anchors": { "primary": { "id": "titlebar", "path": "anchor.png", "x": 0, "y": 0 } },
      "elements": { "connect_btn": { "label": "Connect", "rel_x": 100, "rel_y": 50, "layout": "fixed_from_primary" } }
    },
    "connected": {
      "id": "connected",
      "signature": { "check_regions": [{ "path": "check_camera_icon.png", "x": 50, "y": 100, "required": true }] },
      "anchors": { "primary": { "id": "titlebar", "path": "anchor.png", "x": 0, "y": 0 } },
      "elements": { "record_btn": { "label": "Record", "rel_x": 200, "rel_y": 50, "layout": "fixed_from_primary" } }
    }
  }
}
```

Runtime auto-detects the current state by matching signature regions (~5-10ms per region). Use `--state` to force a specific state.

## Platform Support

### Windows

- **UIA** — uses `uiautomation` library; works for native Win32/WPF/WinUI apps
- **CDP** — uses Playwright `connect_over_cdp()`; for WebView2 apps
- **CV** — visual profile path with `ctypes`/`user32` window capture
- DPI awareness handled via `SetProcessDpiAwareness(2)`
- Window capture via `EnumWindows` / `GetWindowRect`
- Note: the `comtypes` gen cache can corrupt between runs; `uia-list` auto-clears it

### macOS

- **Accessibility** — uses System Events UI scripting
- **CV** — visual profile path with `screencapture` window capture
- Requires `Screen Recording` and `Accessibility` permissions

## Project Status

Working today:
- JSON profile schema with Pydantic validation
- Multi-state profiles with automatic state detection
- macOS accessibility inspection via System Events
- Windows UIA inspection and direct click/type
- Windows CDP inspection and direct click/type via Playwright
- `probe` command for auto-detecting the best backend per app
- Training asset generation from screenshots and grid overlays
- LLM-backed profile generation via the `llm` library
- Automatic window capture on both macOS and Windows
- Automatic anchor cropping and validation
- Template-matching anchor detection
- Coordinate resolution for anchored and scaled controls
- Debug overlay output for target validation

Not complete yet:
- Profile creation still needs manual review/tuning
- Multi-monitor / DPI scale validation matrix (100%, 125%, 150%)
- CDP port is global — not aware of which app's WebView2 to connect to when multiple are running
- Hybrid profiles combining UIA + CV selectors
- LLM-assisted multi-state profile generation needs prompt refinement
- Anchor selection is still not strong enough for every app without retries

## Tooling

- `uv` for packaging, dependency management, and commands
- `ruff` for linting and formatting
- `pytest` for tests

## Troubleshooting

**`probe` recommends wrong backend**: some apps expose partial UIA trees. Run `uia-list --app <name> --actionable-only` and `cdp-list` separately to see what each finds.

**`uia-list` fails or crashes**: the `comtypes` cache may be corrupt. The tool auto-clears it, but if issues persist, manually delete `.venv/Lib/site-packages/comtypes/gen/*`.

**`cdp-list` fails**: CDP must be enabled first. Run `cdp-setup --app <name>`, then close and reopen the app. Verify with `cdp-setup` (no args) — it should show `"listening": "true"`.

**`cdp-click --contains "X"` matches too broadly**: use `--exact` to require an exact label match instead of substring.

**Anchor detection fails (CV path)**: run `locate-anchors`, check confidence values, verify anchor images match the current app appearance. Rebuild with `train` if the app theme or window chrome changed.

**Click lands in wrong place (CV path)**: run `debug-target` and inspect the overlay image. Check the control's `layout` mode and confirm the app is in the expected state.

**macOS capture or clicking fails**: re-check `Screen Recording` and `Accessibility` permissions in System Settings.

## Coordinate Notes

On macOS, runtime capture uses `mss` which reports logical display coordinates, keeping anchor detection aligned with `pyautogui` click coordinates on Retina displays.

On Windows, DPI awareness is set to per-monitor DPI-aware (level 2) so coordinates from `GetWindowRect` and `mss` capture are in physical pixels.

## Additional Docs

- [Architecture](docs/architecture.md)
- [MVP Roadmap](docs/mvp-roadmap.md)
- [New App Guide](docs/new-app-guide.md)
- [Windows Integration](docs/windows-integration.md)
