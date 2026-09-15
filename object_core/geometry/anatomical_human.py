# SPDX-License-Identifier: GPL-3.0-or-later
"""Anatomy-oriented connected Human topology construction."""

from collections import defaultdict, deque
from math import cos, pi, sin
from ..models.mesh import MeshPart, ObjectMesh
from ..models.proportions import HumanoidProportions
from ..proportions.landmarks import generate_landmarks
from .anatomical_pelvis import pelvis_ring, pelvic_transition_ring, pelvis_surface_ring, thigh_opening_ring, upper_thigh_ring
from .deformable import _append_branch, _generate_face_atlas_uvs, _human_body_sections, _lerp_point, _shape_head_surface, _supported_joint_chain

_TORSO_RING_SIDES=16; _LEGACY_RING_SIDES=8; _LEG_RING_SIDES=16
_HIP_OPENING_LEVEL=0; _SHOULDER_OPENING_LEVEL=5; _TORSO_LAST_LEVEL=6

def _ellipse_ring(z,width,depth,sides):
    return tuple((width*.5*cos(2*pi*i/sides),depth*.5*sin(2*pi*i/sides),z) for i in range(sides))

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
        if level==_HIP_OPENING_LEVEL: ring=pelvis_ring(z,w,d,p.thigh_thickness_cm)
        elif level==_HIP_OPENING_LEVEL+1: ring=pelvic_transition_ring(z,w,d,p.thigh_thickness_cm)
        else: ring=_ellipse_ring(z,w,d,sides)
        start=len(vertices); vertices.extend(ring); rings.append(tuple(range(start,start+sides)))
    faces=[tuple(reversed(rings[0]))]; fmap={}
    for level in range(len(rings)-1):
        if len(rings[level])==len(rings[level+1]): _append_equal_ring_band(vertices,faces,rings[level],rings[level+1],fmap,level)
        else: _append_16_to_8_transition(faces,rings[level],rings[level+1])
    faces.append(tuple(rings[-1])); return vertices,faces,fmap,rings

def _opening_face(faces,fmap,level,side):
    segment=0 if side=="left" else 7; return fmap[(level,segment)],faces[fmap[(level,segment)]]

def _append_ring(vertices, points):
    ring=[]
    for point in points: ring.append(len(vertices)); vertices.append(point)
    return tuple(ring)

def _append_ring_band(faces, upper, lower):
    for i in range(16): faces.append((upper[i],upper[(i+1)%16],lower[(i+1)%16],lower[i]))

def _append_dual_leg_bridge(vertices,faces,pelvis_boundary,left_points,right_points):
    """Tile a pair-of-pants patch between one pelvis loop and two thigh loops."""
    left=_append_ring(vertices,left_points); right=_append_ring(vertices,right_points)
    left_p=(0,1,2,3,4,5,6,7); right_p=(8,9,10,11,12,13,14,15)
    left_t=(0,1,2,3,4,5,6,7); right_t=(8,9,10,11,12,13,14,15)
    for seq_p,seq_t,ring in ((left_p,left_t,left),(right_p,right_t,right)):
        for j in range(len(seq_p)-1): faces.append((pelvis_boundary[seq_p[j]],pelvis_boundary[seq_p[j+1]],ring[seq_t[j+1]],ring[seq_t[j]]))
    faces.append((pelvis_boundary[15],pelvis_boundary[0],left[0],left[15]))
    faces.append((pelvis_boundary[7],pelvis_boundary[8],right[8],right[7]))
    for j in range(8):
        li=7+j; r0=(7-j)%16; r1=(6-j)%16
        faces.append((left[li],left[(li+1)%16],right[r1],right[r0]))
    faces.append((pelvis_boundary[7],left[7],right[7]))
    faces.append((pelvis_boundary[15],right[15],left[15]))
    return left,right

def _append_anatomical_leg_from_root(vertices,faces,root,sections,p):
    rings=[root]
    for center,width,depth,blend,side in sections:
        current=_append_ring(vertices,upper_thigh_ring(center,width,depth,side,blend)); _append_ring_band(faces,rings[-1],current); rings.append(current)
    ankle=sections[-1][0]; foot_h=p.foot_height_cm; fw=p.calf_thickness_cm*.88; z=foot_h*.5; heel=(ankle[0],-p.foot_length_cm*.18,z); mid=(ankle[0],p.foot_length_cm*.22,z); ball=(ankle[0],p.foot_length_cm*.56,z); toe=(ankle[0],p.foot_length_cm*.82,z)
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

