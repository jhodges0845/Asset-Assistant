# SPDX-License-Identifier: GPL-3.0-or-later
"""Human contact motion solved against the canonical weighted leg surface."""
from dataclasses import dataclass
from functools import lru_cache
from math import ceil, cos, pi
from ..animation.contact import ContactCycle
from ..animation.idle import IdleClip, RotationTrack, TranslationTrack
from ..animation.walk import WalkClip, generate_walk
from ..animation.run import generate_run
from ..animation.weighted_contact import LimbSurface


@dataclass(frozen=True)
class HumanIdleClip(IdleClip):
    translations: tuple


@dataclass(frozen=True)
class HumanContactClip(WalkClip):
    translations: tuple


def body_crouch(height, strength, running, phase):
    response = min(strength, 1.)
    return height * response * ((.045 if running else .020) + .008*(.5+.5*cos(4*pi*phase)))


def contact_schedule(duration, strength, height, running=False):
    return {side: ContactCycle(duration, height*(.30 if running else .22)*strength,
                              .42 if running else .65,
                              height*(.05 if running else .025)*min(strength,1.), phase)
            for side,phase in (('left',0.),('right',.5))}


@lru_cache(maxsize=24)
def generate_contact_motion(duration, strength, running, parameters, recipe_version):
    # Existing generators remain the single settings-validation boundary and
    # supply arm motion. Anatomy-specific contact replaces their leg tracks.
    generator = generate_run if running else generate_walk
    generator(duration, strength)
    base = generator(duration, min(strength, 1.))
    from .human import HumanProvider, _human_anatomy
    provider = HumanProvider()
    values = dict(parameters)
    anatomy = _human_anatomy(**values)
    if anatomy.recipe_version != recipe_version:
        raise ValueError('Human gait recipe identity mismatch')
    mesh = provider.mesh(values)
    weights = provider.skin_weights(mesh, values)[0]
    bones = {b.name:b for b in provider.skeleton(values).bones}
    regions = {r.name:r for r in anatomy.regions}
    height = values['height_cm']
    schedules = contact_schedule(duration, strength, height, running)
    samples = 128 * ceil(max(1.,strength))
    tracks = [RotationTrack(t.bone,t.axis,
                            tuple((time,angle*(.55 if t.bone.startswith('forearm.') else 1.))
                                  for time,angle in t.keys))
              for t in base.tracks if 'arm.' in t.bone]
    # Include liftoff explicitly so interpolation never spans a stance/swing boundary.
    phases = sorted({i/samples for i in range(samples)} |
                    {(c.touchdown_phase+c.duty_factor)%1. for c in schedules.values()})
    for side in ('left','right'):
        names = tuple(name+'.'+side for name in ('upper_leg','lower_leg','foot'))
        surface = LimbSurface(mesh, weights, regions['leg.'+side],
                              tuple(bones[n] for n in names), 0.)
        seed = (.3,-.6)
        keys = [[] for _ in names]
        for phase in phases:
            surface.crouch = body_crouch(height,strength,running,phase)
            target = schedules[side].target(phase)
            seed = surface.solve(surface.neutral_y+target.forward_cm, target.lift_cm+.02, seed)
            if seed[1] > 1e-7:
                raise ValueError('Human contact solver reversed knee flexion')
            for row,angle in zip(keys,seed+(-sum(seed),)):
                row.append((duration*phase,angle))
        for name,row in zip(names,keys):
            tracks.append(RotationTrack(name,(1.,0.,0.),tuple(row)+((duration,row[0][1]),)))
    roots = tuple((duration*i/samples,(0.,0.,-body_crouch(height,strength,running,i/samples)))
                  for i in range(samples))
    return HumanContactClip(duration,tuple(tracks),
                            (TranslationTrack('root',roots+((duration,roots[0][1]),)),))
