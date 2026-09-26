# SPDX-License-Identifier: GPL-3.0-or-later
"""Tiny Human proof: existing rest landmarks plus authored bilateral arm ownership.

This describes the current Human, without moving the surface or rig algorithm.
The full Human recipe remains a later migration after the two-body-plan review.
"""
from dataclasses import dataclass

from ..anatomy import AnatomyRegion, JointChain, Landmark, ResolvedAnatomy
from ..models import BodyType, HumanoidSpec
from ..proportions import generate_proportions
from ..rigging.surface_human import surface_skeleton


def authored_arm_regions(arm_indices):
    return tuple(AnatomyRegion('arm.' + side, 'human', indices)
                 for side, indices in arm_indices)


@dataclass(frozen=True)
class HumanArmRecipe:
    """Provider-owned proof; topology comes from the existing surface builder."""
    regions: tuple
    recipe_id = 'human.arm-proof'
    recipe_version = '1'

    def __post_init__(self):
        regions = tuple(self.regions)
        if {r.name for r in regions} != {'arm.left', 'arm.right'} or len(regions) != 2:
            raise ValueError('Human arm proof requires both authored arm regions')
        if any(r.mesh_part != 'human' for r in regions):
            raise ValueError('Human arm regions must belong to the human mesh part')
        object.__setattr__(self, 'regions', regions)

    def resolve(self, values):
        spec = HumanoidSpec(values['height_cm'], values['weight_kg'], BodyType(values['body_type']))
        skeleton = surface_skeleton(generate_proportions(spec))
        bones = {bone.name: bone for bone in skeleton.bones}
        landmarks = [Landmark('pelvis', bones['root'].head),
                     Landmark('root.tip', bones['root'].tail),
                     Landmark('shoulder.center', bones['torso'].tail)]
        chains = [JointChain('root', ('pelvis', 'root.tip'), ('root',)),
                  JointChain('torso', ('pelvis', 'shoulder.center'), ('torso',), 'root')]
        for side in ('left', 'right'):
            names = tuple(name + '.' + side for name in ('shoulder', 'elbow', 'wrist', 'hand.tip'))
            bone_names = tuple(name + '.' + side for name in ('upper_arm', 'forearm', 'hand'))
            points = [bones[name].head for name in bone_names] + [bones[bone_names[-1]].tail]
            landmarks.extend(Landmark(name, point) for name, point in zip(names, points))
            chains.append(JointChain('arm.' + side, names, bone_names, 'torso',
                                     (0, 1, 0), 'arm'))
        return ResolvedAnatomy(
            self.recipe_id, self.recipe_version,
            (('height_cm', float(spec.height_cm)), ('weight_kg', float(spec.weight_kg)),
             ('body_type', spec.body_type.value)),
            landmarks=landmarks, regions=self.regions, chains=chains,
            symmetry=(('arm.left', 'arm.right'),),
        )
