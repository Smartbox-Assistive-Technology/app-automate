# Windows Integration

This document is the concrete work plan for moving `app-automate` from the current macOS-first prototype to a Windows-first runtime.

## Current Status

As of 2026-03-20, the Windows UIA path is implemented and live-tested with `uv` against:

- Visual Studio Code
- classic Outlook for Windows
- new Outlook for Windows

Validated commands now include:

- `uia-list`
- `uia-click`
- `uia-type`

The most reliable Windows typing path is direct UIA focus plus UIA `SendKeys`. Mouse-only typing through `pyautogui` is not reliable enough for Outlook compose fields.

## Goal

On Windows, the runtime should support two backends:

1. Semantic backend
   Use UI Automation when the target app exposes usable controls, names, roles, and bounds.

2. Visual backend
   Use the existing profile + anchor + CV flow when UIA is missing, incomplete, unstable, or badly labelled.

The project should keep both. UIA is not a replacement for CV. It is the preferred fast path when it works.

## What Already Transfers Cleanly

The following parts of the codebase should move to Windows with little or no redesign:

- profile schema in `src/app_automate/config`
- LLM builder flow in `src/app_automate/builder`
- anchor scoring and profile validation
- transform math in `src/app_automate/runner/transform.py`
- element resolution and debug overlays
- `uv` / `ruff` / `pytest` project tooling
- settings-file-based model configuration

Those pieces are already platform-neutral.

## What Must Be Replaced Or Added

### 1. Windows semantic backend

Add a Windows accessibility/UIA module similar in spirit to the macOS AX module.

Recommended first target:
- a module under `src/app_automate/accessibility/windows_uia.py`

Responsibilities:
- enumerate visible UIA elements for a target app/window
- capture role, name, automation id, bounds, enabled state, and control type
- provide a filtered query interface like:
  - `find_matching_elements(app_name, contains=..., control_type=...)`
- support later action execution against a matched element

Likely implementation candidates:
- `Python-UIAutomation-for-Windows`
- direct Windows UI Automation wrappers if needed later

### 2. Windows execution adapter

The current live input path uses `pyautogui`, which may work for basic input on Windows, but Windows needs its own tested adapter.

Add:
- `src/app_automate/adapters/windows_input.py`

Responsibilities:
- left click
- right click
- double click
- drag
- scroll
- eventually keyboard input

At first this can still use `pyautogui` under the hood if it behaves well enough, but the adapter boundary should exist from day one.

### 3. Windows capture path

Training and runtime need Windows-native validation for:
- full-screen capture
- window-specific capture during training
- DPI scaling
- mixed-scale multi-monitor setups

Tasks:
- validate `mss` coordinate behavior on Windows
- confirm that capture coordinates and input coordinates match
- if needed, add a Windows-specific capture helper under `src/app_automate/builder/window_capture_windows.py`

### 4. Windows semantic CLI parity

Mirror the new macOS AX commands with Windows UIA commands.

Target CLI parity:
- `uia-list --app "App Name"`
- `uia-list --app "App Name" --actionable-only`
- `uia-click --app "App Name" --contains "Insert" --dry-run`
- `uia-click --app "App Name" --contains "Insert" --action right-click --execute`
- `uia-type --app "App Name" --contains "Search" --text "hello" --execute`

The command shape should stay close to:
- `ax-list`
- `ax-click`

That keeps the UX consistent across platforms.

## Recommended Backend Strategy

Use this priority order at runtime:

1. Windows UIA backend
   Use when the app exposes stable names, control types, and bounds.

2. Visual profile backend
   Use when UIA is missing, generic, wrong, or absent.

3. Hybrid mode
   Long term, allow a profile to combine both:
   - semantic selectors for accessible controls
   - visual anchors for inaccessible controls in the same app

This is the intended end state.

## Immediate Implementation Steps

### Phase 1: inspection only

Build a Windows UIA inspector before adding actions.

Deliverables:
- `windows_uia.py`
- `uia-list` CLI command
- JSON output with:
  - name
  - control type
  - automation id
  - bounds
  - enabled state
  - path or parent context

Success condition:
- run `uia-list` against 2-3 Windows apps and get useful output

### Phase 2: semantic actions

Add:
- `uia-click`

Support:
- click
- right-click
- double-click
- drag
- scroll

