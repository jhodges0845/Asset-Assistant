# SPDX-License-Identifier: GPL-3.0-or-later
"""Avian recipe 1: preserve the existing surface and rig before shape refinement.

Surface centerlines and rest joints are explicitly distinct in this baseline;
legacy offsets are retained, rather than silently changing saved rig behavior.
Only this recipe owns their dimensional formulas. Construction owns topology.
"""
from dataclasses import dataclass
from math import isfinite

from ..anatomy import AnatomyConnection, AnatomyRegion, JointChain, Landmark, ResolvedAnatomy


@dataclass(frozen=True)
class AvianTube:
    name: str
    landmarks: tuple
    widths: tuple
    depths: tuple

    def __post_init__(self):
        if not isinstance(self.name, str) or not self.name:
            raise ValueError('Avian tube needs a name')
        for field in ('landmarks', 'widths', 'depths'):
            object.__setattr__(self, field, tuple(getattr(self, field)))
        if len(self.landmarks) < 2 or len(self.widths) != len(self.landmarks) or len(self.depths) != len(self.landmarks):
            raise ValueError('Avian tube profiles must match its landmark path')
        for value in self.widths + self.depths:
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise TypeError('Avian profile dimensions must be numbers')
            if not isfinite(value) or value <= 0:
                raise ValueError('Avian profile dimensions must be finite and positive')


@dataclass(frozen=True)
class ResolvedAvianAnatomy(ResolvedAnatomy):
    tubes: tuple = ()

    def __post_init__(self):
        super().__post_init__()
        tubes = tuple(self.tubes)
        if any(not isinstance(tube, AvianTube) for tube in tubes):
            raise TypeError('Avian anatomy requires validated tubes')
        if tuple(t.name for t in tubes) != ('body', 'wing.left', 'wing.right', 'leg.left', 'leg.right'):
            raise ValueError('Avian anatomy requires body, wings and legs in construction order')
        names = {p.name for p in self.landmarks}
        if any(not set(t.landmarks) <= names for t in tubes):
            raise ValueError('Avian tube references an unknown landmark')
        object.__setattr__(self, 'tubes', tubes)


def _lerp(a, b, amount):
    return tuple(a[i] + (b[i] - a[i]) * amount for i in range(3))


def _surface_profiles(dimensions):
    landmarks = []

    def tube(name, centers, widths, depths):
        names = tuple('surface.' + name + '.' + str(i) for i in range(len(centers)))
        landmarks.extend(Landmark(n, p) for n, p in zip(names, centers))
        return AvianTube(name, names, widths, depths)

    length = dimensions["body_length_cm"]
    width = dimensions["body_width_cm"]
    height = dimensions["body_height_cm"]
    wingspan = dimensions["wingspan_cm"]
    tail_length = dimensions["tail_length_cm"]

    body_z = height * 0.52
    rear_y = -length * 0.42
    chest_y = length * 0.30
    neck_y = length * 0.48
    head_y = length * 0.63
    beak_y = length * 0.78
    tail_base_y = -length * 0.48
    tail_mid_y = tail_base_y - tail_length * 0.46
    tail_tip_y = tail_base_y - tail_length

    centers = (
        (0.0, tail_tip_y, body_z + height * 0.02),
        (0.0, tail_mid_y, body_z + height * 0.05),
        (0.0, tail_base_y, body_z),
        (0.0, rear_y, body_z),
        (0.0, 0.0, body_z + height * 0.04),
        (0.0, chest_y, body_z + height * 0.08),
        (0.0, neck_y, body_z + height * 0.22),
        (0.0, head_y, body_z + height * 0.31),
        (0.0, beak_y, body_z + height * 0.26),
    )
    widths = (
        width * 0.10, width * 0.18, width * 0.38, width * 0.82,
        width, width * 0.92, width * 0.48, width * 0.60, width * 0.18,
    )
    depths = (
        height * 0.10, height * 0.16, height * 0.28, height * 0.76,
        height, height * 0.88, height * 0.46, height * 0.56, height * 0.20,
    )

    tubes = [tube("body", centers, widths, depths)]

    half_span = wingspan * 0.5
    root_x = width * 0.36
    root_y = length * 0.08
    root_z = body_z + height * 0.14
    for side, sign in (("left", -1.0), ("right", 1.0)):
        shoulder = (sign * root_x, root_y, root_z)
        elbow = (sign * (root_x + (half_span - root_x) * 0.48), root_y - length * 0.06, root_z - height * 0.08)
        tip = (sign * half_span, root_y - length * 0.16, root_z - height * 0.13)
        centers_wing = (
            shoulder,
            _lerp(shoulder, elbow, 0.22),
            elbow,
            _lerp(elbow, tip, 0.20),
            tip,
        )
        base = max(height * 0.20, 1.0)
        widths_wing = (base * 1.12, base, base * 0.84, base * 0.55, base * 0.18)
        depths_wing = (base * 0.78, base * 0.66, base * 0.54, base * 0.34, base * 0.12)
        tubes.append(tube("wing." + side, centers_wing, widths_wing, depths_wing))

    # Ground-contact anatomy. The leg bends slightly forward and the foot projects
    # along +Y so the generated bird has a readable stance before animation.
    hip_x = width * 0.25
    hip_y = -length * 0.04
    hip_z = body_z - height * 0.26
    knee_z = height * 0.28
    ankle_z = height * 0.08
    toe_y = hip_y + length * 0.17
    leg_thickness = max(width * 0.12, 0.8)
    for side, sign in (("left", -1.0), ("right", 1.0)):
        hip = (sign * hip_x, hip_y, hip_z)
        knee = (sign * hip_x * 1.08, hip_y + length * 0.025, knee_z)
        ankle = (sign * hip_x * 1.02, hip_y + length * 0.055, ankle_z)
        toe = (sign * hip_x, toe_y, ankle_z * 0.72)
        centers_leg = (hip, _lerp(hip, knee, 0.45), knee, ankle, toe)
        widths_leg = (
            leg_thickness * 1.15,
            leg_thickness,
            leg_thickness * 0.82,
            leg_thickness * 0.68,
            leg_thickness * 0.42,
        )
        depths_leg = (
            leg_thickness * 1.10,
            leg_thickness * 0.92,
            leg_thickness * 0.72,
            leg_thickness * 0.56,
            leg_thickness * 0.34,
        )
        tubes.append(tube("leg." + side, centers_leg, widths_leg, depths_leg))

    return landmarks, tuple(tubes)


