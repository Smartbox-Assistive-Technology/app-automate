# Architecture

## Direction

The project is macOS-first for development and validation, with Windows as the target production platform. The core package keeps the profile model, CV matching, transform math, and CLI platform-neutral while isolating live input behind adapters.

## Phases

### Builder

- Capture a screenshot or window image.
- Optionally capture the front window of a live macOS app.
- Render a numbered grid overlay for LLM-assisted mapping.
- Send the grid image to a configurable LLM through Simon Willison's `llm` library.
- Save prompt input, screenshots, failed attempts, and generated profile assets.
- Validate profile JSON plus anchor crops before runtime use.
- Retry when the model returns weak, repeated, or oversized anchors.

### Runner

- Capture the current display in logical coordinates.
- Optionally inspect accessible controls through macOS UI scripting for apps that expose useful metadata.
- Find the current anchor position with template matching.
- Compute translation and scale from one or two anchors.
- Resolve named commands into coordinates using layout rules.
- Optionally render a debug overlay before clicking.
- Execute through an adapter.

## Runtime Flow

1. Load a saved profile.
2. Capture the main display or use a supplied screenshot.
3. Match the primary anchor template.
4. Match the secondary anchor template when the profile requires one.
5. Build a runtime transform from baseline anchor positions to live anchor positions.
6. Resolve the requested element through its layout mode.
7. Either:
   - return coordinates with `dry-run`
   - write annotated output with `debug-target`
   - click through the input adapter with `click`

## Builder Flow

1. Capture the target screenshot or app window.
2. Render the grid overlay used for mapping.
3. Build a structured prompt and schema for the LLM.
4. Send the grid image plus schema to the configured model.
5. Validate the returned ids, anchors, and crop boxes.
6. Crop anchor images from the source screenshot.
7. Re-run template matching on the cropped anchors to ensure they are unique enough.
8. Save the final profile or save failure artifacts if the attempt is rejected.

## Platform Strategy

- The current execution path is macOS-first because that is the active development environment.
- On macOS, the next native path is AX/Accessibility inspection for apps that expose usable roles, descriptions, and bounds.
- The live input path uses `pyautogui`, which works cross-platform but still depends on OS permissions and windowing behavior.
- Windows should get its own adapter layer and test matrix rather than relying only on the current generic `pyautogui` path.
- On Windows, UI Automation should be treated as a semantic backend where available, with CV profiles as the fallback for poorly-labelled apps.

## Settings Strategy

- Builder configuration lives in `app-automate.settings.toml`.
- The settings file is the intended production configuration path for model choice, API key, retry count, grid size, and anchor thresholds.
- `.env.local` is supported only as a local-development fallback for API keys.

## Coordinate System

- Runtime capture uses `mss`.
- On this Mac, `mss` returns logical display coordinates rather than Retina pixel coordinates.
- `pyautogui` also uses logical coordinates.
- Profile anchor images and live capture therefore need to be generated from the same logical coordinate space.

## Initial Layout Modes

- `fixed_from_primary`: fixed offset from the primary anchor
- `top_right`: fixed offset from the live secondary x-coordinate and live primary y-origin
- `bottom_right`: fixed offset from the live secondary anchor
- `center_scaled`: offset from the primary anchor, scaled between the two anchors

## Current Risks

- UI scripting and AX metadata quality vary significantly between apps.
- Template matching can degrade after theme changes, app updates, or mode changes.
- Some apps do not resize proportionally, which weakens `center_scaled`.
- A stable titlebar anchor does not guarantee that internal controls behave predictably across all window states.
- LLM output can still be structurally valid but semantically weak, especially in repeated or grid-heavy UIs.
- Multi-monitor behavior needs more validation, especially once Windows support is added.
