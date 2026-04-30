"""Orientation helpers shared across API/worker modules."""

from __future__ import annotations


def normalize_orientation(value: str | None, default: str = "VERTICAL") -> str:
    """Normalize orientation aliases to VERTICAL/HORIZONTAL.

    Accepted aliases include:
    - VERTICAL: VERTICAL, PORTRAIT, 9:16, 9/16, *_PORTRAIT
    - HORIZONTAL: HORIZONTAL, LANDSCAPE, 16:9, 16/9, *_LANDSCAPE
    """
    if not value:
        return default
    upper = str(value).strip().upper().replace(" ", "")

    vertical_aliases = {
        "VERTICAL",
        "PORTRAIT",
        "9:16",
        "9/16",
        "VIDEO_ASPECT_RATIO_PORTRAIT",
        "IMAGE_ASPECT_RATIO_PORTRAIT",
    }
    horizontal_aliases = {
        "HORIZONTAL",
        "LANDSCAPE",
        "16:9",
        "16/9",
        "VIDEO_ASPECT_RATIO_LANDSCAPE",
        "IMAGE_ASPECT_RATIO_LANDSCAPE",
    }

    if upper in vertical_aliases or upper.endswith("_PORTRAIT"):
        return "VERTICAL"
    if upper in horizontal_aliases or upper.endswith("_LANDSCAPE"):
        return "HORIZONTAL"
    return default


def orientation_prefix(value: str | None, default: str = "VERTICAL") -> str:
    """Return DB field prefix for the given orientation."""
    return "vertical" if normalize_orientation(value, default=default) == "VERTICAL" else "horizontal"

