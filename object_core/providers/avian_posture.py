# SPDX-License-Identifier: GPL-3.0-or-later
"""Shared authored Avian wing posture in generated bone-local coordinates."""
from math import sin, cos, atan2, sqrt
from ..animation.idle import BoneLocalRotationTrack

COMPACT_FOLD_ROTATIONS = (
    ('wing.upper.left', 'z', 1.3),
    ('wing.upper.left', 'y', 1.),
    ('wing.lower.left', 'z', .2),
    ('wing.upper.right', 'z', -1.3),
    ('wing.upper.right', 'y', -1.),
    ('wing.lower.right', 'z', -.2),
)


def folded_wing_tracks(duration):
    """Hold the reviewed XYZ Euler pose as one axis-angle track per joint."""
    rotations = {}
    for name, axis, angle in COMPACT_FOLD_ROTATIONS:
        rotations.setdefault(name, [0., 0., 0.])['xyz'.index(axis)] = angle
    tracks = []
    for name, (x,y,z) in rotations.items():
        sx,sy,sz = sin(x/2),sin(y/2),sin(z/2)
        cx,cy,cz = cos(x/2),cos(y/2),cos(z/2)
        # XYZ Euler: qz * qy * qx. Preserve a single coherent rotation per bone.
        w = cx*cy*cz + sx*sy*sz
        vector = (sx*cy*cz-cx*sy*sz, cx*sy*cz+sx*cy*sz, cx*cy*sz-sx*sy*cz)
        length = sqrt(sum(v*v for v in vector))
        axis = tuple(v/length for v in vector)
        angle = 2*atan2(length,w)
        tracks.append(BoneLocalRotationTrack(name,axis,((0.,angle),(duration,angle))))
    return tuple(tracks)
