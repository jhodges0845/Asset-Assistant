# SPDX-License-Identifier: GPL-3.0-or-later
"""Procedural mesh-editing pelvis experiment.

Build a coarse cage, split its lower topology in place, reshape the resulting
openings, then extrude those exact boundaries. Helpers are generic mesh-editing
operations; object-specific intent remains in the recipe.
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


def _append(vertices,points):
    start=len(vertices); vertices.extend(points); return tuple(range(start,start+len(points)))


def _bridge(faces,a,b):
    if len(a)!=len(b): raise ValueError("boundary sizes must match")
    for i in range(len(a)):
        j=(i+1)%len(a); faces.append((a[i],a[j],b[j],b[i]))


def _extrude_boundary(vertices,faces,boundary,target_points):
    """Generic polygon-modeling extrusion of an existing selected boundary."""
    if len(boundary)!=len(target_points): raise ValueError("extrusion sizes must match")
    result=_append(vertices,target_points)
    _bridge(faces,boundary,result)
    return result


def generate_neutral_pelvis(shape=None):
    p=shape or NeutralPelvisShape(); w,d,h=p.width,p.depth,p.height
    vertices=[]; faces=[]; n=16

    # Coarse mass plus inserted horizontal cuts. These establish only the large
    # silhouette before any branch topology exists.
    top=_append(vertices,_loop(0,h*.50,p.waist_width,p.waist_depth,n,side_drop=h*.010))
    a=_append(vertices,_loop(0,h*.29,w*.91,d*.93,n,rear=-d*.020*p.glute_projection,side_drop=h*.030))
    b=_append(vertices,_loop(0,h*.07,w*1.00*p.hip_fullness,d*1.00,n,rear=-d*.070*p.glute_projection,side_drop=h*.050))
    lower=_append(vertices,_loop(0,-h*.16,w*.90,d*.89,n,rear=-d*.050*p.glute_projection,side_drop=h*.045))
    _bridge(faces,top,a); _bridge(faces,a,b); _bridge(faces,b,lower)

    # Split the bottom IN PLACE. Existing lower vertices remain the outer edges
    # of the two selected openings; only four center-cut vertices are inserted.
    # 0=right, 4=front, 8=left, 12=rear.
    gap=p.thigh_spacing*.5
    front_y=d*.40; rear_y=-d*(.43+.025*p.glute_projection)
    cut_z=-h*.16
    lf=_append(vertices,((-gap,front_y,cut_z+h*.035),))[0]
    lr=_append(vertices,((-gap,rear_y,cut_z+h*.020),))[0]
    rf=_append(vertices,(( gap,front_y,cut_z+h*.035),))[0]
    rr=_append(vertices,(( gap,rear_y,cut_z+h*.020),))[0]

    # Selected edge loops created by the split. Notice that their outer vertices
    # are literally `lower` vertices, so there can be no separate root seam.
    left_open=(lower[8],lower[7],lower[6],lower[5],lower[4],lf,lr,lower[12])
    right_open=(lower[0],lower[15],lower[14],lower[13],lower[12],rr,rf,lower[4])

    # Rebuild only the bottom faces around those openings. These local polygons
    # are analogous to an artist cutting the original bottom face into regions.
    faces.extend([
        (lower[8],lower[9],lower[10],lower[11],lower[12],lr),
        (lower[8],lf,lower[4],lower[5],lower[6],lower[7]),
        (lower[12],lower[13],lower[14],lower[15],lower[0],rr),
        (lower[4],rf,lower[0],lower[1],lower[2],lower[3]),
        (lf,rf,rr,lr),
    ])

    # First extrusion is deliberately short. This is the equivalent of pulling
    # the selected openings down a little and reshaping the new vertices before
    # performing the longer extrusion to the attachment boundary.
    center=gap+p.thigh_opening_width*.5
    root_z=-h*.25
    root_w=p.thigh_opening_width*1.12; root_d=p.thigh_opening_depth*1.12
    def target(sign,z,width,depth):
        # Eight points match the split opening; phase places samples at lateral,
        # diagonal, front, diagonal, medial, diagonal, rear, diagonal positions.
        pts=[]
        for i in range(8):
            ang=pi*i/4
            pts.append((sign*center + width*.5*cos(ang), depth*.5*sin(ang), z))
        return tuple(pts)
    left_root=_extrude_boundary(vertices,faces,left_open,target(-1,root_z,root_w,root_d))
    right_root=_extrude_boundary(vertices,faces,right_open,target(1,root_z,root_w,root_d))

    # Second extrusion reaches the thigh attachment. Because it starts from the
    # just-extruded boundaries, the construction history remains continuous.
    out_z=-h*.55
    left_out=_extrude_boundary(vertices,faces,left_root,target(-1,out_z,p.thigh_opening_width,p.thigh_opening_depth))
    right_out=_extrude_boundary(vertices,faces,right_root,target(1,out_z,p.thigh_opening_width,p.thigh_opening_depth))

    # Public attachment metadata is still 16 samples; internal modeling topology
    # is intentionally independent so future generic resampling can own this step.
    def public_loop(cx,z,width,depth): return _append(vertices,_loop(cx,z,width,depth,16))
    torso=public_loop(0,h*.50,p.waist_width,p.waist_depth)
    left=public_loop(-center,out_z,p.thigh_opening_width,p.thigh_opening_depth)
    right=public_loop(center,out_z,p.thigh_opening_width,p.thigh_opening_depth)
    return tuple(vertices),tuple(tuple(reversed(f)) for f in faces),{
        "torso":torso,"left_thigh":left,"right_thigh":right,
    }
