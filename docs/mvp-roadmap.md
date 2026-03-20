# MVP Roadmap

## Completed

- Bootstrap package with `uv`
- Add `ruff`, `pytest`, and a typed config model
- Add a real CLI with `train`, `inspect`, `list-elements`, `dry-run`, `locate-anchors`, `debug-target`, and `click`
- Capture screenshots on macOS
- Render grid overlays
- Wire the builder phase to a real LLM response pipeline
- Add settings-file-based LLM configuration
- Save prompt input plus failed-attempt artifacts for LLM mapping
- Add anchor crop tooling
- Auto-crop and validate anchors directly from profile-building workflows
- Add template matching over real screenshots
- Resolve elements using one-anchor and two-anchor transforms
- Add a debug overlay to visualize predicted click targets
- Enable live clicking on macOS after permission validation
- Add confidence thresholds and failure handling that surface better user-facing errors
- Add a command path to capture and crop a target app window automatically during training
- Exercise the flow against a real application profile (Photo Booth)

## Next

- Add a human review step for builder output before a profile is considered final
- Rank and score candidate anchors before accepting the LLM's proposal
- Improve prompt/schema guidance for repeated-grid interfaces
- Expand validation coverage across more real apps and window states
- Add richer settings support for multiple providers and profiles
- Validate additional apps with different layouts and control strategies

## Windows Path

- Add a Windows adapter
- Add Windows-native capture support during training
- Test DPI scaling and display scaling edge cases
- Validate capture and click behavior across multiple monitors
- Shift the main validation matrix from macOS to Windows

## Hard Problems

- Profiles that span multiple app modes
- Controls that animate or move independently from the window frame
- Layouts that do not scale linearly
- More robust anchor selection and re-training workflows
