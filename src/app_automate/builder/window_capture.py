from __future__ import annotations

import platform
import time
from pathlib import Path

from PIL import Image


def capture_app_window(app_name: str, output_path: Path) -> Path:
    from app_automate.vision.screenshots import capture_main_display

    _activate_app(app_name)
    time.sleep(0.4)
    left, top, width, height = front_window_bounds(app_name)
    full_screen_path = output_path.parent / "screen.png"
    capture_main_display(full_screen_path)
    image = Image.open(full_screen_path)
    crop = image.crop((left, top, left + width, top + height))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    crop.save(output_path)
    return output_path


def front_window_bounds(app_name: str) -> tuple[int, int, int, int]:
    system = platform.system()
    if system == "Darwin":
        return _front_window_bounds_macos(app_name)
    if system == "Windows":
        return _front_window_bounds_windows(app_name)
    raise RuntimeError(f"automatic app-window capture is not supported on {system}")


def _activate_app(app_name: str) -> None:
    system = platform.system()
    if system == "Darwin":
        _activate_app_macos(app_name)
    elif system == "Windows":
        _activate_app_windows(app_name)
    else:
        raise RuntimeError(f"app activation is not supported on {system}")


# --- macOS -----------------------------------------------------------------


def _front_window_bounds_macos(app_name: str) -> tuple[int, int, int, int]:
    position_raw = _osascript(
        'tell application "System Events" to tell process '
        f'"{app_name}" to get position of front window'
    )
    size_raw = _osascript(
        'tell application "System Events" to tell process '
        f'"{app_name}" to get size of front window'
    )
    left, top = _parse_pair(position_raw)
    width, height = _parse_pair(size_raw)
    return left, top, width, height


def _activate_app_macos(app_name: str) -> None:
    _osascript(f'tell application "{app_name}" to activate')


def _osascript(script: str) -> str:
    import subprocess

    result = subprocess.run(
        ["osascript", "-e", script],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip())
    return result.stdout.strip()


def _parse_pair(value: str) -> tuple[int, int]:
    parts = [part.strip() for part in value.split(",")]
    if len(parts) != 2:
        raise RuntimeError(f"unexpected window bounds response: {value}")
    return int(parts[0]), int(parts[1])


# --- Windows ---------------------------------------------------------------


def _ensure_dpi_aware() -> None:
    import ctypes

    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass


def _front_window_bounds_windows(app_name: str) -> tuple[int, int, int, int]:
    _ensure_dpi_aware()
    hwnds = _find_windows_by_title(app_name)
    if not hwnds:
        raise RuntimeError(f'no visible window found matching "{app_name}"')
    hwnd = hwnds[0]
    left, top, right, bottom = _get_window_rect(hwnd)
    return left, top, right - left, bottom - top


def activate_app(app_name: str) -> None:
    if platform.system() == "Windows":
        _activate_app_windows(app_name)
    else:
        import subprocess

        subprocess.run(
            ["osascript", "-e", f'tell application "{app_name}" to activate']
        )


def _activate_app_windows(app_name: str) -> None:
    import ctypes

    _ensure_dpi_aware()
    hwnds = _find_windows_by_title(app_name)
    if not hwnds:
        raise RuntimeError(f'no visible window found matching "{app_name}"')
    hwnd = hwnds[0]
    ctypes.windll.user32.ShowWindow(hwnd, 9)
    ctypes.windll.user32.SetForegroundWindow(hwnd)


def _find_windows_by_title(title: str) -> list:
    import ctypes
    import ctypes.wintypes

    matches: list = []

    @ctypes.WINFUNCTYPE(
        ctypes.wintypes.BOOL, ctypes.wintypes.HWND, ctypes.wintypes.LPARAM
    )
    def enum_callback(hwnd, _lparam):
        if ctypes.windll.user32.IsWindowVisible(hwnd):
            length = ctypes.windll.user32.GetWindowTextLengthW(hwnd)
            if length > 0:
                buf = ctypes.create_unicode_buffer(length + 1)
                ctypes.windll.user32.GetWindowTextW(hwnd, buf, length + 1)
                if title.lower() in buf.value.lower():
                    matches.append(hwnd)
        return True

    ctypes.windll.user32.EnumWindows(enum_callback, 0)
    return matches


def _get_window_rect(hwnd) -> tuple[int, int, int, int]:
    import ctypes
    import ctypes.wintypes

    rect = ctypes.wintypes.RECT()
    ctypes.windll.user32.GetWindowRect(hwnd, ctypes.byref(rect))
    return rect.left, rect.top, rect.right, rect.bottom
