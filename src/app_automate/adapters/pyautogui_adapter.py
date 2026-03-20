from __future__ import annotations

import pyautogui


class PyAutoGuiAdapter:
    def click(self, x: float, y: float) -> None:
        pyautogui.click(x=x, y=y)

    def right_click(self, x: float, y: float) -> None:
        pyautogui.click(x=x, y=y, button="right")

    def double_click(self, x: float, y: float) -> None:
        pyautogui.doubleClick(x=x, y=y)

    def scroll(self, x: float, y: float, clicks: int) -> None:
        pyautogui.moveTo(x=x, y=y)
        pyautogui.scroll(clicks)

    def drag(
        self,
        start_x: float,
        start_y: float,
        end_x: float,
        end_y: float,
        *,
        duration: float = 0.2,
        button: str = "left",
    ) -> None:
        pyautogui.moveTo(x=start_x, y=start_y)
        pyautogui.dragTo(x=end_x, y=end_y, duration=duration, button=button)

    def write_text(self, text: str, *, interval: float = 0.0) -> None:
        pyautogui.write(text, interval=interval)

    def hotkey(self, *keys: str) -> None:
        pyautogui.hotkey(*keys)
