# SPDX-License-Identifier: GPL-3.0-or-later
"""Quadruped torso/front-left proof: shared source for current surface and rig.

Receives provider-validated dimensions. Geometry binds authored membership and
boundary indices after construction; empty membership at resolution is pending,
not a topology audit. Other limbs remain outside this deliberately small proof.
"""
from ..anatomy import AnatomyConnection, AnatomyRegion, JointChain, Landmark, ResolvedAnatomy


class QuadrupedFrontRecipe:
    recipe_id = 'quadruped.front-proof'
    recipe_version = '1'

    def resolve(self, dimensions):
        length = dimensions['body_length_cm']
        shoulder = dimensions['shoulder_height_cm']
        width = dimensions['body_width_cm']
        torso_height = shoulder * 0.42
        surface_back_z = shoulder - torso_height * 0.30
        belly_z = shoulder - torso_height * 0.72
        body_z = (surface_back_z + belly_z) * 0.5
        # Preserve the existing rig's distinct centerline and arithmetic.
        rig_back_z = shoulder - torso_height * 0.48 + torso_height * 0.18
        fore_y, hind_y = length * 0.32, -length * 0.32
        side_x = -width * 0.34
        knee_z = (shoulder - torso_height * 0.45) * 0.48
        points = (
            ('torso.rear', (0, -length * 0.42, body_z)),
            ('torso.hind', (0, hind_y, body_z)),
            ('torso.center', (0, 0, body_z)),
            ('torso.fore', (0, fore_y, body_z + torso_height * 0.06)),
            ('chest.center', (0, length * 0.43, body_z + torso_height * 0.16)),
            ('root.base', (0, 0, shoulder * 0.45)),
            ('root.tip', (0, 0, rig_back_z)),
            ('spine.hind', (0, hind_y, rig_back_z)),
            ('spine.fore', (0, fore_y, rig_back_z)),
            ('shoulder.front.left', (side_x, fore_y, shoulder)),
            ('elbow.front.left', (side_x, fore_y, knee_z)),
            ('ankle.front.left', (side_x, fore_y, max(width * 0.12, 1.5))),
            ('paw.front.left', (side_x, fore_y + width * 0.10, max(width * 0.07, 1.0))),
            # Current lower bone ends at the ground; do not silently change it
            # to the surface ankle or invent a paw bone during this extraction.
            ('ground.front.left', (side_x, fore_y, 0)),
        )
        return ResolvedAnatomy(
            self.recipe_id, self.recipe_version,
            tuple((key, float(value)) for key, value in dimensions.items()),
            landmarks=tuple(Landmark(name, position) for name, position in points),
            regions=(AnatomyRegion('torso', 'quadruped', ()),
                     AnatomyRegion('leg.front.left', 'quadruped', ())),
            chains=(JointChain('root', ('root.base', 'root.tip'), ('root',)),
                    JointChain('spine', ('spine.hind', 'spine.fore'), ('spine',), 'root'),
                    JointChain('leg.front.left',
                               ('shoulder.front.left', 'elbow.front.left', 'ground.front.left'),
                               ('fore_upper.left', 'fore_lower.left'), 'spine',
                               (0, -1, 0), 'front_support')),
            connections=(AnatomyConnection('shoulder.front.left',
                                           ('torso', 'leg.front.left'), 'connected'),),
        )
