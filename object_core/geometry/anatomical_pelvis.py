# SPDX-License-Identifier: GPL-3.0-or-later
"""Anatomical landmark and surface profiles for the Human V2 pelvis."""
from math import cos, pi, sin
RING_SIDES=16

def pelvis_landmarks(z,width,depth,thigh_thickness):
    half_w=width*.5; half_d=depth*.5; hip_drop=max(1.2,thigh_thickness*.14); crotch_drop=max(3.0,thigh_thickness*.34); glute_drop=max(1.8,thigh_thickness*.20)
    return {"iliac.left":(half_w*.94,0.0,z+hip_drop*.35),"iliac.right":(-half_w*.94,0.0,z+hip_drop*.35),"trochanter.left":(half_w*1.02,-half_d*.03,z-hip_drop*.72),"trochanter.right":(-half_w*1.02,-half_d*.03,z-hip_drop*.72),"pubic.front":(0.0,half_d*.78,z-crotch_drop*.72),"crotch.center":(0.0,0.0,z-crotch_drop),"glute.left":(half_w*.48,-half_d*1.10,z-glute_drop),"glute.right":(-half_w*.48,-half_d*1.10,z-glute_drop)}

def pelvis_ring(z,width,depth,thigh_thickness):
    drop=max(1.0,thigh_thickness*.16); points=[]
    for i in range(RING_SIDES):
        a=2*pi*i/RING_SIDES; c,s=cos(a),sin(a); lateral=abs(c); rear=max(0.0,-s); front=max(0.0,s)
        points.append((width*.5*c,depth*.5*s-depth*.08*rear+depth*.015*front,z+drop*(.55*lateral-.45)))
    return tuple(points)

def pelvic_transition_ring(z,width,depth,thigh_thickness):
    drop=max(.5,thigh_thickness*.05); points=[]
    for i in range(RING_SIDES):
        a=2*pi*i/RING_SIDES; c,s=cos(a),sin(a); points.append((width*.5*c,depth*.5*s-depth*.035*max(0.0,-s),z+drop*(abs(c)-.5)))
    return tuple(points)

def pelvis_surface_ring(z,width,depth,thigh_thickness,descent):
    t=max(0.0,min(1.0,descent)); lm=pelvis_landmarks(z,width,depth,thigh_thickness); crotch_z=lm["crotch.center"][2]; iliac_z=lm["iliac.left"][2]; glute_z=lm["glute.left"][2]; points=[]
    for i in range(RING_SIDES):
        a=2*pi*i/RING_SIDES; c,s=cos(a),sin(a); lateral=abs(c); medial=1.0-lateral; rear=max(0.0,-s); front=max(0.0,s)
        x=width*.5*(1.0-t*(.07+.10*medial))*c; y=depth*.5*(1.0-.04*t)*s-depth*rear*(.07+.12*t)+depth*front*.015*(1.0-t)
        target=iliac_z*lateral+crotch_z*medial; target=target*(1.0-.28*rear)+glute_z*(.28*rear); points.append((x,y,z*(1.0-t)+target*t))
    return tuple(points)

def pelvis_thigh_paths(z,width,depth,thigh_thickness):
    """Expose longitudinal anatomical paths that future topology can connect directly."""
    lm=pelvis_landmarks(z,width,depth,thigh_thickness); paths={}
    for side in ("left","right"):
        sign=1.0 if side=="left" else -1.0; iliac=lm["iliac."+side]; troch=lm["trochanter."+side]; glute=lm["glute."+side]
        paths["outer."+side]=(iliac,troch,(troch[0]*.96,troch[1],troch[2]-thigh_thickness*.28))
        paths["rear."+side]=(glute,(glute[0]*1.06,glute[1]*.92,glute[2]-thigh_thickness*.18),(sign*width*.24,-depth*.42,glute[2]-thigh_thickness*.38))
        paths["inner."+side]=(lm["crotch.center"],(sign*width*.12,0.0,lm["crotch.center"][2]-thigh_thickness*.10),(sign*width*.18,0.0,lm["crotch.center"][2]-thigh_thickness*.34))
    return paths

def upper_thigh_ring(center,width,depth,side,pelvis_influence):
    sign=1.0 if side=="left" else -1.0; points=[]
    for i in range(RING_SIDES):
        a=2*pi*i/RING_SIDES; c,s=cos(a),sin(a); lateral=max(0.0,sign*c); medial=max(0.0,-sign*c); rear=max(0.0,-s); front=max(0.0,s)
        x=center[0]+width*.5*c+sign*width*pelvis_influence*(.08*lateral-.045*medial); y=center[1]+depth*.5*s-depth*pelvis_influence*.12*rear+depth*pelvis_influence*.02*front; points.append((x,y,center[2]))
    return tuple(points)

def thigh_opening_ring(center,width,depth,side,pelvis_influence):
    """Shape a non-planar thigh root with a broad medial saddle.

    The medial vertices previously dropped much farther than their neighbours,
    producing a pointed crotch wedge in clay.  Spread that descent into the
    front/rear-medial quadrants and taper it as rows travel down the thigh so the
    crotch resolves into two continuous inner-thigh paths instead of a V-shaped fan.
    """
    sign=1.0 if side=="left" else -1.0; base=upper_thigh_ring(center,width,depth,side,pelvis_influence); relief=max(1.2,width*.16); points=[]
    for i,(x,y,_) in enumerate(base):
        a=2*pi*i/RING_SIDES; c,s=cos(a),sin(a); lateral=max(0.0,sign*c); medial=max(0.0,-sign*c); rear=max(0.0,-s); front=max(0.0,s)
        # A softer medial depression keeps the opening anatomical without making
        # the innermost vertex a spike.  Adjacent front/rear vertices share part
        # of the descent, creating a saddle rather than a triangular notch.
        medial_blend=medial*(.48+.20*(front+rear))
        vz=center[2]+relief*(.50*lateral-.43*medial_blend-.08*front-.04*rear)
        # Pull the medial surface slightly toward the thigh centre and keep the
        # posterior seam rounded as it leaves the glute mass.
        x-=sign*width*pelvis_influence*.018*medial
        y-=depth*pelvis_influence*(.035*rear*medial-.012*front*medial)
        points.append((x,y,vz))
    return tuple(points)