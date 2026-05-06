# app-automate

`app-automate` discovers interactive elements in desktop applications and drives them through platform accessibility APIs, browser DevTools, or visual profile matching.

Three backend strategies, picked per-app:

| Backend | How it works | Best for |
|---------|-------------|----------|
| **UIA** | Windows UI Automation tree | Native Windows apps (Calculator, Paint, classic Outlook) |
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

### 2. Inspect what's under the cursor

```bash
uv run --no-project app-automate whats-here
uv run --no-project app-automate whats-here --radius 150 --app Paint
```

Reads cursor position and lists all UIA/CDP elements in a box around it. Useful for exploring what the accessibility tree can see.

### 3. Interact directly (UIA or CDP)

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

### 4. Build a semantic profile (UIA or CDP)

Snapshot the live element tree into a reusable profile — no LLM tokens, no screenshots:

```bash
# From UIA (native Windows app)
uv run --no-project app-automate train --backend uia --app Paint --output-dir examples/profiles/paint

# From CDP (WebView2 app)
uv run --no-project app-automate train --backend cdp --output-dir examples/profiles/outlook
```

Then execute actions against the profile — the runtime re-queries the live backend by stored selectors:

```bash
uv run --no-project app-automate inspect examples/profiles/paint/profile.json
uv run --no-project app-automate list-elements examples/profiles/paint/profile.json
uv run --no-project app-automate dry-run oval --profile examples/profiles/paint/profile.json
uv run --no-project app-automate click oval --profile examples/profiles/paint/profile.json
uv run --no-project app-automate click brushes --profile examples/profiles/paint/profile.json
uv run --no-project app-automate click to_field --profile examples/profiles/outlook/profile.json --text "hello@example.com"
```

Semantic profiles support these actions: `click`, `double_click`, `right_click`, `type`, `drag`, `scroll`, `hotkey`, `wait`.

### 5. Build a visual profile (CV path)

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

### Demo: Draw a car in Paint

```bash
uv run --no-project python demos/paint_car.py
```

Opens MS Paint, builds a semantic profile from the live UIA tree, then draws a car (body, roof, wheels, red fill) using brush, oval, and fill tools selected from the profile.

## CLI Reference

### Probe and Discovery

| Command | Description |
|---------|-------------|
| `probe <app>` | Detect best backend (UIA / CDP / CV) for an app |
| `whats-here` | List UIA/CDP elements near the cursor position |

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

### Semantic Profiles (UIA / CDP)

| Command | Description |
|---------|-------------|
| `train --backend uia --app <name>` | Snapshot UIA tree into a semantic profile |
| `train --backend cdp` | Snapshot CDP elements into a semantic profile |
| `inspect <profile>` | Describe a saved profile |
| `list-elements <profile>` | List elements in a profile |
| `dry-run <command> --profile <path>` | Resolve target without acting |
| `click <command> --profile <path>` | Execute action via stored selectors |
| `click <command> --profile <path> --text <text>` | Execute type action |

### Visual Profiles (CV)

| Command | Description |
|---------|-------------|
| `train --app <name>` | Capture window, generate grid, build profile via LLM |
| `locate-anchors --profile <path>` | Check live anchor detection |
| `debug-target <command> --profile <path>` | Generate annotated debug overlay |

### Common Options

- `--exact` / `--substring` — exact vs substring matching for `--contains`
- `--dry-run` / `--execute` — preview vs real input
- `--actionable-only` / `--all` — filter to interactive controls
- `--json` / `--table` — output format for list commands
- `--index <n>` — select among multiple matches (1-based)
- `--app <name>` — capture or target a specific app window
- `--port <n>` — CDP port (default 9222)
- `--radius <px>` — search box half-width for `whats-here` (default 96)

## Profile Types

### Visual Profiles

JSON files describing an app's visual layout relative to anchor images.

