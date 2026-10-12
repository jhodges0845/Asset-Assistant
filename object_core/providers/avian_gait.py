# SPDX-License-Identifier: GPL-3.0-or-later
"""Alternating Avian steps solved against the canonical weighted surface."""
from dataclasses import dataclass
from functools import lru_cache

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
    crouch = height * .04 * strength
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
            target = schedules[chain.name].target(i / samples)
            seed = surface.solve(surface.neutral_y + target.forward_cm,
                                 target.lift_cm + .02, seed)
            for row, angle in zip(keys, seed + (-sum(seed),)):
                row.append((duration * i / samples, angle))
        for name, row in zip(chain.bones, keys):
            row.append((duration, row[0][1]))
            tracks.append(RotationTrack(name, (1., 0., 0.), tuple(row)))
    # Keep non-chain influences stationary: the contact solver assumes only
    # root translation outside the leg chain. Artist-authored motion stays editable.
    root = TranslationTrack('root', ((0., (0., 0., -crouch)),
                                     (duration, (0., 0., -crouch))))
    return ContactWalkClip(duration, tuple(tracks), (root,))
