# SPDX-License-Identifier: GPL-3.0-or-later
"""Anatomy-oriented connected Human topology construction."""

from collections import defaultdict, deque
from math import cos, pi, sin
from ..models.mesh import MeshPart, ObjectMesh
from ..models.proportions import HumanoidProportions
from ..proportions.landmarks import generate_landmarks
from .deformable import _append_branch, _generate_face_atlas_uvs, _human_body_sections, _lerp_point, _shape_head_surface, _supported_joint_chain

_TORSO_RING_SIDES=16; _LEGACY_RING_SIDES=8; _LEG_RING_SIDES=16
_HIP_OPENING_LEVEL=0; _SHOULDER_OPENING_LEVEL=5; _TORSO_LAST_LEVEL=6

def _ellipse_ring(z,width,depth,sides):
    return tuple((width*.5*cos(2*pi*i/sides),depth*.5*sin(2*pi*i/sides),z) for i in range(sides))

def _pelvis_ring(z,width,depth,p):
    """Build the lower torso boundary as a pelvic saddle, not a flat belt.

    The lateral iliac region sits higher, the medial front/rear boundary descends
    toward the groin, and the rear half carries extra gluteal depth.  The same ring
    is subsequently shared by the torso bands and both leg openings, so pelvis and
    upper thighs begin from one anatomical region rather than independent cylinders.
    """
    points=[]
    drop=max(1.0,p.thigh_thickness_cm*.18)
    for i in range(_TORSO_RING_SIDES):
        angle=2*pi*i/_TORSO_RING_SIDES; c=cos(angle); s=sin(angle)
        lateral=abs(c); medial=1.0-lateral; rear=max(0.0,-s)
        x=width*.5*c
        y=depth*.5*s-depth*.10*rear
        vz=z-drop*medial+drop*.22*lateral
        points.append((x,y,vz))
    return tuple(points)

def _append_equal_ring_band(vertices,faces,lower,upper,face_map,level):
    if len(lower)!=len(upper): raise ValueError("equal ring band requires matching ring sizes")
    for i in range(len(lower)):
        j=(i+1)%len(lower); face_map[(level,i)]=len(faces); faces.append((lower[i],lower[j],upper[j],upper[i]))

def _append_16_to_8_transition(faces,lower,upper):
    if len(lower)!=16 or len(upper)!=8: raise ValueError("transition expects a 16-point lower and 8-point upper ring")
    for i in range(8):
        a,b,c=lower[2*i],lower[2*i+1],lower[(2*i+2)%16]; u,v=upper[i],upper[(i+1)%8]
        faces.append((a,b,u)); faces.append((b,c,v,u))

def _build_body(p,hip_z,shoulder_z,chin_z,crown_z):
    sections=_human_body_sections(p,hip_z,shoulder_z,chin_z,crown_z); rings=[]; vertices=[]
    for level,(z,w,d) in enumerate(sections):
        sides=16 if level<=_TORSO_LAST_LEVEL else 8
        ring=_pelvis_ring(z,w,d,p) if level==_HIP_OPENING_LEVEL else _ellipse_ring(z,w,d,sides)
        start=len(vertices); vertices.extend(ring); rings.append(tuple(range(start,start+sides)))
    faces=[tuple(reversed(rings[0]))]; fmap={}
    for level in range(len(rings)-1):
        if len(rings[level])==len(rings[level+1]): _append_equal_ring_band(vertices,faces,rings[level],rings[level+1],fmap,level)
        else: _append_16_to_8_transition(faces,rings[level],rings[level+1])
    faces.append(tuple(rings[-1])); return vertices,faces,fmap

def _opening_face(faces,fmap,level,side):
    segment=0 if side=="left" else 7; return fmap[(level,segment)],faces[fmap[(level,segment)]]

