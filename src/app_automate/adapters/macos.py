from __future__ import annotations

import platform

from app_automate.adapters.pyautogui_adapter import PyAutoGuiAdapter


class MacOSActionAdapter(PyAutoGuiAdapter):
    def __init__(self) -> None:
        if platform.system() != "Darwin":
            raise RuntimeError("MacOSActionAdapter requires macOS")
