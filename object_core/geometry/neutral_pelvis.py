# SPDX-License-Identifier: GPL-3.0-or-later
"""Procedural mesh-editing pelvis experiment.

The recipe evolves a coarse mesh using generic modeling ideas: create a cage,
insert/split topology where needed, reshape selected vertices, then extrude
selected boundaries.  Object meaning is kept out of the editing helpers.
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


def _loop(cx,z,width,depth,sides=16,rear=0.0,side_drop=0.0):
    pts=[]
    for i in range(sides):
        a=2*pi*i/sides; c=cos(a); s=sin(a)
        pts.append((cx+width*.5*c,
                    depth*.5*s + rear*max(0.0,-s)**2,
                    z-side_drop*abs(c)**1.7))
    return tuple(pts)


def _append(vertices, points):
    start=len(vertices); vertices.extend(points); return tuple(range(start,start+len(points)))


def _bridge(faces,a,b):
    if len(a)!=len(b): raise ValueError("boundary sizes must match")
    for i in range(len(a)):
        j=(i+1)%len(a); faces.append((a[i],a[j],b[j],b[i]))


def _strip(faces,a,b):
    """Bridge two open edge chains, the generic equivalent of filling a strip."""
    if len(a)!=len(b): raise ValueError("edge chains must match")
    for i in range(len(a)-1): faces.append((a[i],a[i+1],b[i+1],b[i]))


def generate_neutral_pelvis(shape=None):
    p=shape or NeutralPelvisShape(); w,d,h=p.width,p.depth,p.height
    vertices=[]; faces=[]; n=16

    # Start coarse and insert three horizontal cuts while shaping the main mass.
    top=_append(vertices,_loop(0,h*.50,p.waist_width,p.waist_depth,n,side_drop=h*.010))
    a=_append(vertices,_loop(0,h*.29,w*.91,d*.93,n,rear=-d*.020*p.glute_projection,side_drop=h*.030))
    b=_append(vertices,_loop(0,h*.07,w*1.00*p.hip_fullness,d*1.00,n,rear=-d*.070*p.glute_projection,side_drop=h*.050))
    lower=_append(vertices,_loop(0,-h*.16,w*.90,d*.89,n,rear=-d*.050*p.glute_projection,side_drop=h*.045))
    _bridge(faces,top,a); _bridge(faces,a,b); _bridge(faces,b,lower)

    # SPLIT operation: rather than attaching two complete loops to `lower`, use
    # its existing front/rear/lateral vertices as the outside boundary and add
    # only the new center-cut vertices required to form two selectable openings.
    # Loop indexing: 0=right, 4=front, 8=left, 12=rear.
    gap=p.thigh_spacing*.5
    root_z=-h*.20
    front_y=d*.40; rear_y=-d*(.43+.025*p.glute_projection)
    inner_front_l=_append(vertices,(( -gap,front_y,root_z+h*.035),))[0]
    inner_rear_l =_append(vertices,(( -gap,rear_y, root_z+h*.020),))[0]
    inner_front_r=_append(vertices,((  gap,front_y,root_z+h*.035),))[0]
    inner_rear_r =_append(vertices,((  gap,rear_y, root_z+h*.020),))[0]

    # New opening boundaries reuse the lower cage's outside vertices.  Each is
    # an 8-edge polygon made by the split, not a separately generated tube.
    left_root=(lower[8],lower[7],lower[6],lower[5],lower[4],inner_front_l,inner_rear_l,lower[12])
    right_root=(lower[0],lower[15],lower[14],lower[13],lower[12],inner_rear_r,inner_front_r,lower[4])

    # Fill the remaining lower surface with local strips/faces.  No long fan
    # triangles cross from the center to unrelated vertices.
    faces.extend([
        (lower[4],lower[5],lower[6],lower[7],lower[8],inner_front_l),
        (lower[12],inner_rear_l,lower[8],lower[9],lower[10],lower[11]),
        (lower[0],lower[1],lower[2],lower[3],lower[4],inner_front_r),
        (lower[12],lower[13],lower[14],lower[15],lower[0],inner_rear_r),
        (inner_front_l,inner_front_r,inner_rear_r,inner_rear_l),
    ])

    # EXTRUDE operation: duplicate each selected opening boundary downward and
    # reshape the duplicate.  This is deliberately the same conceptual action
    # an artist performs after selecting the new lower faces/edge loops.
    center=gap+p.thigh_opening_width*.5
    out_z=-h*.55
    def outlet(sign):
        pts=[]
        for i in range(8):
            a=2*pi*i/8
            pts.append((sign*center+p.thigh_opening_width*.5*cos(a),
                        p.thigh_opening_depth*.5*sin(a),out_z))
        return _append(vertices,pts)
    left_out=outlet(-1); right_out=outlet(1)
    _bridge(faces,left_root,left_out); _bridge(faces,right_root,right_out)

    # Public boundaries remain 16 samples.  They are independent API metadata;
    # the editing cage is free to use the topology appropriate to each operation.
    def public_loop(cx,z,width,depth): return _append(vertices,_loop(cx,z,width,depth,16))
    torso=public_loop(0,h*.50,p.waist_width,p.waist_depth)
    left=public_loop(-center,out_z,p.thigh_opening_width,p.thigh_opening_depth)
    right=public_loop(center,out_z,p.thigh_opening_width,p.thigh_opening_depth)
    return tuple(vertices),tuple(tuple(reversed(f)) for f in faces),{
        "torso":torso,"left_thigh":left,"right_thigh":right,
    }