def _pelvis_thigh_ring(center,width,depth,side,blend):
    sign=1.0 if side=="left" else -1.0; result=[]
    for i in range(_LEG_RING_SIDES):
        angle=2*pi*i/_LEG_RING_SIDES; c=cos(angle); s=sin(angle); lateral=max(0.0,sign*c); medial=max(0.0,-sign*c); rear=max(0.0,-s)
        x=center[0]+width*.5*c+sign*width*blend*(.10*lateral-.055*medial)
        y=center[1]+depth*.5*s-depth*blend*.14*rear
        result.append((x,y,center[2]))
    return tuple(result)

def _append_anatomical_leg(vertices,faces,opening,hip,knee,ankle,p,side):
    """Continue the shared pelvic region through thigh, knee, calf, ankle and foot."""
    sections=((_lerp_point(hip,knee,.08),p.thigh_thickness_cm*1.12,p.thigh_thickness_cm*1.08,.90),(_lerp_point(hip,knee,.18),p.thigh_thickness_cm*1.10,p.thigh_thickness_cm*1.06,.62),(_lerp_point(hip,knee,.30),p.thigh_thickness_cm*1.04,p.thigh_thickness_cm,.34),(_lerp_point(hip,knee,.52),p.thigh_thickness_cm*.94,p.thigh_thickness_cm*.92,0.0),(_lerp_point(hip,knee,.82),p.calf_thickness_cm*1.04,p.calf_thickness_cm*.96,0.0),(knee,p.calf_thickness_cm*.92,p.calf_thickness_cm*.88,0.0),(_lerp_point(knee,ankle,.18),p.calf_thickness_cm*.98,p.calf_thickness_cm*.94,0.0),(_lerp_point(knee,ankle,.38),p.calf_thickness_cm*1.08,p.calf_thickness_cm,0.0),(_lerp_point(knee,ankle,.55),p.calf_thickness_cm*1.12,p.calf_thickness_cm*1.04,0.0),(_lerp_point(knee,ankle,.76),p.calf_thickness_cm*.84,p.calf_thickness_cm*.80,0.0),(ankle,p.calf_thickness_cm*.60,p.calf_thickness_cm*.58,0.0))
    center,width,depth,blend=sections[0]; shaped=_pelvis_thigh_ring(center,width,depth,side,blend); ring=[None]*16; cardinal=(0,4,8,12)
    for slot,vertex_index in zip(cardinal,opening): ring[slot]=vertex_index
    for i in range(16):
        if ring[i] is None: ring[i]=len(vertices); vertices.append(shaped[i])
    first=tuple(ring)
    for sector in range(4):
        a=cardinal[sector]; b=cardinal[(sector+1)%4]; end=16 if sector==3 else b
        for i in range(a,end-1): faces.append((first[i%16],first[(i+1)%16],opening[(sector+1)%4]))
    rings=[first]
    for center,width,depth,blend in sections[1:]:
        shaped=_pelvis_thigh_ring(center,width,depth,side,blend); current=[]
        for point in shaped: current.append(len(vertices)); vertices.append(point)
        current=tuple(current)
        for i in range(16): faces.append((rings[-1][i],rings[-1][(i+1)%16],current[(i+1)%16],current[i]))
        rings.append(current)
    foot_h=p.foot_height_cm; fw=p.calf_thickness_cm*.88; z=foot_h*.5; heel=(ankle[0],-p.foot_length_cm*.18,z); mid=(ankle[0],p.foot_length_cm*.22,z); ball=(ankle[0],p.foot_length_cm*.56,z); toe=(ankle[0],p.foot_length_cm*.82,z)
    centers,widths,depths=_supported_joint_chain((ankle,heel,mid,ball,toe),(p.calf_thickness_cm*.6,fw*.82,fw,fw*1.06,fw*.74),(p.calf_thickness_cm*.58,foot_h*.92,foot_h,foot_h*.82,foot_h*.56)); previous=rings[-1]
    for idx,(center,width,depth) in enumerate(zip(centers[1:],widths[1:],depths[1:])):
        current=[]
        for i in range(8):
            angle=2*pi*i/8; vz=max(0.0,center[2]+depth*.5*sin(angle)); current.append(len(vertices)); vertices.append((center[0]+width*.5*cos(angle),center[1],vz))
        current=tuple(current)
        if idx==0: _append_16_to_8_transition(faces,previous,current)
        else:
            for i in range(8): faces.append((previous[i],previous[(i+1)%8],current[(i+1)%8],current[i]))
        previous=current
    faces.append(tuple(previous))

