from __future__ import annotations

from typing import Protocol


class ActionAdapter(Protocol):
    def click(self, x: float, y: float) -> None: ...

    def right_click(self, x: float, y: float) -> None: ...

    def double_click(self, x: float, y: float) -> None: ...

    def scroll(self, x: float, y: float, clicks: int) -> None: ...

    def drag(
        self,
        start_x: float,
        start_y: float,
        end_x: float,
        end_y: float,
        *,
        duration: float = 0.2,
        button: str = "left",
    ) -> None: ...
