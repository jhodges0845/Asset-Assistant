# SPDX-License-Identifier: GPL-3.0-or-later
"""Procedural mesh-editing pelvis experiment.

This prototype models by evolving a coarse mesh: create a seed cage, split it
with additional sections, move/scale those sections, and extrude two outlets.
The editing vocabulary is generic; this recipe supplies only coordinates.
"""
from dataclasses import dataclass
from math import cos, pi, sin


@dataclass(frozen=True)
class NeutralPelvisShape:
    width: float=34.0; depth: float=24.0; height: float=20.0
    waist_width: float=28.0; waist_depth: float=20.0
    hip_fullness: float=1.0; glute_projection: float=1.0
    crotch_width: float=7.0; crotch_depth: float=8.0; crotch_drop: float=1.0
    thigh_opening_width: float=12.0; thigh_opening_depth: float=13.0; thigh_spacing: float=4.0


def semantic_controls(): return tuple(NeutralPelvisShape.__dataclass_fields__)


def _section(cx, z, width, depth, sides=12, rear=0.0, side_drop=0.0):
    """Generic editable polygon section; used as temporary construction cage."""
    pts=[]
    for i in range(sides):
        a=2*pi*i/sides; c=cos(a); s=sin(a)
        x=cx+width*.5*c
        y=depth*.5*s + rear*max(0.0,-s)**2
        zz=z-side_drop*abs(c)**1.7
        pts.append((x,y,zz))
    return tuple(pts)


def _append_section(vertices, points):
    start=len(vertices); vertices.extend(points); return tuple(range(start,start+len(points)))


def _bridge(faces,a,b):
    if len(a)!=len(b): raise ValueError("editable sections require matching edge counts")
    n=len(a)
    for i in range(n): faces.append((a[i],a[(i+1)%n],b[(i+1)%n],b[i]))


def _cap_annulus(faces, outer, left, right):
    """Connect lower seed section to two extruded branches with a center saddle."""
    # Section indices: 0=+X, 3=front, 6=-X, 9=rear for 12 sides.
    # Outer halves flow into the corresponding outside halves of each branch.
    for i in range(9,16):
        a=outer[i%12]; b=outer[(i+1)%12]
        j=(i-9)%12
        faces.append((a,b,left[(j+1)%12],left[j]))
    for i in range(3,10):
        a=outer[i%12]; b=outer[(i+1)%12]
        j=(i-3)%12
        faces.append((a,b,right[(j+1)%12],right[j]))
    # Central front/rear bridge closes the branch split without a vertical wall.
    faces.append((outer[3],left[6],right[0]))
    faces.append((outer[9],right[6],left[0]))
    faces.append((left[6],left[7],right[11],right[0]))
    faces.append((left[5],left[6],right[0],right[1]))


def generate_neutral_pelvis(shape=None):
    p=shape or NeutralPelvisShape(); w,d,h=p.width,p.depth,p.height
    vertices=[]; faces=[]; sides=12

    # Artist-like construction history: begin with a very coarse torso-facing
    # seed, insert sections only where silhouette control is needed, and reshape
    # each new section before continuing downward.
    seed=_append_section(vertices,_section(0,h*.50,p.waist_width,p.waist_depth,sides,side_drop=h*.015))
    split_a=_append_section(vertices,_section(0,h*.28,w*.92,d*.94,sides,rear=-d*.025*p.glute_projection,side_drop=h*.035))
    split_b=_append_section(vertices,_section(0,h*.04,w*1.02*p.hip_fullness,d*1.02,sides,rear=-d*.080*p.glute_projection,side_drop=h*.055))
    lower=_append_section(vertices,_section(0,-h*.20,w*.88,d*.88,sides,rear=-d*.060*p.glute_projection,side_drop=h*.040))
    _bridge(faces,seed,split_a); _bridge(faces,split_a,split_b); _bridge(faces,split_b,lower)

    # Extrude two branches from the lower edited mass.  A wider root is created
    # first; a second extrusion reaches the public thigh opening.  These are
    # generic duplicate/move/scale operations expressed directly as sections.
    center=p.thigh_spacing*.5+p.thigh_opening_width*.5
    root_w=p.thigh_opening_width*1.20; root_d=p.thigh_opening_depth*1.22
    left_root=_append_section(vertices,_section(-center,-h*.24,root_w,root_d,sides,rear=-d*.025,side_drop=h*.020))
    right_root=_append_section(vertices,_section(center,-h*.24,root_w,root_d,sides,rear=-d*.025,side_drop=h*.020))
    _cap_annulus(faces,lower,left_root,right_root)

    left_out=_append_section(vertices,_section(-center,-h*.55,p.thigh_opening_width,p.thigh_opening_depth,sides,rear=-d*.010))
    right_out=_append_section(vertices,_section(center,-h*.55,p.thigh_opening_width,p.thigh_opening_depth,sides,rear=-d*.010))
    _bridge(faces,left_root,left_out); _bridge(faces,right_root,right_out)

    # Keep the established 16-sample attachment API independent of the coarse
    # editing cage.  Later the generic editor can resample selected boundary edges.
    def boundary(cx,z,width,depth):
        out=[]
        for i in range(16):
            a=2*pi*i/16; out.append((cx+width*.5*cos(a),depth*.5*sin(a),z))
        return tuple(_append_section(vertices,out))
    torso=boundary(0,h*.50,p.waist_width,p.waist_depth)
    left=boundary(-center,-h*.55,p.thigh_opening_width,p.thigh_opening_depth)
    right=boundary(center,-h*.55,p.thigh_opening_width,p.thigh_opening_depth)
    return tuple(vertices),tuple(tuple(reversed(f)) for f in faces),{"torso":torso,"left_thigh":left,"right_thigh":right}
