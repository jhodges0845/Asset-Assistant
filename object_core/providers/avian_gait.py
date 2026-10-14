# SPDX-License-Identifier: GPL-3.0-or-later
"""Alternating Avian steps solved against the canonical weighted surface."""
from dataclasses import dataclass
from functools import lru_cache
from math import cos, pi

from ..animation.contact import ContactCycle
from ..animation.idle import RotationTrack, TranslationTrack
from ..animation.walk import WalkClip
from ..animation.weighted_contact import LimbSurface


@dataclass(frozen=True)
class ContactWalkClip(WalkClip):
    translations: tuple


def contact_schedule(duration, strength, height):
    return {name: ContactCycle(duration, height * .08 * strength, .65,
                               height * .035 * strength, phase)
            for name, phase in (('leg.left', 0.), ('leg.right', .5))}


def body_crouch(height, strength, phase):
    """Small two-step vertical response; authored timing, not a balance simulation.

    Compress during double support and rise during single support. Preserve the
    proven 4% maximum compression even when the artist increases step strength.
    """
    compression = .5 + .5*cos(4*pi*((phase % 1.)-.075))
    return height * min(strength,1.) * (.028 + .012*compression)


@lru_cache(maxsize=24)
def generate_contact_walk(duration, strength, parameters):
    from .avian import AvianProvider
    provider = AvianProvider()
    values = dict(parameters)
    mesh, anatomy = provider.mesh(values), provider.anatomy(values)
    weights = provider.skin_weights(mesh, values)[0]
    bones = {bone.name: bone for bone in provider.skeleton(values).bones}
    regions = {region.name: region for region in anatomy.regions}
    height = values['body_height_cm']
    crouch = body_crouch(height, strength, 0.)
    schedules = contact_schedule(duration, strength, height)
    tracks = []
    samples = 128
    for chain in anatomy.chains:
        if chain.name not in schedules:
            continue
        surface = LimbSurface(mesh, weights, regions[chain.name],
                              tuple(bones[name] for name in chain.bones), crouch)
        seed = (.25, -.5)
        keys = [[] for _ in chain.bones]
        for i in range(samples):
            surface.crouch = body_crouch(height, strength, i / samples)
            target = schedules[chain.name].target(i / samples)
            seed = surface.solve(surface.neutral_y + target.forward_cm,
                                 target.lift_cm + .02, seed)
            for row, angle in zip(keys, seed + (-sum(seed),)):
                row.append((duration * i / samples, angle))
        for name, row in zip(chain.bones, keys):
            row.append((duration, row[0][1]))
            tracks.append(RotationTrack(name, (1., 0., 0.), tuple(row)))
    # Keep non-leg influences on the legs stationary. Authored wing ownership
    # excludes the legs, so the held fold cannot change the contact solution.
    root_keys = tuple((duration*i/samples, (0.,0.,-body_crouch(height,strength,i/samples)))
                      for i in range(samples))
    root = TranslationTrack('root',root_keys+((duration,root_keys[0][1]),))
    from .avian_posture import folded_wing_tracks
    return ContactWalkClip(duration, tuple(tracks) + folded_wing_tracks(duration), (root,))
