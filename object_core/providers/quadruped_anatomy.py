# SPDX-License-Identifier: GPL-3.0-or-later
"""Canine recipe resolving the current Quadruped surface and complete rest rig.

Hind limbs resolve separate hip, knee, hock and paw landmarks. The remaining
body sections resolve a tucked waist, fuller chest and a separate muzzle base.
Each limb declares a ground landmark for neutral sole contact.
Front shoulders resolve ahead of the elbow; distal dimensions fit leg height.
Detailed facial features still await refinement.
Provider-validated dimensions enter resolution; the constructor binds topology.
"""
from dataclasses import dataclass
from math import isfinite

from ..anatomy import AnatomyConnection, AnatomyRegion, JointChain, Landmark, ResolvedAnatomy


@dataclass(frozen=True)
class CanineBodySection:
    """A recipe-owned body cross section centered on a resolved landmark."""
    landmark: str
    width_cm: float
    depth_cm: float

    def __post_init__(self):
        if not isinstance(self.landmark, str) or not self.landmark:
            raise ValueError('Canine body section requires a landmark name')
        for value in (self.width_cm, self.depth_cm):
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise TypeError('Canine section dimensions must be numbers')
            if not isfinite(value) or value <= 0:
                raise ValueError('Canine section dimensions must be positive and finite')


@dataclass(frozen=True)
class CaninePawProfile:
    """Low-paw volume and forward projection, independent of rest-rig joints."""
    width_scale: float
    length_scale: float
    forward_cm: float
    height_cm: float

    def __post_init__(self):
        for name in ('width_scale', 'length_scale', 'forward_cm', 'height_cm'):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise TypeError('Canine paw profile values must be numbers')
            if not isfinite(value) or value < 0 or (name != 'forward_cm' and value == 0):
                raise ValueError('Canine paw profile requires positive scales/height and nonnegative projection')


@dataclass(frozen=True)
class ResolvedCanineAnatomy(ResolvedAnatomy):
    """Compact canine surface profile; construction still owns mesh topology."""
    body_sections: tuple = ()
    paw_profile: CaninePawProfile = None

    def __post_init__(self):
        super().__post_init__()
        if not isinstance(self.paw_profile, CaninePawProfile):
            raise TypeError('Canine resolution requires a validated paw profile')
        sections = tuple(self.body_sections)
        expected = ('tail.tip', 'tail.mid', 'tail.base', 'torso.rear', 'torso.hind',
                    'torso.center', 'torso.fore', 'chest.center', 'neck.center',
                    'head.center', 'muzzle.base', 'muzzle.tip')
        if any(not isinstance(section, CanineBodySection) for section in sections):
            raise TypeError('Canine resolution requires validated body sections')
        if tuple(section.landmark for section in sections) != expected:
            raise ValueError('Canine body sections must follow the authored torso path')
        if not set(expected) <= {p.name for p in self.landmarks}:
            raise ValueError('Canine section references a missing landmark')
        object.__setattr__(self, 'body_sections', sections)


