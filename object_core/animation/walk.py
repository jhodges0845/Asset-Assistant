# SPDX-License-Identifier: GPL-3.0-or-later
"""Portable in-place Human walk-cycle generation."""

from dataclasses import dataclass
from math import isfinite, radians
from typing import Tuple

from .idle import RotationTrack


@dataclass(frozen=True)
class WalkClip:
    duration: float
    tracks: Tuple[RotationTrack, ...]


def _keys(duration, degrees, strength):
    quarter = duration / 4
    return tuple(
        (time, radians(angle) * strength)
        for time, angle in (
            (0.0, degrees),
            (quarter, 0.0),
            (2 * quarter, -degrees),
            (3 * quarter, 0.0),
            (duration, degrees),
        )
    )


def _knee_keys(duration, degrees, strength):
    """Flex backward only; phase comes from the hip cycle, never bend sign."""
    return tuple((time, min(0.0, angle))
                 for time, angle in _keys(duration, degrees, strength))


def generate_walk(duration=1.2, strength=1.0):
    """Return a closed in-place walk cycle with opposing arm/leg swing."""
    for name, value, lower, upper in (("duration", duration, 0.5, 4), ("strength", strength, 0.1, 2)):
        if isinstance(value, bool) or not isinstance(value, (float, int)):
            raise TypeError(name + " must be a number")
        if not isfinite(value) or not lower <= value <= upper:
            raise ValueError(name + " must be between " + str(lower) + " and " + str(upper))

    tracks = (
        RotationTrack("upper_leg.left", (1.0, 0.0, 0.0), _keys(duration, 24.0, strength)),
        RotationTrack("upper_leg.right", (1.0, 0.0, 0.0), _keys(duration, -24.0, strength)),
        RotationTrack("lower_leg.left", (1.0, 0.0, 0.0), _knee_keys(duration, -14.0, strength)),
        RotationTrack("lower_leg.right", (1.0, 0.0, 0.0), _knee_keys(duration, 14.0, strength)),
        RotationTrack("upper_arm.left", (1.0, 0.0, 0.0), _keys(duration, -18.0, strength)),
        RotationTrack("upper_arm.right", (1.0, 0.0, 0.0), _keys(duration, 18.0, strength)),
        RotationTrack("torso", (0.0, 0.0, 1.0), _keys(duration, 3.0, strength)),
    )
    return WalkClip(float(duration), tracks)