Success condition:
- use `uia-click` on at least one app with good UIA support
- use `uia-type` on at least one app with editable UIA fields

### Phase 3: training/capture validation

Make the visual path reliable on Windows.

Tasks:
- validate `train --app ...` behavior on Windows
- confirm `mss` plus input coordinates align at 100%, 125%, and 150% scale
- validate on single-monitor and dual-monitor setups

Success condition:
- train and run one accessible app and one non-accessible app successfully

### Phase 4: hybrid routing

Add runtime selection logic:
- semantic first
- CV fallback

This may later become:
- `--backend auto|uia|cv`

## Validation Matrix

Minimum Windows matrix:

- Windows 11
- display scale:
  - 100%
  - 125%
  - 150%
- monitor setups:
  - single monitor
  - dual monitor
- app categories:
  - native accessible app
  - Electron app with partial UIA
  - app with poor/no UIA and visible stable controls

Recommended validation apps:
- one Microsoft Office app
- one browser or Electron app
- one app with poor accessibility and stable visuals

Confirmed working examples:

- classic Outlook compose workflow
- VS Code caption-button targeting
- new Outlook tab targeting

## Risks Specific To Windows

- DPI scaling can desynchronize capture and input coordinates.
- Some Electron apps expose partial or inconsistent UIA trees.
- Some apps expose controls without useful labels.
- Multi-monitor setups may shift coordinate origins or scaling unexpectedly.
- `pyautogui` may be acceptable for MVP input, but it should not be treated as the final Windows strategy without validation.

## Code Areas To Touch

Likely files/modules:

- add `src/app_automate/accessibility/windows_uia.py`
- add `src/app_automate/adapters/windows_input.py`
- extend `src/app_automate/cli.py`
- extend docs
- possibly add Windows-specific builder capture helpers

Likely existing code to reuse:

- `src/app_automate/accessibility/macos_ax.py`
- `src/app_automate/adapters/base.py`
- `src/app_automate/adapters/pyautogui_adapter.py`
- `src/app_automate/builder/training.py`
- `src/app_automate/vision`

## Suggested First Week On Windows

1. Set up `uv sync` and confirm the repo runs unchanged.
2. Implement `uia-list`.
3. Test `uia-list` on 3 apps.
4. Implement `uia-click --dry-run`.
5. Validate one real `uia-click`.
6. Validate `mss` capture coordinates against input coordinates.
7. Test the current visual builder on one Windows app.
8. Document the first scaling issue you hit before trying to fix everything.

## Definition Of Done For Initial Windows Support

Initial Windows support is good enough when all of these are true:

- `uia-list` works on at least one accessible Windows app
- `uia-click` works on at least one accessible Windows app
- `uia-type` works on at least one accessible Windows app with editable fields
- the visual profile path works on at least one poor-accessibility Windows app
- coordinate alignment is verified at more than one display scale
- docs explain when to use UIA versus CV

That is the bar for a real Windows milestone, not just a port.

## Example: Classic Outlook Compose

This was validated live on 2026-03-20 against classic Outlook for Windows.

1. Inspect actionable controls:

```bash
uv run app-automate uia-list --app "Inbox-will.wade@thinksmartbox.com - Outlook" --max-depth 20 --actionable-only --json
```

2. Open a new draft:

```bash
uv run app-automate uia-click --app "Inbox-will.wade@thinksmartbox.com - Outlook" --contains "New Email" --max-depth 20 --execute
```

3. Type a subject into the compose window:

```bash
uv run app-automate uia-type --app "Untitled - Message (HTML)" --contains "Subject" --control-type EditControl --max-depth 24 --text "App Automate Windows Outlook Test" --replace --execute
```

4. Type the message body:

```bash
uv run app-automate uia-type --app "App Automate Windows Outlook Test - Message (HTML)" --contains "Page 1 content" --control-type EditControl --max-depth 24 --text "Hello from app-automate on Windows via UIA SendKeys." --replace --execute
```

Notes:

- The compose window title changes after the subject is entered.
- Outlook commits the subject once focus moves off the subject field, so the body step is a good verification point.
- Classic Outlook needed deeper traversal than the original defaults; `--max-depth 20` and `--max-depth 24` were used for reliable discovery.
- For this workflow, direct UIA invoke plus UIA `SendKeys` was reliable; generic mouse typing was not.
