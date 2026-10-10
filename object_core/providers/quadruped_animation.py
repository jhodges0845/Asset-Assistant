# SPDX-License-Identifier: GPL-3.0-or-later
"""Portable quadruped animation generation."""

from math import cos, isfinite, pi, radians

from ..animation import RotationTrack


def _validate(duration, strength, duration_min, duration_max):
    for name, value, lower, upper in (
        ("duration", duration, duration_min, duration_max),
        ("strength", strength, 0.1, 2.0),
    ):
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise TypeError(name + " must be a number")
        if not isfinite(value) or not lower <= value <= upper:
            raise ValueError(name + " must be between " + str(lower) + " and " + str(upper))


def _closed_wave(duration, degrees, strength, samples=16, phase=0.0):
    return tuple(
        (
            duration * index / samples,
            radians(degrees) * strength * cos(2 * pi * index / samples + phase),
        )
        for index in range(samples + 1)
    )


def generate_quadruped_idle(duration=4.0, strength=1.0):
    """Return a subtle closed quadruped idle with breathing, head and tail motion."""
    _validate(duration, strength, 1.0, 20.0)
    tracks = (
        RotationTrack("spine", (1.0, 0.0, 0.0), _closed_wave(duration, 2.0, strength)),
        RotationTrack("neck", (1.0, 0.0, 0.0), _closed_wave(duration, 2.5, strength, phase=pi)),
        RotationTrack("head", (0.0, 0.0, 1.0), _closed_wave(duration, 2.0, strength, phase=pi / 2)),
        RotationTrack("tail.1", (0.0, 0.0, 1.0), _closed_wave(duration, 4.0, strength, phase=pi / 2)),
        RotationTrack("tail.2", (0.0, 0.0, 1.0), _closed_wave(duration, 6.0, strength, phase=pi)),
        RotationTrack("tail.3", (0.0, 0.0, 1.0), _closed_wave(duration, 8.0, strength, phase=3 * pi / 2)),
    )
    # Explicit zero translations prevent crouch and lateral offsets leaking when Blender's native action
    # selector (or the clip list) switches from a contact gait back to Idle.
    from .quadruped_gait import ContactIdleClip, LATERAL_COMPENSATION_BONES
    from ..animation.idle import TranslationTrack
    return ContactIdleClip(float(duration), tracks,
                           tuple(TranslationTrack(name, ((0., (0., 0., 0.)),
                                 (float(duration), (0., 0., 0.))))
                                 for name in ('root',) + LATERAL_COMPENSATION_BONES))


def _contact_clip(duration, strength, running, values):
    from .quadruped import QUADRUPED_PARAMETERS
    from .quadruped_anatomy import CanineRecipe
    from .quadruped_gait import generate_contact_clip
    parameters = {p.key: p.default for p in QUADRUPED_PARAMETERS} if values is None else values
    return generate_contact_clip(float(duration), float(strength), running,
                                 tuple(sorted(parameters.items())),
                                 (CanineRecipe.recipe_id, CanineRecipe.recipe_version))


def generate_quadruped_walk(duration=1.2, strength=1.0, values=None):
    """Return a contact-solved four-beat walk for the supplied proportions."""
    _validate(duration, strength, 0.5, 4.0)
    return _contact_clip(duration, strength, False, values)


def generate_quadruped_run(duration=0.64, strength=1.0, values=None):
    """Return a contact-solved diagonal running trot with flight intervals."""
    _validate(duration, strength, 0.3, 2.0)
    return _contact_clip(duration, strength, True, values)