class CanineRecipe:
    recipe_id = 'canine'
    recipe_version = '11'

    def resolve(self, dimensions):
        length = dimensions['body_length_cm']
        shoulder = dimensions['shoulder_height_cm']
        width = dimensions['body_width_cm']
        head_length = dimensions['head_length_cm']
        tail_length = dimensions['tail_length_cm']
        torso_height = shoulder * 0.42
        face_height = min(torso_height, head_length)
        muzzle_z = shoulder + (torso_height - face_height) * .05
        surface_back_z = shoulder - torso_height * 0.30
        belly_z = shoulder - torso_height * 0.72
        body_z = (surface_back_z + belly_z) * 0.5
        rig_back_z = shoulder - torso_height * 0.48 + torso_height * 0.18
        fore_y, hind_y = length * 0.32, -length * 0.32
        knee_z = (shoulder - torso_height * 0.45) * 0.48
        # Distal landmarks must stay below the elbow even for short, wide bodies.
        ankle_z = min(max(width * .12, 1.5), knee_z * .5)
        paw_z = min(max(width * .07, 1.0), ankle_z * .6)
        paw_forward = min(width * .10, shoulder * .08)
        points = [
            ('tail.tip', (0, -length * 0.5 - tail_length, surface_back_z + torso_height * 0.36)),
            ('tail.mid', (0, -length * 0.5 - tail_length * 0.48, surface_back_z + torso_height * 0.22)),
            ('tail.base', (0, -length * 0.5, surface_back_z)),
            ('torso.rear', (0, -length * 0.42, body_z)),
            ('torso.hind', (0, hind_y, body_z + torso_height * .11)),
            ('torso.center', (0, -length * .06, body_z + torso_height * .03)),
            ('torso.fore', (0, fore_y, body_z - torso_height * .02)),
            ('chest.center', (0, length * .43, body_z + torso_height * .08)),
            ('neck.center', (0, length * .47 + head_length * .12, shoulder + torso_height * .05)),
            ('head.center', (0, length * 0.5 + head_length * 0.34, shoulder + torso_height * .05 + face_height * .13)),
            ('muzzle.base', (0, length * 0.5 + head_length * 0.54, muzzle_z)),
            ('muzzle.tip', (0, length * 0.5 + head_length * 0.90, muzzle_z)),
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
                   ('body', 'torso', 'chest', 'waist', 'head', 'muzzle', 'tail', 'ear.left', 'ear.right')]
        connections = []
        for side, x in (('left', -width * 0.34), ('right', width * 0.34)):
            for family, bone_prefix, y, top_z, upper, joint in (
                ('front', 'fore', fore_y, shoulder, 'shoulder', 'elbow'),
                ('hind', 'hind', hind_y, shoulder * 0.86, 'hip', 'knee'),
            ):
                suffix = family + '.' + side
                region = 'leg.' + suffix
                if family == 'hind':
                    # +Y is forward. The stifle sits forward of the hip; the
                    # raised hock is behind it, with a separate distal segment.
                    # Bounded offsets keep extreme length/height combinations
                    # ordered without deriving joint placement from mesh size.
                    knee = (x, y + min(length * .10, shoulder * .20), shoulder * .53)
                    hock = (x, y - min(length * .06, shoulder * .12), shoulder * .22)
                    paw = (x, hock[1] + min(length * .06, shoulder * .10), shoulder * .045)
                    points.extend(((upper + '.' + suffix, (x, y, top_z)),
                                   ('knee.' + suffix, knee), ('hock.' + suffix, hock),
                                   ('paw.' + suffix, paw),
                                   ('ground.' + suffix, (x, paw[1], 0))))
                    path = (upper + '.' + suffix, 'knee.' + suffix,
                            'hock.' + suffix, 'paw.' + suffix)
                    bones = ('hind_upper.' + side, 'hind_lower.' + side, 'hind_pastern.' + side)
                else:
                    points.extend((
                        # Bound the upper-leg slope while keeping the elbow and
                        # distal chain aligned with the existing support.
                        (upper + '.' + suffix, (x, y + min(length * .04, shoulder * .06), top_z)),
                        (joint + '.' + suffix, (x, y, knee_z)),
                        ('ankle.' + suffix, (x, y, ankle_z)),
                        ('paw.' + suffix, (x, y + paw_forward, paw_z)),
                        ('ground.' + suffix, (x, y, 0)),
                    ))
                    path = (upper + '.' + suffix, joint + '.' + suffix, 'ground.' + suffix)
                    bones = (bone_prefix + '_upper.' + side, bone_prefix + '_lower.' + side)
                chains.append(JointChain(region, path, bones,
                    'spine', (0, -1 if family == 'front' else 1, 0), family + '_support'))
                regions.append(AnatomyRegion(region, 'quadruped', ()))
                connections.append(AnatomyConnection(upper + '.' + suffix, ('torso', region), 'connected'))
        for side, sign in (('left', -1), ('right', 1)):
            base = (sign * width * .22, length * .49 + head_length * .20,
                    shoulder + torso_height * .05 + face_height * .27)
            tip = (sign * width * .32, base[1] - head_length * .08,
                   base[2] + head_length * .42)
            points.extend((('ear.base.' + side, base), ('ear.tip.' + side, tip)))
            connections.append(AnatomyConnection('ear.' + side, ('head', 'ear.' + side), 'connected'))
        start_y, start_z = -length * 0.5, rig_back_z
        points.append(('tail.rig.0', (0, start_y, start_z)))
        for index in range(3):
            start_y = start_y - max(tail_length / 3, 2.0) * 0.75
            start_z = start_z + torso_height * 0.12
            points.append(('tail.rig.' + str(index + 1), (0, start_y, start_z)))
        chains.append(JointChain('tail', tuple('tail.rig.' + str(i) for i in range(4)),
                                 ('tail.1', 'tail.2', 'tail.3'), 'spine', motion_role='tail'))
        # A tucked abdominal section expands into the ribcage/chest; these
        # are species proportions rather than constants hidden in the builder.
        sections = tuple(CanineBodySection(name, section_width, section_depth)
                         for name, section_width, section_depth in (
            ('tail.tip', width * .08, width * .08),
            ('tail.mid', width * .12, width * .12),
            ('tail.base', width * .18, width * .18),
            ('torso.rear', width * .82, torso_height * .82),
            ('torso.hind', width * .80, torso_height * .72),
            ('torso.center', width * .92, torso_height * .92),
            ('torso.fore', width * 1.08, torso_height * 1.10),
            ('chest.center', width * .90, torso_height * 1.05),
            ('neck.center', width * .58, torso_height * .62),
            ('head.center', width * .82, face_height * .78),
            ('muzzle.base', width * .42, face_height * .36),
            ('muzzle.tip', width * .28, face_height * .28)))
        return ResolvedCanineAnatomy(
            self.recipe_id, self.recipe_version,
            tuple((key, float(value)) for key, value in dimensions.items()),
            landmarks=tuple(Landmark(name, position) for name, position in points),
            regions=regions, chains=chains, connections=connections,
            body_sections=sections,
            paw_profile=CaninePawProfile(
                width_scale=1.20, length_scale=1.65,
                forward_cm=min(width * .02, shoulder * .03),
                height_cm=min(width * .16, shoulder * .08)),
            symmetry=(('leg.front.left', 'leg.front.right'), ('leg.hind.left', 'leg.hind.right'), ('ear.left', 'ear.right')),
        )