```json
{
  "type": "visual",
  "baseline": { "width": 720, "height": 572 },
  "anchors": {
    "primary": { "id": "titlebar_top_left", "path": "anchor_primary.png", "x": 0, "y": 0 }
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

Layout modes: `fixed_from_primary`, `top_right`, `bottom_right`, `center_scaled`.

### Semantic Profiles

JSON files storing element selectors from UIA or CDP — no screenshots or anchors needed.

```json
{
  "type": "semantic",
  "backend": "uia",
  "app_name": "Paint",
  "semantic_elements": {
    "oval": {
      "label": "Oval",
      "role": "ListItemControl",
      "action": "click"
    },
    "brushes": {
      "label": "Brushes",
      "role": "RadioButtonControl",
      "action": "click"
    },
    "fill": {
      "label": "Fill",
      "role": "ButtonControl",
      "action": "click"
    },
    "red": {
      "label": "Red",
      "role": "ListItemControl",
      "action": "click"
    }
  }
}
```

Key fields:
- `backend`: `"uia"` or `"cdp"` — which backend to query at runtime
- `semantic_elements[*].label`: element label for matching
- `semantic_elements[*].role`: UIA control type or ARIA role
- `semantic_elements[*].automation_id`: UIA automation ID (optional, for precise matching)
- `semantic_elements[*].selector`: CSS selector for CDP elements (optional)
- `semantic_elements[*].action`: `click`, `double_click`, `right_click`, `type`, `drag`, `scroll`, `hotkey`, `wait`
- `semantic_elements[*].drag_dx` / `drag_dy`: drag distance (for drag actions)
- `semantic_elements[*].hotkey`: key combination like `"ctrl+z"` (for hotkey actions)
- `semantic_elements[*].text`: default text to type (for type actions)

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
- Window capture and activation via `EnumWindows` / `GetWindowRect` / `SetForegroundWindow`
- Note: the `comtypes` gen cache can corrupt between runs; `uia-list` auto-clears it

### macOS

- **Accessibility** — uses System Events UI scripting
- **CV** — visual profile path with `screencapture` window capture
- Requires `Screen Recording` and `Accessibility` permissions

## Demos

- `demos/paint_car.py` — draws a car in MS Paint using a semantic profile built from the live UIA tree

## Project Status

Working today:
- JSON profile schema with Pydantic validation (visual and semantic types)
- Multi-state visual profiles with automatic state detection
- Semantic profiles built from UIA or CDP element trees
- 8 action types: click, double_click, right_click, type, drag, scroll, hotkey, wait
- macOS accessibility inspection via System Events
- Windows UIA inspection and direct click/type
- Windows CDP inspection and direct click/type via Playwright
- `probe` command for auto-detecting the best backend per app
- `whats-here` command for inspecting elements near the cursor
- `train --backend uia/cdp` for instant semantic profiles (no LLM tokens)
- Training asset generation from screenshots and grid overlays
- LLM-backed visual profile generation via the `llm` library
- Automatic window capture and activation on both macOS and Windows
- Template-matching anchor detection
- Debug overlay output for target validation

Not complete yet:
- Multi-monitor / DPI scale validation matrix (100%, 125%, 150%)
- CDP port is global — not aware of which app's WebView2 to connect to when multiple are running
- Hybrid profiles combining semantic + visual selectors
- LLM-assisted multi-state profile generation needs prompt refinement
- Anchor selection is still not strong enough for every app without retries

## Tooling

- `uv` for packaging, dependency management, and commands
- `ruff` for linting and formatting
- `pytest` for tests

## Troubleshooting

**`probe` recommends wrong backend**: some apps expose partial UIA trees. Run `uia-list --app <name> --actionable-only` and `cdp-list` separately to see what each finds.

**`whats-here` finds nothing**: try `--radius 200` to widen the search. Use `--app <name>` to limit to a specific app's elements. Some UIA elements may not have bounding boxes.

**`uia-list` fails or crashes**: the `comtypes` cache may be corrupt. The tool auto-clears it, but if issues persist, manually delete `.venv/Lib/site-packages/comtypes/gen/*`.

**`cdp-list` fails**: CDP must be enabled first. Run `cdp-setup --app <name>`, then close and reopen the app. Verify with `cdp-setup` (no args) — it should show `"listening": "true"`.

**`cdp-click --contains "X"` matches too broadly**: use `--exact` to require an exact label match instead of substring.

**Semantic `click` fails with keyword error**: ensure you're on the latest version — earlier builds passed unsupported kwargs to UIA click functions.

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
