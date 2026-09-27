# SPDX-License-Identifier: GPL-3.0-or-later
"""Portable measurements for canine review surfaces in centimeters."""
from math import isfinite


def limb_ground_clearance(vertices, regions):
    """Measure lowest authored limb vertices against the recipe's Z=0 plane.

    Positive clearance means a gap; negative clearance means penetration.
    These static measurements do not establish stance contact or gait quality.
    """
    result = {}
    for region in regions:
        if not region.name.startswith('leg.'):
            continue
        if not region.vertex_indices:
            raise ValueError('Ground review requires bound limb regions')
        heights = [vertices[index][2] for index in region.vertex_indices]
        if not all(isfinite(z) for z in heights):
            raise ValueError('Ground review requires finite limb heights')
        lowest = min(heights)
        result[region.name] = {
            'minimum_z_cm': lowest,
            'penetration_cm': max(0.0, -lowest),
            'gap_cm': max(0.0, lowest),
        }
    if not result:
        raise ValueError('Ground review requires authored limb regions')
    return result


def _convex_hull(points):
    points = sorted(set(points))
    if len(points) < 3:
        return points

    def cross(a, b, c):
        return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])

    halves = []
    for ordered in (points, reversed(points)):
        half = []
        for point in ordered:
            while len(half) >= 2 and cross(half[-2], half[-1], point) <= 0:
                half.pop()
            half.append(point)
        halves.append(half[:-1])
    return halves[0] + halves[1]


def limb_support_footprint(vertices, faces, regions, tolerance_cm=0.1):
    """XY hull of each authored limb surface in the band Z=0..tolerance.

    Edge intersections include sloped faces even when no vertex lies in the
    band. The hull is a near-ground envelope, not physical contact area: it
    spans concavities/disconnected patches and does not establish gait support.
    Penetration is excluded and must be read with limb_ground_clearance.
    """
    if not isfinite(tolerance_cm) or tolerance_cm <= 0:
        raise ValueError('Support review requires a positive finite tolerance')
    regions = tuple(regions)
    limb_ground_clearance(vertices, regions)
    edges = {tuple(sorted((a, b))) for face in faces
             for a, b in zip(face, face[1:] + face[:1])}
    result = {}
    for region in regions:
        if not region.name.startswith('leg.'):
            continue
        owned = set(region.vertex_indices)
        if not all(all(isfinite(c) for c in vertices[i]) for i in owned):
            raise ValueError('Support review requires finite limb coordinates')
        points = [tuple(vertices[i][:2]) for i in owned if 0 <= vertices[i][2] <= tolerance_cm]
        for a, b in edges:
            if a not in owned or b not in owned:
                continue
            start, end = vertices[a], vertices[b]
            if start[2] == end[2]:
                continue
            for plane in (0.0, tolerance_cm):
                if min(start[2], end[2]) < plane < max(start[2], end[2]):
                    t = (plane - start[2]) / (end[2] - start[2])
                    points.append(tuple(start[k] + t * (end[k] - start[k]) for k in (0, 1)))
        hull = _convex_hull(points)
        area = abs(sum(a[0] * b[1] - b[0] * a[1]
                       for a, b in zip(hull, hull[1:] + hull[:1]))) / 2
        result[region.name] = {
            'tolerance_cm': tolerance_cm,
            'near_ground_hull_area_cm2': area,
            'width_cm': max(p[0] for p in hull) - min(p[0] for p in hull) if hull else 0.0,
            'length_cm': max(p[1] for p in hull) - min(p[1] for p in hull) if hull else 0.0,
        }
    return result
