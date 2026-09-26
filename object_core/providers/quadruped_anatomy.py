# SPDX-License-Identifier: GPL-3.0-or-later
"""Canine recipe resolving the current Quadruped surface and complete rest rig.

The current coarse surface/rig relationships are preserved deliberately. Canine
quality refinement (ears, digitigrade stance and paw articulation) comes next.
Provider-validated dimensions enter resolution; the constructor binds topology.
"""
from ..anatomy import AnatomyConnection, AnatomyRegion, JointChain, Landmark, ResolvedAnatomy


class CanineRecipe:
    recipe_id = 'canine'
    recipe_version = '2'

    def resolve(self, dimensions):
        length = dimensions['body_length_cm']
        shoulder = dimensions['shoulder_height_cm']
        width = dimensions['body_width_cm']
        head_length = dimensions['head_length_cm']
        tail_length = dimensions['tail_length_cm']
        torso_height = shoulder * 0.42
        surface_back_z = shoulder - torso_height * 0.30
        belly_z = shoulder - torso_height * 0.72
        body_z = (surface_back_z + belly_z) * 0.5
        rig_back_z = shoulder - torso_height * 0.48 + torso_height * 0.18
        fore_y, hind_y = length * 0.32, -length * 0.32
        knee_z = (shoulder - torso_height * 0.45) * 0.48
        points = [
            ('tail.tip', (0, -length * 0.5 - tail_length, surface_back_z + torso_height * 0.36)),
            ('tail.mid', (0, -length * 0.5 - tail_length * 0.48, surface_back_z + torso_height * 0.22)),
            ('tail.base', (0, -length * 0.5, surface_back_z)),
            ('torso.rear', (0, -length * 0.42, body_z)),
            ('torso.hind', (0, hind_y, body_z)),
            ('torso.center', (0, 0, body_z)),
            ('torso.fore', (0, fore_y, body_z + torso_height * 0.06)),
            ('chest.center', (0, length * 0.43, body_z + torso_height * 0.16)),
            ('neck.center', (0, length * 0.52, shoulder + torso_height * 0.05)),
            ('head.center', (0, length * 0.5 + head_length * 0.34, shoulder + torso_height * 0.13)),
            ('muzzle.tip', (0, length * 0.5 + head_length * 0.82, shoulder + torso_height * 0.06)),
            ('root.base', (0, 0, shoulder * 0.45)),
            ('root.tip', (0, 0, rig_back_z)),
            ('spine.hind', (0, hind_y, rig_back_z)),
            ('spine.fore', (0, fore_y, rig_back_z)),
            ('neck.top', (0, length * 0.5, shoulder)),
            ('head.tip', (0, length * 0.5 + head_length * 0.28 + head_length * 0.35,
                          shoulder + torso_height * 0.08)),
        ]
        chains = [JointChain('root', ('root.base', 'root.tip'), ('root',)),
                  JointChain('spine', ('spine.hind', 'spine.fore'), ('spine',), 'root'),
                  JointChain('neck', ('spine.fore', 'neck.top'), ('neck',), 'spine'),
                  JointChain('head', ('neck.top', 'head.tip'), ('head',), 'neck')]
        regions = [AnatomyRegion(name, 'quadruped', ()) for name in
                   ('body', 'torso', 'chest', 'waist', 'head', 'muzzle', 'tail')]
        connections = []
        for side, x in (('left', -width * 0.34), ('right', width * 0.34)):
            for family, bone_prefix, y, top_z, upper, joint in (
                ('front', 'fore', fore_y, shoulder, 'shoulder', 'elbow'),
                ('hind', 'hind', hind_y, shoulder * 0.86, 'hip', 'knee'),
            ):
                suffix = family + '.' + side
                region = 'leg.' + suffix
                points.extend((
                    (upper + '.' + suffix, (x, y, top_z)),
                    (joint + '.' + suffix, (x, y, knee_z)),
                    ('ankle.' + suffix, (x, y, max(width * 0.12, 1.5))),
                    ('paw.' + suffix, (x, y + width * 0.10, max(width * 0.07, 1.0))),
                    ('ground.' + suffix, (x, y, 0)),
                ))
                chains.append(JointChain(region,
                    (upper + '.' + suffix, joint + '.' + suffix, 'ground.' + suffix),
                    (bone_prefix + '_upper.' + side, bone_prefix + '_lower.' + side),
                    'spine', (0, -1 if family == 'front' else 1, 0), family + '_support'))
                regions.append(AnatomyRegion(region, 'quadruped', ()))
                connections.append(AnatomyConnection(upper + '.' + suffix, ('torso', region), 'connected'))
        start_y, start_z = -length * 0.5, rig_back_z
        points.append(('tail.rig.0', (0, start_y, start_z)))
        for index in range(3):
            start_y = start_y - max(tail_length / 3, 2.0) * 0.75
            start_z = start_z + torso_height * 0.12
            points.append(('tail.rig.' + str(index + 1), (0, start_y, start_z)))
        chains.append(JointChain('tail', tuple('tail.rig.' + str(i) for i in range(4)),
                                 ('tail.1', 'tail.2', 'tail.3'), 'spine', motion_role='tail'))
        return ResolvedAnatomy(
            self.recipe_id, self.recipe_version,
            tuple((key, float(value)) for key, value in dimensions.items()),
            landmarks=tuple(Landmark(name, position) for name, position in points),
            regions=regions, chains=chains, connections=connections,
            symmetry=(('leg.front.left', 'leg.front.right'), ('leg.hind.left', 'leg.hind.right')),
        )
