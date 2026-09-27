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
