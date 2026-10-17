# SPDX-License-Identifier: GPL-3.0-or-later
"""Portable planar contact solving against a weighted limb surface.

Influences outside the supplied chain inherit root translation only; callers
must keep those bones unrotated when using this planar model.
"""
from math import cos, sin


def paw_roll_forward_offset(sole_yz, toe_yz, pitch):
    """Sole-centroid forward offset for rotation about a fixed material toe."""
    return ((cos(pitch) - 1) * (sole_yz[0] - toe_yz[0])
            - sin(pitch) * (sole_yz[1] - toe_yz[1]))


class LimbSurface:
    """Exact planar linear-blend skinning for this limb's contact solve."""
    def __init__(self, mesh, weights, region, bones, crouch):
        self.heads = tuple(b.head[1:] for b in bones)
        self.crouch = crouch
        self.paw_pitch = 0.
        names = {b.name: i for i, b in enumerate(bones)}
        vertices = mesh.parts[0].vertices
        indices = tuple(region.vertex_indices)
        # Include every authored limb vertex, so the contact envelope cannot
        # overlook a higher rest vertex that rotates below the neutral sole.
        self.rows = tuple(tuple((names.get(w.bone_name, -1), w.weight,
                                vertices[i][1] * w.weight, vertices[i][2] * w.weight)
                               for w in weights.vertices[i]) for i in indices)
        sole = tuple(i for i in indices if 0 <= vertices[i][2] <= .1)
        if not sole:
            raise ValueError('Contact gait requires a grounded neutral sole')
        self.neutral_y = sum(vertices[i][1] for i in sole) / len(sole)
        self.neutral_z = sum(vertices[i][2] for i in sole) / len(sole)
        floor = min(vertices[i][2] for i in sole)
        grounded = tuple(i for i in sole if vertices[i][2] <= floor + .02)
        toe = max(grounded, key=lambda i: (vertices[i][1], -vertices[i][2]))
        self.toe_y, self.toe_z = vertices[toe][1:]
        sums = [[0., 0., 0.] for _ in range(len(bones) + 1)]
        for i in sole:
            for w in weights.vertices[i]:
                row = sums[names.get(w.bone_name, -1)]
                row[0] += w.weight / len(sole)
                row[1] += w.weight * vertices[i][1] / len(sole)
                row[2] += w.weight * vertices[i][2] / len(sole)
        self.centroid = tuple(sums)

    def roll_forward_offset(self):
        # Preserve the fixed foremost sole point's reference travel while rolling.
        # All canonical sole vertices belong fully to the distal paw bone.
        return paw_roll_forward_offset((self.neutral_y, self.neutral_z),
                                       (self.toe_y, self.toe_z), self.paw_pitch)

    def transforms(self, angles):
        angles = tuple(angles) + ((self.paw_pitch-sum(angles),) if len(self.heads) == 3 else ())
        transforms = []
        c, s, ty, tz, total = 1., 0., 0., -self.crouch, 0.
        for (hy, hz), angle in zip(self.heads, angles):
            py, pz = c*hy - s*hz + ty, s*hy + c*hz + tz
            total += angle
            c, s = cos(total), sin(total)
            ty, tz = py - c*hy + s*hz, pz - s*hy - c*hz
            transforms.append((c, s, ty, tz))
        transforms.append((1., 0., 0., -self.crouch))
        return transforms

    def measure(self, angles):
        transforms = self.transforms(angles)
        y = sum(c*wy - s*wz + ty*w for (w, wy, wz), (c, s, ty, tz)
                in zip(self.centroid, transforms))
        lowest = min(sum(transforms[i][1]*wy + transforms[i][0]*wz + transforms[i][3]*w
                         for i, w, wy, wz in row) for row in self.rows)
        return y, lowest

    def solve(self, target_y, target_z, seed):
        angles = list(seed)
        for _ in range(45):
            y, z = self.measure(angles)
            ey, ez = target_y-y, target_z-z
            if max(abs(ey), abs(ez)) < 1e-6:
                return tuple(angles)
            eps = 1e-5
            ya, za = self.measure((angles[0]+eps, angles[1]))
            yb, zb = self.measure((angles[0], angles[1]+eps))
            a, b, c, d = (ya-y)/eps, (yb-y)/eps, (za-z)/eps, (zb-z)/eps
            det = a*d-b*c
            if abs(det) < 1e-9:
                break
            da, db = (d*ey-b*ez)/det, (a*ez-c*ey)/det
            scale = min(1., .15 / max(abs(da), abs(db), 1e-12))
            angles[0] += da*scale
            angles[1] += db*scale
            if max(abs(v) for v in angles) > 2.6:
                break
        raise ValueError('Contact target is unreachable with the current limb proportions')


