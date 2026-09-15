# SPDX-License-Identifier: GPL-3.0-or-later
"""Anatomical landmark and surface profiles for the Human V2 pelvis.

Human V2 treats the pelvis as an anatomical surface, not merely a stack of torso
rings. The landmark field gives the constructor stable semantic anchors for iliac
crest, greater trochanter, pubic/crotch and glute regions while retaining the
existing 16-point boundary contract during migration.
"""

from math import cos, pi, sin

RING_SIDES = 16


def pelvis_landmarks(z, width, depth, thigh_thickness):
    """Return bilateral anatomical anchors used to construct the lower pelvis."""
    half_w = width * 0.5
    half_d = depth * 0.5
    hip_drop = max(1.2, thigh_thickness * 0.14)
    crotch_drop = max(3.0, thigh_thickness * 0.34)
    glute_drop = max(1.8, thigh_thickness * 0.20)
    return {
        "iliac.left": (half_w * 0.94, 0.0, z + hip_drop * 0.35),
        "iliac.right": (-half_w * 0.94, 0.0, z + hip_drop * 0.35),
        "trochanter.left": (half_w * 1.02, -half_d * 0.03, z - hip_drop * 0.72),
        "trochanter.right": (-half_w * 1.02, -half_d * 0.03, z - hip_drop * 0.72),
        "pubic.front": (0.0, half_d * 0.78, z - crotch_drop * 0.72),
        "crotch.center": (0.0, 0.0, z - crotch_drop),
        "glute.left": (half_w * 0.48, -half_d * 1.10, z - glute_drop),
        "glute.right": (-half_w * 0.48, -half_d * 1.10, z - glute_drop),
    }


def pelvis_ring(z, width, depth, thigh_thickness):
    drop = max(1.0, thigh_thickness * 0.16)
    points = []
    for i in range(RING_SIDES):
        angle = 2 * pi * i / RING_SIDES
        c, s = cos(angle), sin(angle)
        lateral = abs(c); rear = max(0.0, -s); front = max(0.0, s)
        points.append((width*.5*c, depth*.5*s-depth*.08*rear+depth*.015*front,
                       z+drop*(.55*lateral-.45)))
    return tuple(points)


def pelvic_transition_ring(z, width, depth, thigh_thickness):
    drop = max(0.5, thigh_thickness * 0.05)
    points = []
    for i in range(RING_SIDES):
        angle=2*pi*i/RING_SIDES; c,s=cos(angle),sin(angle)
        lateral=abs(c); rear=max(0.0,-s)
        points.append((width*.5*c, depth*.5*s-depth*.035*rear, z+drop*(lateral-.5)))
    return tuple(points)


def pelvis_surface_ring(z, width, depth, thigh_thickness, descent):
    """Sample a landmark-driven intermediate pelvic surface loop."""
    t=max(0.0,min(1.0,descent)); lm=pelvis_landmarks(z,width,depth,thigh_thickness)
    crotch_z=lm["crotch.center"][2]; iliac_z=lm["iliac.left"][2]; glute_z=lm["glute.left"][2]
    points=[]
    for i in range(RING_SIDES):
        angle=2*pi*i/RING_SIDES; c,s=cos(angle),sin(angle)
        lateral=abs(c); medial=1.0-lateral; rear=max(0.0,-s); front=max(0.0,s)
        x=width*.5*(1.0-t*(.07+.10*medial))*c
        y=depth*.5*(1.0-.04*t)*s-depth*rear*(.07+.12*t)+depth*front*.015*(1.0-t)
        target=iliac_z*lateral+crotch_z*medial
        target=target*(1.0-.28*rear)+glute_z*(.28*rear)
        points.append((x,y,z*(1.0-t)+target*t))
    return tuple(points)


def upper_thigh_ring(center,width,depth,side,pelvis_influence):
    sign=1.0 if side=="left" else -1.0; points=[]
    for i in range(RING_SIDES):
        angle=2*pi*i/RING_SIDES; c,s=cos(angle),sin(angle)
        lateral=max(0.0,sign*c); medial=max(0.0,-sign*c); rear=max(0.0,-s); front=max(0.0,s)
        x=center[0]+width*.5*c+sign*width*pelvis_influence*(.08*lateral-.045*medial)
        y=center[1]+depth*.5*s-depth*pelvis_influence*.12*rear+depth*pelvis_influence*.02*front
        points.append((x,y,center[2]))
    return tuple(points)


def thigh_opening_ring(center,width,depth,side,pelvis_influence):
    sign=1.0 if side=="left" else -1.0; base=upper_thigh_ring(center,width,depth,side,pelvis_influence)
    relief=max(1.2,width*.16); points=[]
    for i,(x,y,_) in enumerate(base):
        angle=2*pi*i/RING_SIDES; c,s=cos(angle),sin(angle)
        lateral=max(0.0,sign*c); medial=max(0.0,-sign*c); rear=max(0.0,-s); front=max(0.0,s)
        vz=center[2]+relief*(.55*lateral-.70*medial-.12*front-.05*rear)
        y-=depth*pelvis_influence*.055*rear*medial
        points.append((x,y,vz))
    return tuple(points)
