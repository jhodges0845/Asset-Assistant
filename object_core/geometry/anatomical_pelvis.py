# SPDX-License-Identifier: GPL-3.0-or-later
"""Shared anatomical profiles for the Human V2 pelvis and upper thighs.

This module deliberately owns the transition between lower torso and both legs. It
keeps pelvis-specific anatomy out of the generic deformable helpers and gives the
constructor one place to describe iliac width, groin descent, glute projection and
upper-thigh convergence.
"""

from math import cos, pi, sin

RING_SIDES = 16


def pelvis_ring(z, width, depth, thigh_thickness):
    """Return the upper iliac boundary of the shared pelvis."""
    drop = max(1.0, thigh_thickness * 0.16)
    points = []
    for i in range(RING_SIDES):
        angle = 2 * pi * i / RING_SIDES
        c, s = cos(angle), sin(angle)
        lateral = abs(c)
        rear = max(0.0, -s)
        front = max(0.0, s)
        x = width * 0.5 * c
        y = depth * 0.5 * s - depth * 0.08 * rear + depth * 0.015 * front
        vz = z + drop * (0.55 * lateral - 0.45)
        points.append((x, y, vz))
    return tuple(points)


def pelvic_transition_ring(z, width, depth, thigh_thickness):
    """Return the ring above the iliac boundary with pelvic shape fading into torso."""
    drop = max(0.5, thigh_thickness * 0.05)
    points = []
    for i in range(RING_SIDES):
        angle = 2 * pi * i / RING_SIDES
        c, s = cos(angle), sin(angle)
        lateral = abs(c)
        rear = max(0.0, -s)
        x = width * 0.5 * c
        y = depth * 0.5 * s - depth * 0.035 * rear
        vz = z + drop * (lateral - 0.5)
        points.append((x, y, vz))
    return tuple(points)


def pelvis_surface_ring(z, width, depth, thigh_thickness, descent):
    """Return an intermediate pelvis loop between iliac crest and thigh openings."""
    t = max(0.0, min(1.0, descent))
    drop = max(2.0, thigh_thickness * (0.18 + 0.34 * t))
    points = []
    for i in range(RING_SIDES):
        angle = 2 * pi * i / RING_SIDES
        c, s = cos(angle), sin(angle)
        lateral = abs(c)
        medial = 1.0 - lateral
        rear = max(0.0, -s)
        front = max(0.0, s)
        width_scale = 1.0 - t * (0.10 + 0.12 * medial)
        x = width * 0.5 * width_scale * c
        depth_scale = 1.0 - 0.08 * t
        y = depth * 0.5 * depth_scale * s
        y -= depth * rear * (0.08 + 0.10 * t)
        y += depth * front * (0.01 + 0.015 * (1.0 - t))
        sector_drop = 0.35 + 0.65 * medial + 0.12 * front + 0.05 * rear
        vz = z - drop * sector_drop
        points.append((x, y, vz))
    return tuple(points)


def upper_thigh_ring(center, width, depth, side, pelvis_influence):
    """Return a thigh ring whose root inherits pelvic/glute shape and then fades."""
    sign = 1.0 if side == "left" else -1.0
    points = []
    for i in range(RING_SIDES):
        angle = 2 * pi * i / RING_SIDES
        c, s = cos(angle), sin(angle)
        lateral = max(0.0, sign * c)
        medial = max(0.0, -sign * c)
        rear = max(0.0, -s)
        front = max(0.0, s)
        x = center[0] + width * 0.5 * c
        x += sign * width * pelvis_influence * (0.08 * lateral - 0.045 * medial)
        y = center[1] + depth * 0.5 * s
        y -= depth * pelvis_influence * 0.12 * rear
        y += depth * pelvis_influence * 0.02 * front
        points.append((x, y, center[2]))
    return tuple(points)


def thigh_opening_ring(center, width, depth, side, pelvis_influence):
    """Return a non-planar anatomical thigh opening for the pelvis split.

    The outer hip sits higher than the inner-thigh origin, while the rear quadrant
    carries glute depth downward.  The pair-of-pants bridge can therefore follow an
    anatomical saddle instead of terminating at a horizontal cylindrical leg ring.
    """
    sign = 1.0 if side == "left" else -1.0
    base = upper_thigh_ring(center, width, depth, side, pelvis_influence)
    relief = max(1.2, width * 0.16)
    points = []
    for i, (x, y, _) in enumerate(base):
        angle = 2 * pi * i / RING_SIDES
        c, s = cos(angle), sin(angle)
        lateral = max(0.0, sign * c)
        medial = max(0.0, -sign * c)
        rear = max(0.0, -s)
        front = max(0.0, s)
        z = center[2] + relief * (0.55 * lateral - 0.70 * medial - 0.12 * front - 0.05 * rear)
        # Carry the glute fold into the opening rather than making it a separate shelf.
        y -= depth * pelvis_influence * 0.055 * rear * medial
        points.append((x, y, z))
    return tuple(points)
