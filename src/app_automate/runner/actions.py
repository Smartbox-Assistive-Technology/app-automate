from __future__ import annotations

from app_automate.adapters.base import ActionAdapter
from app_automate.runner.runtime import ResolvedCommand


def click_resolved_command(adapter: ActionAdapter, command: ResolvedCommand) -> None:
    adapter.click(command.x, command.y)
