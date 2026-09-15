# SPDX-License-Identifier: GPL-3.0-or-later
"""Shared anatomical profiles for the Human V2 pelvis and upper thighs.

This module deliberately owns the transition between lower torso and both legs.  It
keeps pelvis-specific anatomy out of the generic deformable helpers and gives the
constructor one place to describe iliac width, groin descent, glute projection and
upper-thigh convergence.
"""

from math import cos, pi, sin

RING_SIDES = 16


def pelvis_ring(z, width, depth, thigh_thickness):
    """Return a non-planar 16-point pelvic boundary.

    Lateral vertices form the iliac crest, medial front/rear vertices descend toward
    the groin, the rear half projects for gluteal volume, and the front remains more
    restrained.  Left and right are generated from the same field so symmetry is
    exact rather than repaired after construction.
    """
    drop = max(1.0, thigh_thickness * 0.20)
    points = []
    for i in range(RING_SIDES):
        angle = 2 * pi * i / RING_SIDES
        c, s = cos(angle), sin(angle)
        lateral = abs(c)
        medial = 1.0 - lateral
        rear = max(0.0, -s)
        front = max(0.0, s)
        x = width * 0.5 * c
        y = depth * 0.5 * s - depth * 0.14 * rear + depth * 0.025 * front
        vz = z - drop * medial + drop * 0.28 * lateral
        points.append((x, y, vz))
    return tuple(points)


def pelvic_transition_ring(z, width, depth, thigh_thickness):
    """Return the ring immediately above the pelvis with fading pelvic anatomy."""
    drop = max(0.6, thigh_thickness * 0.08)
    points = []
    for i in range(RING_SIDES):
        angle = 2 * pi * i / RING_SIDES
        c, s = cos(angle), sin(angle)
        lateral = abs(c)
        rear = max(0.0, -s)
        x = width * 0.5 * c
        y = depth * 0.5 * s - depth * 0.055 * rear
        vz = z + drop * (lateral - 0.5)
        points.append((x, y, vz))
    return tuple(points)


def upper_thigh_ring(center, width, depth, side, pelvis_influence):
    """Return a thigh-root ring whose shape is inherited from the shared pelvis.

    The influence fades to zero before mid-thigh.  Lateral hip and rear glute volume
    therefore continue through the root while the medial quadrant converges toward
    the groin instead of producing a circular tube directly below the torso.
    """
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
        x += sign * width * pelvis_influence * (0.12 * lateral - 0.075 * medial)
        y = center[1] + depth * 0.5 * s
        y -= depth * pelvis_influence * 0.17 * rear
        y += depth * pelvis_influence * 0.025 * front
        points.append((x, y, center[2]))
    return tuple(points)
