from __future__ import annotations

from app_automate.config.models import AppProfile


def describe_profile(profile: AppProfile) -> str:
    lines = [
        f"Profile: {profile.profile_id}",
        f"App: {profile.app_name}",
        f"Platform hint: {profile.platform_hint}",
        f"Baseline: {profile.baseline.width}x{profile.baseline.height}",
        f"Primary anchor: {profile.anchors.primary.id}",
    ]
    if profile.anchors.secondary is not None:
        lines.append(f"Secondary anchor: {profile.anchors.secondary.id}")
    lines.append("Elements:")
    for element_id, element in sorted(profile.elements.items()):
        lines.append(
            f"  - {element_id}: {element.label} [{element.layout.value}] "
            f"({element.rel_x}, {element.rel_y})"
        )
    return "\n".join(lines)
