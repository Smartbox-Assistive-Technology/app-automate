# Outlook Windows Classic Example

This example now includes both:

- a visual fallback `profile.json`
- the Windows semantic UIA workflow for classic Outlook

The visual profile is intended for the existing anchor/CV runtime. The UIA commands are still the preferred path when Outlook exposes reliable controls.

Files in this directory:

- `profile.json`
- `anchor_primary.png`
- `screenshot.png`
- `screen.png`
- `grid.png`

The semantic flow uses these Windows UIA commands directly:

- `uia-list`
- `uia-click`
- `uia-type`

Validated on 2026-03-20 with:

- app window: `Inbox-will.wade@thinksmartbox.com - Outlook`
- compose window: `Untitled - Message (HTML)`

## Visual Profile

This profile was captured from the classic Outlook compose window with the `Message` ribbon visible.

Inspect the profile:

```bash
uv run app-automate inspect examples/profiles/outlook-windows-classic/profile.json
uv run app-automate list-elements examples/profiles/outlook-windows-classic/profile.json
```

Validate anchor detection against the captured full-screen image:

```bash
uv run app-automate locate-anchors --profile examples/profiles/outlook-windows-classic/profile.json --screenshot examples/profiles/outlook-windows-classic/screen.png
```

Preview a resolved target from the profile:

```bash
uv run app-automate dry-run "subject" --profile examples/profiles/outlook-windows-classic/profile.json --screenshot examples/profiles/outlook-windows-classic/screen.png
```

The visual profile includes:

- `send_btn`
- `to_field`
- `subject_field`
- `body_field`
- `attach_file_btn`

## Workflow

Inspect the main Outlook window:

```bash
uv run app-automate uia-list --app "Inbox-will.wade@thinksmartbox.com - Outlook" --max-depth 20 --actionable-only --json
```

Open a new draft:

```bash
uv run app-automate uia-click --app "Inbox-will.wade@thinksmartbox.com - Outlook" --contains "New Email" --max-depth 20 --execute
```

Type the subject:

```bash
uv run app-automate uia-type --app "Untitled - Message (HTML)" --contains "Subject" --control-type EditControl --max-depth 24 --text "App Automate Windows Outlook Test" --replace --execute
```

Type the body:

```bash
uv run app-automate uia-type --app "Untitled - Message (HTML)" --contains "Page 1 content" --control-type EditControl --max-depth 24 --text "Hello from app-automate on Windows via CLI UIA typing." --replace --execute
```

## Notes

- Outlook needed deeper traversal than the original UIA defaults.
- `New Email` behaves as an Office ribbon split button, so direct UIA invoke is more reliable than coordinate-only clicking.
- Outlook commits the subject after focus moves away from the subject field, so typing into the body is a good final validation step.
- The visual profile is based on a stable untitled compose window. If the ribbon mode or compose layout changes, retraining or anchor replacement may be needed.
