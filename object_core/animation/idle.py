# SPDX-License-Identifier: GPL-3.0-or-later
"""Sampled idle rotations in rest armature coordinates, independent of bone roll."""

from dataclasses import dataclass
from math import cos, isfinite, pi, radians
from typing import Tuple


@dataclass(frozen=True)
class RotationTrack:
    bone: str
    axis: Tuple[float, float, float]
    # (seconds, angle in radians); adapters interpolate samples linearly.
    keys: Tuple[Tuple[float, float], ...]


@dataclass(frozen=True)
class TranslationTrack:
    """Bone displacement in rest armature axes, in centimeters."""
    bone: str
    keys: Tuple[Tuple[float, Tuple[float, float, float]], ...]


@dataclass(frozen=True)
class IdleClip:
    duration: float
    tracks: Tuple[RotationTrack, ...]


def generate_idle(duration=4.0, strength=1.0):
    """Return a closed, 32-segment breathing cycle with stationary legs/root."""
    for name, value, lower, upper in (("duration", duration, 1, 20), ("strength", strength, 0.1, 2)):
        if isinstance(value, bool) or not isinstance(value, (float, int)):
            raise TypeError(name + " must be a number")
        if not isfinite(value) or not lower <= value <= upper:
            raise ValueError(name + " must be between " + str(lower) + " and " + str(upper))
    tracks = []
    for bone, degrees in (("torso", 5.0), ("head", -3.0),
                          ("upper_arm.left", -10.0), ("upper_arm.right", -10.0)):
        keys = tuple((duration * i / 32, 0.0 if i in (0, 32) else
                      radians(degrees) * strength * (1 - cos(2 * pi * i / 32)) / 2)
                     for i in range(33))
        tracks.append(RotationTrack(bone, (1.0, 0.0, 0.0), keys))
    return IdleClip(float(duration), tuple(tracks))
