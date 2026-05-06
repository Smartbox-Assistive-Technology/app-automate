from __future__ import annotations

from app_automate.adapters.pyautogui_adapter import PyAutoGuiAdapter


def _ensure_dpi_aware() -> None:
    import ctypes

    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass


class WindowsInputAdapter(PyAutoGuiAdapter):
    """Windows input adapter with DPI-aware coordinate handling."""

    def __init__(self) -> None:
        _ensure_dpi_aware()
        super().__init__()
