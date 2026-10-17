# SPDX-License-Identifier: GPL-3.0-or-later
"""Avian recipe 17: tapered beak and broad, thin tail fan.

Wing and leg surface centerlines and rest chains share landmark identities.
Body and tail rest offsets remain explicit.
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
    toe_length: float = 0.0
    rear_toe_length: float = 0.0
    claw_length: float = 0.0

    def __post_init__(self):
        if not isinstance(self.name, str) or not self.name:
            raise ValueError('Avian tube needs a name')
        for name in ('toe_length', 'rear_toe_length', 'claw_length'):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise TypeError(name + ' must be a number')
            if not isfinite(value) or value < 0:
                raise ValueError(name + ' must be finite and nonnegative')
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


def _support_lift(height):
    """Give the grounded support chain room beneath the unchanged torso profile."""
    return height * .22


def _surface_profiles(dimensions):
    landmarks = []

    def tube(name, centers, widths, depths, toe_length=0.0, rear_toe_length=0.0, claw_length=0.0):
        names = tuple('surface.' + name + '.' + str(i) for i in range(len(centers)))
        landmarks.extend(Landmark(n, p) for n, p in zip(names, centers))
        return AvianTube(name, names, widths, depths, toe_length, rear_toe_length, claw_length)

    length = dimensions["body_length_cm"]
    width = dimensions["body_width_cm"]
    height = dimensions["body_height_cm"]
    wingspan = dimensions["wingspan_cm"]
    tail_length = dimensions["tail_length_cm"]

    support_lift = _support_lift(height)
    body_z = height * 0.52 + support_lift
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
        width * 0.55, width * 0.65, width * 0.38, width * 0.82,
        width, width * 0.92, width * 0.48, width * 0.60, width * 0.04,
    )
    depths = (
        height * 0.04, height * 0.08, height * 0.28, height * 0.76,
        height, height * 0.88, height * 0.46, height * 0.56, height * 0.05,
    )

    tubes = [tube("body", centers, widths, depths)]

    half_span = wingspan * 0.5
    # Tall torsos need lateral clearance for the folded proximal wing.
    # Limit the offset by available span so short wings retain an upper segment.
    root_x = min(max(width * 0.55, height * 0.34),
                 width * 0.5 + (half_span - width * 0.5) * 0.25)
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
        # Chord runs fore/aft across the wing; retain a compact shoulder and
        # thin depth while giving the middle a broad, tapered lifting outline.
        chord = max(1.0, min(length * .32, (half_span - root_x) * .65))
        widths_wing = (base * 1.12, chord * .80, chord, chord * .72, chord * .06)
        depths_wing = (base * 0.78, base * 0.66, base * 0.54, base * 0.34, base * 0.12)
        tubes.append(tube("wing." + side, centers_wing, widths_wing, depths_wing))

    # Keep the support path descending and beneath the underside opening.
    # Construction flattens the plantar arc of the ankle/toe rings to ground.
    hip_x = width * 0.15
    hip_y = -length * 0.20
    hip_z = height * 0.10 + support_lift
    knee_z = height * 0.09 + support_lift * .5
    ankle_z = height * 0.04
    ball_y = hip_y + length * 0.10
    leg_thickness = min(max(width * 0.12, 0.8), height * 0.07)
    for side, sign in (("left", -1.0), ("right", 1.0)):
        hip = (sign * hip_x, hip_y, hip_z)
        knee = (sign * hip_x * 1.08, hip_y + length * 0.025, knee_z)
        ankle = (sign * hip_x * 1.02, hip_y + length * 0.055, ankle_z)
        ball = (sign * hip_x, ball_y, height * 0.025)
        centers_leg = (hip, _lerp(hip, knee, 0.45), knee, ankle, ball)
        widths_leg = (
            leg_thickness * 1.15,
            leg_thickness,
            leg_thickness * 0.82,
            leg_thickness * 0.95,
            leg_thickness * 0.85,
        )
        depths_leg = (
            leg_thickness * 1.10,
            leg_thickness * 0.92,
            leg_thickness * 0.72,
            leg_thickness * 0.56,
            leg_thickness * 0.34,
        )
        tubes.append(tube("leg." + side, centers_leg, widths_leg, depths_leg, toe_length=length * .07, rear_toe_length=length * .0455, claw_length=min(leg_thickness * .65, length * .02)))

    return landmarks, tuple(tubes)


def _segment(name, head, tail, parent=None):
    return name, head, tail, parent


def _rest_segments(dimensions, landmarks, tubes):
    length = dimensions["body_length_cm"]
    width = dimensions["body_width_cm"]
    height = dimensions["body_height_cm"]
    tail_length = dimensions["tail_length_cm"]

    support_lift = _support_lift(height)
    body_z = height * 0.56 + support_lift
    rear_y = -length * 0.34
    chest_y = length * 0.28
    neck_y = length * 0.48
    head_y = length * 0.66
    tail_base_y = -length * 0.48

    bones = [
        _segment("root", (0, 0, height * 0.22 + support_lift), (0, 0, body_z)),
        _segment("spine", (0, rear_y, body_z), (0, chest_y, body_z + height * 0.06), "root"),
        _segment("neck", (0, chest_y, body_z + height * 0.06), (0, neck_y, body_z + height * 0.22), "spine"),
        _segment("head", (0, neck_y, body_z + height * 0.22), (0, head_y, body_z + height * 0.30), "neck"),
    ]

    points = {p.name: p.position for p in landmarks}
    for side in ('left', 'right'):
        wing = next(t for t in tubes if t.name == 'wing.' + side)
        shoulder, elbow, tip = (points[wing.landmarks[i]] for i in (0, 2, 4))
        bones.extend((
            _segment("wing.upper." + side, shoulder, elbow, "spine"),
            _segment("wing.lower." + side, elbow, tip, "wing.upper." + side),
        ))

    # Surface and rest rig share one authored support chain.
    for side in ('left', 'right'):
        leg = next(t for t in tubes if t.name == 'leg.' + side)
        hip, knee, ankle, ball = (points[leg.landmarks[i]] for i in (0, 2, 3, 4))
        bones.extend((
            _segment("leg.upper." + side, hip, knee, "spine"),
            _segment("leg.lower." + side, knee, ankle, "leg.upper." + side),
            _segment("foot." + side, ankle, ball, "leg.lower." + side),
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
    recipe_version = '17'

    def resolve(self, dimensions):
        # Values have already passed the provider's range/cross-field validation.
        landmarks, tubes = _surface_profiles(dimensions)
        segments = _rest_segments(dimensions, landmarks, tubes)
        chains = []
        groups = ((0, 1, 'root', None), (1, 2, 'spine', None),
                  (2, 3, 'neck', None), (3, 4, 'head', None),
                  (4, 6, 'wing.left', 'flight'), (6, 8, 'wing.right', 'flight'),
                  (8, 11, 'leg.left', 'leg_support'), (11, 14, 'leg.right', 'leg_support'),
                  (14, 16, 'tail', 'balance'))
        for start, end, name, role in groups:
            group = segments[start:end]
            points = [group[0][1]] + [segment[2] for segment in group]
            if role in ('flight', 'leg_support'):
                tube = next(t for t in tubes if t.name == name)
                names = tuple(tube.landmarks[i] for i in ((0, 2, 4) if role == 'flight' else (0, 2, 3, 4)))
            else:
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
