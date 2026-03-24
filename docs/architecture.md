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
3. **If the profile has multiple states, detect the active state:**
   - For each state, check its signature regions (tiny template matches at expected positions)
   - Use the first matching state's anchors and elements
   - Fall back to `default_state` if no state matches
4. Match the primary anchor template.
5. Match the secondary anchor template when the profile requires one.
6. Build a runtime transform from baseline anchor positions to live anchor positions.
7. Resolve the requested element through its layout mode.
8. Either:
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

## Multi-State Profiles

Apps often have distinct UI states. A camera connected/dis disconnected, dialogs appear, Each mode can be handled by:

1. Creating separate profiles for each state during `train`
2. Manually combine them into a multi-state profile
3. At runtime, use signature regions for detect the active state

### When to use:
- Create separate profiles for each app state using `train`
- Define check regions for each state (small template images of unique visual indicators)
- At training time, the LLM identifies these check regions
- Save signature crops alongside anchor images
- Validate each state's structure

### Multi-State Profile example

```json
{
  "profile_id": "camera-app-states",
  "app_name": "Camera App",
  "baseline": { "width": 800, "height": 600 },
  "default_state": "idle",
  "states": {
    "idle": {
      "id": "idle",
      "signature": {
        "description": "Camera disconnected, no dialog open",
        "check_regions": [
          {
            "path": "check_no_camera.png",
            "x": 50,
            "y": 100,
            "confidence_threshold": 0.9,
            "required": true
          }
        ]
      },
      "anchors": {
        "primary": {
          "id": "titlebar",
          "path": "anchor_primary.png",
          "x": 0,
          "y": 0
        },
      },
      "elements": {
        "connect_btn": {
          "label": "Connect",
          "rel_x": 100,
          "rel_y": 50,
          "layout": "fixed_from_primary",
        }
      }
    },
    "connected": {
      "id": "connected",
      "signature": {
        "description": "Camera connected and ready",
        "check_regions": [
          {
            "path": "check_camera_icon.png",
            "x": 50,
            "y": 100,
            "confidence_threshold": 0.9,
            "required": true
          }
        ]
      },
      "anchors": {
        "primary": {
          "id": "titlebar",
          "path": "anchor_primary.png",
          "x": 0,
          "y": 0
        },
        "secondary": {
          "id": "status_bar",
          "path": "anchor_secondary.png",
          "x": 700,
          "y": 550
        }
      },
      "elements": {
        "record_btn": {
          "label": "Record",
          "rel_x": 50,
          "rel_y": 20,
          "layout": "bottom_right"
        }
      }
    }
  }
}
```
    ]
  }
}
```

- **Check regions** are tiny crops (e.g., 20x20px) of distinctive visual indicators
- Each region is matched at its expected position (±5px tolerance)
- A state matches when all `required` regions match
- First matching state wins; fall back to `default_state`

### State Detection Performance

State detection is O(k) tiny template matches, where k = number of check regions across all states. This is dramatically cheaper than full-screen understanding:
- Single state check: ~5-10ms per region
- Typical multi-state profile: 3-5 states × 2-3 regions = ~50-150ms total
- Avoids expensive vision model calls on every interaction

### Backward Compatibility

Legacy single-state profiles continue to work:
- Profiles with top-level `anchors` and `elements` use the legacy path
- Profiles with `states` dict use the new multi-state path
- Cannot mix both structures in the same profile

## Current Risks

- UI scripting and AX metadata quality vary significantly between apps.
- Template matching can degrade after theme changes, app updates, or major mode changes.
- Some apps do not resize proportionally, which weakens `center_scaled`.
- A stable titlebar anchor does not guarantee that internal controls behave predictably across all window states.
- LLM output can still be structurally valid but semantically weak, especially in repeated or grid-heavy UIs.
- Multi-monitor behavior needs more validation, especially once Windows support is added.
- State signatures require careful selection of distinctive check regions; poorly chosen regions may cause false positives.
- Multi-state profile creation is currently manual; no automated workflow exists to combine single-state profiles.