def _leg_sections(hip,knee,ankle,p,side):
    data=((.18,p.thigh_thickness_cm*1.11,p.thigh_thickness_cm*1.07,.72),(.30,p.thigh_thickness_cm*1.04,p.thigh_thickness_cm,.40),(.52,p.thigh_thickness_cm*.94,p.thigh_thickness_cm*.92,0.0),(.82,p.calf_thickness_cm*1.04,p.calf_thickness_cm*.96,0.0))
    result=[(_lerp_point(hip,knee,f),w,d,b,side) for f,w,d,b in data]
    result.extend(((knee,p.calf_thickness_cm*.92,p.calf_thickness_cm*.88,0.0,side),(_lerp_point(knee,ankle,.18),p.calf_thickness_cm*.98,p.calf_thickness_cm*.94,0.0,side),(_lerp_point(knee,ankle,.38),p.calf_thickness_cm*1.08,p.calf_thickness_cm,0.0,side),(_lerp_point(knee,ankle,.55),p.calf_thickness_cm*1.12,p.calf_thickness_cm*1.04,0.0,side),(_lerp_point(knee,ankle,.76),p.calf_thickness_cm*.84,p.calf_thickness_cm*.80,0.0,side),(ankle,p.calf_thickness_cm*.60,p.calf_thickness_cm*.58,0.0,side)))
    return tuple(result)

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
    p=proportions; pts=generate_landmarks(p); vertices,body_faces,fmap,rings=_build_body(p,pts["hip_center"][2],pts["shoulder_center"][2],pts["chin"][2],pts["crown"][2]); vertices=_shape_head_surface(vertices,p,pts["chin"][2],pts["crown"][2]); openings={}; removed={0}
    for side in ("left","right"):
        idx,face=_opening_face(body_faces,fmap,_SHOULDER_OPENING_LEVEL,side); openings[side]=face; removed.add(idx)
    faces=[f for i,f in enumerate(body_faces) if i not in removed]
    for side in ("left","right"):
        shoulder=pts["shoulder."+side]; elbow=pts["elbow."+side]; wrist=pts["wrist."+side]; fingertips=pts["fingertips."+side]; shoulder_exit=_lerp_point(shoulder,elbow,.12); palm=_lerp_point(wrist,fingertips,.42); knuckles=_lerp_point(wrist,fingertips,.72); hw=p.forearm_thickness_cm*.92; hd=p.forearm_thickness_cm*.40
        ac,aw,ad=_supported_joint_chain((shoulder,shoulder_exit,elbow,wrist,palm,knuckles,fingertips),(p.upper_arm_thickness_cm*1.05,p.upper_arm_thickness_cm,p.upper_arm_thickness_cm*.82,p.forearm_thickness_cm*.72,hw,hw*.94,hw*.48),(p.upper_arm_thickness_cm*1.05,p.upper_arm_thickness_cm,p.upper_arm_thickness_cm*.82,p.forearm_thickness_cm*.72,hd,hd*.88,hd*.54)); _append_branch(vertices,faces,openings[side],ac,aw,ad)
    lh=pts["hip.left"]; rh=pts["hip.right"]; lk=pts["knee.left"]; rk=pts["knee.right"]; la=pts["ankle.left"]; ra=pts["ankle.right"]
    hip_z=pts["hip_center"][2]
    base_width=max(abs(v[0]) for v in (vertices[i] for i in rings[0]))*2.0
    base_depth=(max(vertices[i][1] for i in rings[0])-min(vertices[i][1] for i in rings[0]))
    pelvis_mid=_append_ring(vertices,pelvis_surface_ring(hip_z-1.5,base_width*.98,base_depth*1.04,p.thigh_thickness_cm,.38))
    pelvis_low=_append_ring(vertices,pelvis_surface_ring(hip_z-3.8,base_width*.94,base_depth*1.08,p.thigh_thickness_cm,.72))
    _append_ring_band(faces,rings[0],pelvis_mid); _append_ring_band(faces,pelvis_mid,pelvis_low)
    lc=_lerp_point(lh,lk,.10); rc=_lerp_point(rh,rk,.10)
    # The split now terminates on anatomical, non-planar thigh openings. Lateral hip
    # points remain high while medial points descend into the crotch seam; rear
    # points carry glute depth into the upper thigh instead of forming a flat shelf.
    lp=thigh_opening_ring(lc,p.thigh_thickness_cm*1.10,p.thigh_thickness_cm*1.08,"left",.86)
    rp=thigh_opening_ring(rc,p.thigh_thickness_cm*1.10,p.thigh_thickness_cm*1.08,"right",.86)
    left_root,right_root=_append_dual_leg_bridge(vertices,faces,pelvis_low,lp,rp)
    _append_anatomical_leg_from_root(vertices,faces,left_root,_leg_sections(lh,lk,la,p,"left"),p); _append_anatomical_leg_from_root(vertices,faces,right_root,_leg_sections(rh,rk,ra,p,"right"),p)
    vertices=tuple(vertices); faces=_orient_faces_consistently(faces); return ObjectMesh((MeshPart("human",vertices,faces,_generate_face_atlas_uvs(vertices,faces)),))
