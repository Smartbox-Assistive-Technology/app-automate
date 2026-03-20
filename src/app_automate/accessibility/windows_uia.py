from __future__ import annotations

import platform
from dataclasses import dataclass
from typing import Any

from app_automate.accessibility.models import UIElement

ACTIONABLE_CONTROL_TYPES = {
    "ButtonControl",
    "CheckBoxControl",
    "ComboBoxControl",
    "EditControl",
    "HyperlinkControl",
    "ListItemControl",
    "MenuItemControl",
    "RadioButtonControl",
    "SplitButtonControl",
    "TabItemControl",
    "TreeItemControl",
}


@dataclass(slots=True)
class UIAElement(UIElement):
    @property
    def actionable(self) -> bool:
        return self.class_name in ACTIONABLE_CONTROL_TYPES


def list_app_ui_elements(
    app_name: str,
    *,
    max_depth: int = 3,
    actionable_only: bool = False,
) -> list[UIAElement]:
    _ensure_windows()
    automation = _import_uiautomation()
    windows = automation.GetRootControl().GetChildren()
    matching_windows = [
        window
        for window in windows
        if _matches_app_window(window, app_name)
    ]
    if not matching_windows:
        raise RuntimeError(f'no visible UIA windows found for app "{app_name}"')

    elements: list[UIAElement] = []
    for index, window in enumerate(matching_windows, start=1):
        window_path = f"window[{index}]"
        root = _to_element(window, path=window_path, depth=0)
        if root is None:
            continue
        elements.append(root)
        elements.extend(
            _walk_children(
                window,
                path=window_path,
                depth=1,
                max_depth=max_depth,
            )
        )

    if actionable_only:
        return [element for element in elements if element.actionable]
    return elements


def find_matching_elements(
    app_name: str,
    *,
    contains: str,
    control_type: str | None = None,
    max_depth: int = 3,
    actionable_only: bool = True,
    enabled_only: bool = True,
) -> list[UIAElement]:
    needle = contains.lower()
    elements = list_app_ui_elements(
        app_name,
        max_depth=max_depth,
        actionable_only=actionable_only,
    )
    matches = [
        element
        for element in elements
        if _matches_element(element, needle)
        and (control_type is None or element.class_name == control_type)
        and (not enabled_only or element.enabled is not False)
    ]
    return sorted(
        matches,
        key=lambda element: (
            element.label.lower() != needle,
            element.depth,
            element.x if element.x is not None else 0,
            element.y if element.y is not None else 0,
        ),
    )


def _walk_children(
    control: Any,
    *,
    path: str,
    depth: int,
    max_depth: int,
) -> list[UIAElement]:
    if depth > max_depth:
        return []

    children = list(control.GetChildren())
    elements: list[UIAElement] = []
    for index, child in enumerate(children, start=1):
        child_path = f"{path} > child[{index}]"
        element = _to_element(child, path=child_path, depth=depth)
        if element is None:
            continue
        elements.append(element)
        elements.extend(
            _walk_children(
                child,
                path=child_path,
                depth=depth + 1,
                max_depth=max_depth,
            )
        )
    return elements


def _to_element(control: Any, *, path: str, depth: int) -> UIAElement | None:
    try:
        rect = control.BoundingRectangle
    except Exception:
        rect = None

    try:
        child_count = len(control.GetChildren())
    except Exception:
        child_count = 0

    left = _safe_int(getattr(rect, "left", None))
    top = _safe_int(getattr(rect, "top", None))
    right = _safe_int(getattr(rect, "right", None))
    bottom = _safe_int(getattr(rect, "bottom", None))

    width = None
    height = None
    if None not in {left, top, right, bottom}:
        width = right - left
        height = bottom - top

    return UIAElement(
        path=path,
        class_name=_safe_str(getattr(control, "ControlTypeName", None))
        or _safe_str(getattr(control, "ClassName", None))
        or "UnknownControl",
        role=_safe_str(getattr(control, "LocalizedControlType", None)),
        subrole=_safe_str(getattr(control, "ClassName", None)),
        description=_safe_str(getattr(control, "HelpText", None)),
        title=None,
        name=_safe_str(getattr(control, "Name", None)),
        automation_id=_safe_str(getattr(control, "AutomationId", None)),
        x=left,
        y=top,
        width=width,
        height=height,
        enabled=_safe_bool(getattr(control, "IsEnabled", None)),
        depth=depth,
        child_count=child_count,
    )


def _matches_app_window(control: Any, app_name: str) -> bool:
    name = _safe_str(getattr(control, "Name", None)) or ""
    class_name = _safe_str(getattr(control, "ClassName", None)) or ""
    automation_id = _safe_str(getattr(control, "AutomationId", None)) or ""
    process_name = _safe_process_name(control)
    needle = app_name.lower()
    return any(
        needle in value.lower()
        for value in (name, class_name, automation_id, process_name)
        if value
    )


def _safe_process_name(control: Any) -> str | None:
    try:
        return _safe_str(control.ProcessName)
    except Exception:
        return None


def _matches_element(element: UIAElement, needle: str) -> bool:
    haystacks = [
        element.label,
        element.class_name,
        element.role or "",
        element.subrole or "",
        element.automation_id or "",
    ]
    return any(needle in value.lower() for value in haystacks if value)


def _import_uiautomation() -> Any:
    try:
        import uiautomation as automation
    except ImportError as exc:
        raise RuntimeError(
            "Windows UIA support requires the optional 'uiautomation' package"
        ) from exc
    return automation


def _safe_str(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _safe_int(value: object) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _safe_bool(value: object) -> bool | None:
    if value is None:
        return None
    return bool(value)


def _ensure_windows() -> None:
    if platform.system() != "Windows":
        raise RuntimeError("Windows UIA inspection is only available on Windows")
