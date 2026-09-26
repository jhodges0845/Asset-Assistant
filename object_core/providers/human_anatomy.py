# SPDX-License-Identifier: GPL-3.0-or-later
"""Human recipe: resolve construction controls, rest landmarks and authored ownership.

Resolution precedes the mesh and skeleton. Human-specific surface math remains
in geometry; the generic anatomy contract knows nothing about Human body plans.
"""
from dataclasses import dataclass
from math import pi, sin
from typing import Optional

from ..anatomy import AnatomyConnection, AnatomyRegion, JointChain, Landmark, ResolvedAnatomy
from ..geometry.human_shaping import shape_surface_point
from ..models import BodyType, HumanoidSpec
from ..models.proportions import HumanoidProportions
from ..proportions import generate_proportions
from ..proportions.rules import MIN_HEIGHT_CM, MAX_HEIGHT_CM



@dataclass(frozen=True)
class ResolvedHumanAnatomy(ResolvedAnatomy):
    """Compact Human construction payload; no mesh, weights or Blender state."""
    proportions: Optional[HumanoidProportions] = None
    surface_reference: Optional[HumanoidProportions] = None

    def __post_init__(self):
        super().__post_init__()
        if not isinstance(self.proportions, HumanoidProportions):
            raise TypeError('Human resolution requires validated proportions')
        if not isinstance(self.surface_reference, HumanoidProportions):
            raise TypeError('Human resolution requires a surface reference')


@dataclass(frozen=True)
class HumanRecipe:
    """One Human resolution; regions come from audited neutral topology."""
    regions: tuple = ()
    recipe_id = 'human'
    recipe_version = '1'

    def __post_init__(self):
        regions = tuple(self.regions)
        if {r.name for r in regions} != {'body', 'arm.left', 'arm.right', 'leg.left', 'leg.right'} or len(regions) != 5:
            raise ValueError('Human recipe requires the body and all four authored limb regions')
        if any(r.mesh_part != 'human' for r in regions):
            raise ValueError('Human regions must belong to the human mesh part')
        object.__setattr__(self, 'regions', regions)

    def resolve(self, values):
        spec = HumanoidSpec(values['height_cm'], values['weight_kg'], BodyType(values['body_type']))
        proportions = generate_proportions(spec)
        height = proportions.standing_height_cm
        # Preserve existing floating-point evaluation for rig and surface:
        # proportions sum to the requested height, subject to roundoff.
        # The validated input can sum a few ulps beyond the allowed boundary.
        reference_height = min(MAX_HEIGHT_CM, max(MIN_HEIGHT_CM, height))
        rig_reference = generate_proportions(HumanoidSpec(reference_height, 95.0, BodyType.AVERAGE))
        surface_reference = generate_proportions(HumanoidSpec(spec.height_cm, 95.0, BodyType.AVERAGE))
        floor = min(
            0.09 - 0.059 * min((k / 32) / 0.24, 1) - 0.003 * (k / 32)
            - (0.026 * (1 - k / 32) + 0.014 * (k / 32)) * sin(pi / 2 * min(1, k / 16))
            for k in range(1, 33)
        )

        def point(x, y, z):
            return shape_surface_point(
                (x * height / 1.75, y * height / 1.75,
                 (z - floor) * height / (1.75 - floor)), proportions, rig_reference)

        landmarks = [Landmark('pelvis', point(0, 0.008, 0.99)),
                     Landmark('root.tip', point(0, 0.008, 1.04)),
                     Landmark('shoulder.center', point(0, 0, 1.465)),
                     Landmark('chin', point(0, 0, 1.548)),
                     Landmark('crown', point(0, 0, 1.75))]
        chains = [JointChain('root', ('pelvis', 'root.tip'), ('root',)),
                  JointChain('torso', ('pelvis', 'shoulder.center'), ('torso',), 'root'),
                  JointChain('neck', ('shoulder.center', 'chin'), ('neck',), 'torso'),
                  JointChain('head', ('chin', 'crown'), ('head',), 'neck')]
        for side, sign in (('left', 1), ('right', -1)):
            arm_names = tuple(name + '.' + side for name in ('shoulder', 'elbow', 'wrist', 'hand.tip'))
            arm_points = tuple(point(sign * x, 0, z) for x, z in
                               ((0.192, 1.385), (0.263, 1.19), (0.308, 0.923), (0.316, 0.78)))
            leg_names = tuple(name + '.' + side for name in ('hip', 'knee', 'ankle', 'toe'))
            leg_points = tuple(point(sign * x, y, z) for x, y, z in
                               ((0.089, 0.008, 0.965), (0.155, 0.008, 0.50),
                                (0.187, 0.005, 0.09), (0.187, 0.174, 0.028)))
            landmarks.extend(Landmark(name, p) for name, p in zip(arm_names, arm_points))
            landmarks.extend(Landmark(name, p) for name, p in zip(leg_names, leg_points))
            chains.append(JointChain('arm.' + side, arm_names,
                                     tuple(name + '.' + side for name in ('upper_arm', 'forearm', 'hand')),
                                     'torso', (0, 1, 0), 'arm'))
            chains.append(JointChain('leg.' + side, leg_names,
                                     tuple(name + '.' + side for name in ('upper_leg', 'lower_leg', 'foot')),
                                     'root', (0, -1, 0), 'leg_support'))
        return ResolvedHumanAnatomy(
            self.recipe_id, self.recipe_version,
            (('height_cm', spec.height_cm), ('weight_kg', spec.weight_kg), ('body_type', spec.body_type.value)),
            landmarks=landmarks, regions=self.regions, chains=chains,
            symmetry=(('arm.left', 'arm.right'), ('leg.left', 'leg.right')),
            connections=tuple(AnatomyConnection('body.' + region.name,
                                               ('body', region.name), 'connected')
                              for region in self.regions if region.name != 'body'),
            proportions=proportions, surface_reference=surface_reference,
        )