def _segment(name, head, tail, parent=None):
    return name, head, tail, parent


def _rest_segments(dimensions):
    length = dimensions["body_length_cm"]
    width = dimensions["body_width_cm"]
    height = dimensions["body_height_cm"]
    wingspan = dimensions["wingspan_cm"]
    tail_length = dimensions["tail_length_cm"]

    body_z = height * 0.56
    rear_y = -length * 0.34
    chest_y = length * 0.28
    neck_y = length * 0.48
    head_y = length * 0.66
    half_span = wingspan * 0.5
    shoulder_x = width * 0.34
    shoulder_y = length * 0.08
    shoulder_z = body_z + height * 0.12
    tail_base_y = -length * 0.48

    bones = [
        _segment("root", (0, 0, height * 0.22), (0, 0, body_z)),
        _segment("spine", (0, rear_y, body_z), (0, chest_y, body_z + height * 0.06), "root"),
        _segment("neck", (0, chest_y, body_z + height * 0.06), (0, neck_y, body_z + height * 0.22), "spine"),
        _segment("head", (0, neck_y, body_z + height * 0.22), (0, head_y, body_z + height * 0.30), "neck"),
    ]

    for side, sign in (("left", -1.0), ("right", 1.0)):
        shoulder = (sign * shoulder_x, shoulder_y, shoulder_z)
        elbow = (sign * (shoulder_x + (half_span - shoulder_x) * 0.50), shoulder_y - length * 0.06, shoulder_z - height * 0.07)
        tip = (sign * half_span, shoulder_y - length * 0.16, shoulder_z - height * 0.12)
        bones.extend((
            _segment("wing.upper." + side, shoulder, elbow, "spine"),
            _segment("wing.lower." + side, elbow, tip, "wing.upper." + side),
        ))

    # Birds need a ground-contact chain as well as wings. Keep the leg anatomy
    # provider-specific so shared Blender rigging stays body-plan agnostic.
    hip_x = width * 0.24
    hip_y = -length * 0.04
    hip_z = body_z - height * 0.28
    knee_z = height * 0.28
    ankle_z = height * 0.08
    toe_y = hip_y + length * 0.16
    for side, sign in (("left", -1.0), ("right", 1.0)):
        hip = (sign * hip_x, hip_y, hip_z)
        knee = (sign * hip_x * 1.08, hip_y + length * 0.025, knee_z)
        ankle = (sign * hip_x * 1.02, hip_y + length * 0.055, ankle_z)
        toe = (sign * hip_x, toe_y, ankle_z * 0.72)
        bones.extend((
            _segment("leg.upper." + side, hip, knee, "spine"),
            _segment("leg.lower." + side, knee, ankle, "leg.upper." + side),
            _segment("foot." + side, ankle, toe, "leg.lower." + side),
        ))

    tail_segment = max(tail_length / 2.0, 1.0)
    start = (0, tail_base_y, body_z)
    mid = (0, tail_base_y - tail_segment, body_z + height * 0.04)
    tip = (0, tail_base_y - tail_length, body_z + height * 0.02)
    bones.extend((
        _segment("tail.1", start, mid, "spine"),
        _segment("tail.2", mid, tip, "tail.1"),
    ))
    return bones


class AvianRecipe:
    recipe_id = 'avian'
    recipe_version = '1'

    def resolve(self, dimensions):
        # Values have already passed the provider's range/cross-field validation.
        landmarks, tubes = _surface_profiles(dimensions)
        segments = _rest_segments(dimensions)
        chains = []
        groups = ((0, 1, 'root', None), (1, 2, 'spine', None),
                  (2, 3, 'neck', None), (3, 4, 'head', None),
                  (4, 6, 'wing.left', 'flight'), (6, 8, 'wing.right', 'flight'),
                  (8, 11, 'leg.left', 'leg_support'), (11, 14, 'leg.right', 'leg_support'),
                  (14, 16, 'tail', 'balance'))
        for start, end, name, role in groups:
            group = segments[start:end]
            points = [group[0][1]] + [segment[2] for segment in group]
            names = tuple('joint.' + name + '.' + str(i) for i in range(len(points)))
            landmarks.extend(Landmark(n, p) for n, p in zip(names, points))
            chains.append(JointChain(name, names, tuple(s[0] for s in group), group[0][3],
                                     motion_role=role))
        regions = tuple(AnatomyRegion(t.name, 'avian', ()) for t in tubes)
        return ResolvedAvianAnatomy(
            self.recipe_id, self.recipe_version, tuple(dimensions.items()),
            landmarks=landmarks, regions=regions, chains=chains,
            connections=tuple(AnatomyConnection('body.' + t.name, ('body', t.name), 'connected')
                              for t in tubes[1:]),
            symmetry=(('wing.left', 'wing.right'), ('leg.left', 'leg.right')),
            tubes=tubes)