def _orient_faces_consistently(faces):
    edge_faces=defaultdict(list)
    for fi,face in enumerate(faces):
        for i,a in enumerate(face):
            b=face[(i+1)%len(face)]; edge_faces[tuple(sorted((a,b)))].append((fi,a,b))
    flip=[None]*len(faces)
    for seed in range(len(faces)):
        if flip[seed] is not None: continue
        flip[seed]=False; queue=deque([seed])
        while queue:
            fi=queue.popleft(); face=faces[fi]
            for i,a in enumerate(face):
                b=face[(i+1)%len(face)]
                for other,oa,ob in edge_faces[tuple(sorted((a,b)))]:
                    if other==fi: continue
                    same=(a==oa and b==ob); required=flip[fi]^same
                    if flip[other] is None: flip[other]=required; queue.append(other)
                    elif flip[other]!=required: raise ValueError("anatomical Human surface cannot be oriented consistently")
    return tuple(tuple(reversed(face)) if flip[i] else tuple(face) for i,face in enumerate(faces))

def generate_anatomical_human_mesh(proportions: HumanoidProportions)->ObjectMesh:
    if not isinstance(proportions,HumanoidProportions): raise TypeError("proportions must be HumanoidProportions")
    p=proportions; pts=generate_landmarks(p); vertices,body_faces,fmap=_build_body(p,pts["hip_center"][2],pts["shoulder_center"][2],pts["chin"][2],pts["crown"][2]); vertices=_shape_head_surface(vertices,p,pts["chin"][2],pts["crown"][2]); openings={}; removed=set()
    for level,region in ((_HIP_OPENING_LEVEL,"hip"),(_SHOULDER_OPENING_LEVEL,"shoulder")):
        for side in ("left","right"):
            idx,face=_opening_face(body_faces,fmap,level,side); openings[(region,side)]=face; removed.add(idx)
    faces=[f for i,f in enumerate(body_faces) if i not in removed]
    for side in ("left","right"):
        shoulder=pts["shoulder."+side]; elbow=pts["elbow."+side]; wrist=pts["wrist."+side]; fingertips=pts["fingertips."+side]; shoulder_exit=_lerp_point(shoulder,elbow,.12); palm=_lerp_point(wrist,fingertips,.42); knuckles=_lerp_point(wrist,fingertips,.72); hw=p.forearm_thickness_cm*.92; hd=p.forearm_thickness_cm*.40
        ac,aw,ad=_supported_joint_chain((shoulder,shoulder_exit,elbow,wrist,palm,knuckles,fingertips),(p.upper_arm_thickness_cm*1.05,p.upper_arm_thickness_cm,p.upper_arm_thickness_cm*.82,p.forearm_thickness_cm*.72,hw,hw*.94,hw*.48),(p.upper_arm_thickness_cm*1.05,p.upper_arm_thickness_cm,p.upper_arm_thickness_cm*.82,p.forearm_thickness_cm*.72,hd,hd*.88,hd*.54)); _append_branch(vertices,faces,openings[("shoulder",side)],ac,aw,ad)
        _append_anatomical_leg(vertices,faces,openings[("hip",side)],pts["hip."+side],pts["knee."+side],pts["ankle."+side],p,side)
    vertices=tuple(vertices); faces=_orient_faces_consistently(faces); return ObjectMesh((MeshPart("human",vertices,faces,_generate_face_atlas_uvs(vertices,faces)),))
