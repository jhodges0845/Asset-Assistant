# SPDX-License-Identifier: GPL-3.0-or-later
"""Contact-driven canine joint rotations against the canonical weighted surface."""
from dataclasses import dataclass
from functools import lru_cache
from math import cos, sin, pi

from ..animation.contact import ContactCycle
from ..animation.weighted_contact import LimbSurface as _LimbSurface, paw_roll_forward_offset
from ..animation.idle import IdleClip, RotationTrack, TranslationTrack
from ..animation.walk import WalkClip
from ..animation.run import RunClip


@dataclass(frozen=True)
class ContactIdleClip(IdleClip):
    translations: tuple


@dataclass(frozen=True)
class ContactWalkClip(WalkClip):
    translations: tuple


@dataclass(frozen=True)
class ContactRunClip(RunClip):
    translations: tuple


def contact_schedule(duration, strength, height, running=False):
    # Deliberate four-beat walk; the run is a diagonal trot with flight intervals.
    phases = ((0, .5, .75, .25) if not running else (0, .5, .5, 0))
    names = ('leg.front.left', 'leg.front.right', 'leg.hind.left', 'leg.hind.right')
    return {name: ContactCycle(duration, height * (.30 if running else .20) * strength,
                              .4 if running else .65, height * (.10 if running else .06) * strength,
                              phase) for name, phase in zip(names, phases)}


LATERAL_COMPENSATION_BONES = ('fore_upper.left', 'fore_upper.right',
                              'hind_upper.left', 'hind_upper.right')


def _body_sway(schedules, width, height, strength, phase):
    """Small authored sway toward stance support; not a balance simulation."""
    support = []
    for name, schedule in schedules.items():
        local = (phase - schedule.touchdown_phase) % 1.
        weight = sin(pi * local / schedule.duty_factor)**2 if local < schedule.duty_factor else 0.
        support.append((-1. if name.endswith('.left') else 1., weight))
    total = sum(weight for _, weight in support)
    return .01 * min(width, height) * strength * sum(side * weight for side, weight in support) / max(total, 1e-12)


def _body_crouch(height, strength, running, phase):
    """Bounded stylized compression, in centimeters below the neutral root.

    Walk has a small pulse between each footfall. Trot compresses mid-stance
    and rises in flight. This is authored body response, not a dynamics model.
    """
    beats, center, amplitude = (2, .2, .014) if running else (4, .125, .006)
    compression = .5 + .5 * cos(2 * pi * beats * ((phase % 1.) - center))
    return height * strength * (.07 + amplitude * compression)


def _paw_pitch(schedule, phase, strength):
    """Late-stance heel lift, smoothly released into swing curl."""
    local = (phase - schedule.touchdown_phase) % 1.
    def smooth(value):
        t = max(0., min(1., value))
        return t*t*(3 - 2*t)
    if local <= schedule.duty_factor:
        return -.06 * strength * smooth((local / schedule.duty_factor - .75) / .25)
    u = (local - schedule.duty_factor) / (1. - schedule.duty_factor)
    return strength * (.12 * sin(pi * u) ** 2 - .06 * (1 - smooth(u / .3)))


@lru_cache(maxsize=24)
def generate_contact_clip(duration, strength, running, parameters, recipe_identity):
    from .quadruped import QuadrupedProvider, _construction
    from .quadruped_rigging import _build_quadruped_skeleton, generate_quadruped_skin_weights
    provider = QuadrupedProvider()
    mesh, anatomy = _construction(provider.dimensions(dict(parameters)))
    if (anatomy.recipe_id, anatomy.recipe_version) != recipe_identity:
        raise ValueError('Contact gait recipe identity does not match the construction')
    skeleton = _build_quadruped_skeleton(anatomy)
    weights = generate_quadruped_skin_weights(mesh, skeleton, anatomy=anatomy)[0]
    height = dict(parameters)['shoulder_height_cm']
    crouch = _body_crouch(height, strength, running, 0.)
    schedules = contact_schedule(duration, strength, height, running)
    bones = {b.name: b for b in skeleton.bones}
    regions = {r.name: r for r in anatomy.regions}
    tracks = []
    # Dense samples limit quaternion interpolation's deviation from solved
    # surface targets. A 0.02 cm clearance margin covers measured interpolation.
    samples = 128
    for chain in anatomy.chains:
        if chain.name not in schedules:
            continue
        surface = _LimbSurface(mesh, weights, regions[chain.name],
                               tuple(bones[n] for n in chain.bones), crouch)
        schedule = schedules[chain.name]
        seed = (-.3, .6) if '.front.' in chain.name else (.2, -.4)
        keys = [[] for _ in chain.bones]
        for i in range(samples):
            surface.crouch = _body_crouch(height, strength, running, i / samples)
            surface.paw_pitch = _paw_pitch(schedule, i / samples, strength) if len(chain.bones) == 3 else 0.
            target = schedule.target(i / samples)
            seed = surface.solve(surface.neutral_y + target.forward_cm + surface.roll_forward_offset(), target.lift_cm + .02, seed)
            angles = seed + ((surface.paw_pitch-sum(seed),) if len(chain.bones) == 3 else ())
            for row, angle in zip(keys, angles):
                row.append((duration * i / samples, angle))
        for name, row in zip(chain.bones, keys):
            row.append((duration, row[0][1]))
            tracks.append(RotationTrack(name, (1., 0., 0.), tuple(row)))
    from .quadruped_animation import _closed_wave
    for name, degrees, phase in (('neck', 2., pi), ('tail.1', 7., pi),
                                 ('tail.2', 10., 1.5*pi), ('tail.3', 12., 0.)):
        wave = _closed_wave(duration, degrees, strength, phase=phase)
        wave = wave[:-1] + ((duration, wave[0][1]),)
        tracks.append(RotationTrack(name, (1., 0., 0.) if name == 'neck' else (0., 0., 1.), wave))
    root_keys = tuple((duration * i / samples,
                       (0. if running else _body_sway(schedules, dict(parameters)['body_width_cm'], height, strength, i / samples),
                        0., -_body_crouch(height, strength, running, i / samples)))
                      for i in range(samples))
    translation = TranslationTrack('root', root_keys + ((duration, root_keys[0][1]),))
    # All limb rotations are about X. Equal opposite upper-limb translations
    # therefore preserve distal contact through linear interpolation as well.
    compensation = tuple(TranslationTrack(name, tuple((t, (-offset[0], 0., 0.))
                         for t, offset in translation.keys)) for name in LATERAL_COMPENSATION_BONES)
    return (ContactRunClip if running else ContactWalkClip)(duration, tuple(tracks), (translation,) + compensation)
