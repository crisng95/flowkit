"""User-facing Omni model labels and Flow credit preflight.

Ported from the alias and duration work in GTAI-1/flow-mcp PR #30.
This module handles UI-facing labels and published credit preflight.
"""
from __future__ import annotations

import re

OMNI_11_DURATIONS = (4, 6, 8, 10)
OMNI_12_DURATIONS = tuple(range(3, 16))


def is_omni_12_label(value: str) -> bool:
    tokens = re.findall(r"[a-z]+|[0-9]+(?:\.[0-9]+)*", str(value).lower())
    return all(term in tokens for term in ("omni", "1.2", "flash"))


def matches_model_label(shown: str, requested: str) -> bool:
    if is_omni_12_label(requested):
        return is_omni_12_label(shown)
    return str(requested).strip().casefold() in str(shown).casefold()


def estimate_omni_12_credits(duration: int, resolution: str) -> int:
    """Flow Nov-2026 posted per-second pricing for one clip."""
    if type(duration) is not int or duration not in OMNI_12_DURATIONS:
        raise ValueError("Omni 1.2 supports integer seconds from 3 to 15")
    if resolution not in ("360p", "720p"):
        raise ValueError("Omni 1.2 resolution must be 360p or 720p")
    unit = 1 if resolution == "360p" else 3
    return unit * min(duration, 10) + 2 * unit * max(0, duration - 10)
