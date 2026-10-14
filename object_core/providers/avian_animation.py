# SPDX-License-Identifier: GPL-3.0-or-later
"""Portable Avian idle, walk, and flight animation generation."""

from dataclasses import dataclass
from math import cos, isfinite, pi, radians
from typing import Tuple

from ..animation import IdleClip, RotationTrack
from ..animation.idle import TranslationTrack
from .avian_posture import folded_wing_tracks


@dataclass(frozen=True)
class GroundIdleClip(IdleClip):
    translations: tuple


def _root_reset(duration):
    return (TranslationTrack("root", ((0., (0., 0., 0.)), (duration, (0., 0., 0.)))),)


@dataclass(frozen=True)
class FlightClip:
    duration: float
    tracks: Tuple[RotationTrack, ...]
    translations: tuple = ()


def _validate(duration, strength, lower, upper):
    for name, value, minimum, maximum in (
        ("duration", duration, lower, upper),
        ("strength", strength, 0.1, 2.0),
    ):
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise TypeError(name + " must be a number")
        if not isfinite(value) or not minimum <= value <= maximum:
            raise ValueError(name + " must be between " + str(minimum) + " and " + str(maximum))


def _wave(duration, degrees, strength, samples=16, phase=0.0):
    return tuple(
        (duration * index / samples,
         radians(degrees) * strength * cos(2 * pi * index / samples + phase))
        for index in range(samples + 1)
    )


def generate_avian_idle(duration=4.0, strength=1.0):
    """Return a resting cycle with folded wings and head, neck and tail motion."""
    _validate(duration, strength, 1.0, 20.0)
    tracks = (
        RotationTrack("neck", (1.0, 0.0, 0.0), _wave(duration, 2.0, strength)),
        RotationTrack("head", (0.0, 0.0, 1.0), _wave(duration, 4.0, strength, phase=pi / 2)),
        RotationTrack("tail.1", (1.0, 0.0, 0.0), _wave(duration, 2.5, strength, phase=pi / 2)),
        RotationTrack("tail.2", (1.0, 0.0, 0.0), _wave(duration, 3.5, strength, phase=pi)),
    )
    return GroundIdleClip(float(duration), tracks + folded_wing_tracks(duration), _root_reset(duration))


def generate_avian_walk(duration=1.2, strength=1.0, values=None):
    """Return a parameter-aware walk solved against the weighted foot surface."""
    _validate(duration, strength, 0.5, 4.0)
    from .avian import AvianProvider
    from .avian_gait import generate_contact_walk
    provider = AvianProvider()
    if values is None:
        values = {p.key: p.default for p in provider.parameters}
    parameters = tuple(sorted(provider.dimensions(values).items()))
    return generate_contact_walk(float(duration), float(strength), parameters)


def generate_avian_flight(duration=0.9, strength=1.0):
    """Return a closed in-place wingbeat cycle with symmetric wings and body follow-through."""
    _validate(duration, strength, 0.5, 4.0)
    tracks = (
        RotationTrack("wing.upper.left", (0.0, 1.0, 0.0), _wave(duration, 48.0, strength)),
        RotationTrack("wing.upper.right", (0.0, 1.0, 0.0), _wave(duration, -48.0, strength)),
        RotationTrack("wing.lower.left", (0.0, 1.0, 0.0), _wave(duration, 24.0, strength, phase=pi / 5)),
        RotationTrack("wing.lower.right", (0.0, 1.0, 0.0), _wave(duration, -24.0, strength, phase=pi / 5)),
        RotationTrack("spine", (1.0, 0.0, 0.0), _wave(duration, 4.0, strength, phase=pi / 2)),
        RotationTrack("neck", (1.0, 0.0, 0.0), _wave(duration, 3.0, strength, phase=pi)),
        RotationTrack("tail.1", (1.0, 0.0, 0.0), _wave(duration, 6.0, strength, phase=pi / 2)),
        RotationTrack("tail.2", (1.0, 0.0, 0.0), _wave(duration, 9.0, strength, phase=3 * pi / 4)),
    )
    return FlightClip(float(duration), tracks, _root_reset(duration))
