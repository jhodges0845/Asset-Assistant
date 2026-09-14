# SPDX-License-Identifier: GPL-3.0-or-later
"""Anatomy-oriented connected Human topology construction."""

from math import cos, pi, sin

from ..models.mesh import MeshPart, ObjectMesh
from ..models.proportions import HumanoidProportions
from ..proportions.landmarks import generate_landmarks
from .deformable import (
    _append_branch,
    _generate_face_atlas_uvs,
    _human_body_sections,
    _lerp_point,
    _shape_head_surface,
    _supported_joint_chain,
)

_TORSO_RING_SIDES = 16
_LEGACY_RING_SIDES = 8
_LEG_RING_SIDES = 16
_HIP_OPENING_LEVEL = 0
_SHOULDER_OPENING_LEVEL = 5
_TORSO_LAST_LEVEL = 6


def _ellipse_ring(z, width, depth, sides):
    return tuple((width * 0.5 * cos(2.0*pi*i/sides), depth * 0.5 * sin(2.0*pi*i/sides), z) for i in range(sides))


def _append_equal_ring_band(vertices, faces, lower, upper, face_map, level):
    sides = len(lower)
    if sides != len(upper):
        raise ValueError("equal ring band requires matching ring sizes")
    for segment in range(sides):
        nxt = (segment + 1) % sides
        face_map[(level, segment)] = len(faces)
        faces.append((lower[segment], lower[nxt], upper[nxt], upper[segment]))


def _append_16_to_8_transition(faces, lower, upper):
    if len(lower) != _TORSO_RING_SIDES or len(upper) != _LEGACY_RING_SIDES:
        raise ValueError("transition expects a 16-point lower and 8-point upper ring")
    for index in range(_LEGACY_RING_SIDES):
        a, b, c = lower[2*index], lower[2*index+1], lower[(2*index+2)%16]
        u, v = upper[index], upper[(index+1)%8]
        faces.append((a,b,u)); faces.append((b,c,v,u))


def _build_body(proportions, hip_z, shoulder_z, chin_z, crown_z):
    sections = _human_body_sections(proportions, hip_z, shoulder_z, chin_z, crown_z)
    rings=[]; vertices=[]
    for level,(z,width,depth) in enumerate(sections):
        sides = 16 if level <= _TORSO_LAST_LEVEL else 8
        ring=_ellipse_ring(z,width,depth,sides); start=len(vertices)
        vertices.extend(ring); rings.append(tuple(range(start,start+sides)))
    faces=[tuple(reversed(rings[0]))]; face_map={}
    for level in range(len(rings)-1):
        lower,upper=rings[level],rings[level+1]
        if len(lower)==len(upper): _append_equal_ring_band(vertices,faces,lower,upper,face_map,level)
        else: _append_16_to_8_transition(faces,lower,upper)
    faces.append(tuple(rings[-1])); return vertices,faces,face_map


def _opening_face(faces, face_map, level, side):
    segment = 0 if side == "left" else _TORSO_RING_SIDES//2-1
    return face_map[(level,segment)], faces[face_map[(level,segment)]]


def _append_anatomical_leg(vertices, faces, opening, hip, knee, ankle, p):
    """Attach a 16-sided leg whose longitudinal loops describe major anatomy."""
    sign = 1.0 if hip[0] >= 0.0 else -1.0
    foot_h = p.foot_height_cm
    # Extra construction levels prevent the old long hip-to-knee and knee-to-ankle faces.
    sections = (
        (_lerp_point(hip,knee,0.08), p.thigh_thickness_cm*1.08, p.thigh_thickness_cm*1.02),
        (_lerp_point(hip,knee,0.25), p.thigh_thickness_cm*1.04, p.thigh_thickness_cm*1.00),
        (_lerp_point(hip,knee,0.52), p.thigh_thickness_cm*0.94, p.thigh_thickness_cm*0.92),
        (_lerp_point(hip,knee,0.82), p.calf_thickness_cm*1.04, p.calf_thickness_cm*0.96),
        (knee, p.calf_thickness_cm*0.92, p.calf_thickness_cm*0.88),
        (_lerp_point(knee,ankle,0.24), p.calf_thickness_cm*1.02, p.calf_thickness_cm*0.98),
        (_lerp_point(knee,ankle,0.48), p.calf_thickness_cm*1.12, p.calf_thickness_cm*1.04),
        (_lerp_point(knee,ankle,0.72), p.calf_thickness_cm*0.86, p.calf_thickness_cm*0.82),
        (ankle, p.calf_thickness_cm*0.60, p.calf_thickness_cm*0.58),
    )
    rings=[]
    for center,width,depth in sections:
        start=len(vertices); z=center[2]
        ring=[]
        for i in range(_LEG_RING_SIDES):
            angle=2*pi*i/_LEG_RING_SIDES
            # Slight lateral thigh/calf bias makes the neutral contour anatomical without semantic identity.
            x=center[0] + width*0.5*cos(angle) + sign*width*0.025*sin(angle)**2
            y=center[1] + depth*0.5*sin(angle)
            ring.append(len(vertices)); vertices.append((x,y,z))
        rings.append(tuple(ring))
    # Opening is a torso quad. Fan it into the first 16-ring without splitting torso boundary edges.
    for edge in range(4):
        a=opening[edge]; b=opening[(edge+1)%4]
        base=edge*4
        faces.append((a,b,rings[0][(base+4)%16],rings[0][base]))
        for j in range(3):
            faces.append((a,rings[0][base+j],rings[0][base+j+1]))
    for lower,upper in zip(rings,rings[1:]):
        for i in range(16): faces.append((lower[i],lower[(i+1)%16],upper[(i+1)%16],upper[i]))
    # Keep existing foot construction compatible by bridging the 16-ring ankle to an 8-sided foot chain.
    foot_center_z=foot_h*0.5
    heel=(ankle[0],-p.foot_length_cm*0.18,foot_center_z)
    mid=(ankle[0],p.foot_length_cm*0.22,foot_center_z)
    ball=(ankle[0],p.foot_length_cm*0.56,foot_center_z)
    toe=(ankle[0],p.foot_length_cm*0.82,foot_center_z)
    fw=p.calf_thickness_cm*0.88
    centers,widths,depths=_supported_joint_chain((ankle,heel,mid,ball,toe),(p.calf_thickness_cm*.6,fw*.82,fw,fw*1.06,fw*.74),(p.calf_thickness_cm*.58,foot_h*.92,foot_h,foot_h*.82,foot_h*.56))
    # Create first legacy foot ring, bridge 16 -> 8, then let branch helper close the rest using a synthetic quad opening.
    first_center=centers[1]; tangent=(first_center[0]-ankle[0],first_center[1]-ankle[1],first_center[2]-ankle[2])
    # Use an explicit 8-point horizontal ring; feet are migrated separately later.
    start=len(vertices); first=[]
    for i in range(8):
        angle=2*pi*i/8; first.append(len(vertices)); vertices.append((first_center[0]+widths[1]*.5*cos(angle),first_center[1]+depths[1]*.5*sin(angle),first_center[2]))
    first=tuple(first); _append_16_to_8_transition(faces,rings[-1],first)
    # Continue foot as equal 8-sided bands and cap at toe.
    previous=first
    for center,width,depth in zip(centers[2:],widths[2:],depths[2:]):
        start=len(vertices); current=[]
        for i in range(8):
            angle=2*pi*i/8; current.append(len(vertices)); vertices.append((center[0]+width*.5*cos(angle),center[1]+depth*.5*sin(angle),center[2]))
        current=tuple(current)
        for i in range(8): faces.append((previous[i],previous[(i+1)%8],current[(i+1)%8],current[i]))
        previous=current
    faces.append(tuple(previous))


def generate_anatomical_human_mesh(proportions: HumanoidProportions) -> ObjectMesh:
    if not isinstance(proportions, HumanoidProportions): raise TypeError("proportions must be HumanoidProportions")
    p=proportions; points=generate_landmarks(p)
    hip_z=points["hip_center"][2]; shoulder_z=points["shoulder_center"][2]; chin_z=points["chin"][2]; crown_z=points["crown"][2]
    vertices,body_faces,face_map=_build_body(p,hip_z,shoulder_z,chin_z,crown_z); vertices=_shape_head_surface(vertices,p,chin_z,crown_z)
    openings={}; removed=set()
    for level,region in ((_HIP_OPENING_LEVEL,"hip"),(_SHOULDER_OPENING_LEVEL,"shoulder")):
        for side in ("left","right"):
            idx,face=_opening_face(body_faces,face_map,level,side); openings[(region,side)]=face; removed.add(idx)
    faces=[face for idx,face in enumerate(body_faces) if idx not in removed]
    for side in ("left","right"):
        shoulder=points["shoulder."+side]; elbow=points["elbow."+side]; wrist=points["wrist."+side]; fingertips=points["fingertips."+side]
        shoulder_exit=_lerp_point(shoulder,elbow,.12); palm=_lerp_point(wrist,fingertips,.42); knuckles=_lerp_point(wrist,fingertips,.72)
        hw=p.forearm_thickness_cm*.92; hd=p.forearm_thickness_cm*.40
        ac,aw,ad=_supported_joint_chain((shoulder,shoulder_exit,elbow,wrist,palm,knuckles,fingertips),(p.upper_arm_thickness_cm*1.05,p.upper_arm_thickness_cm,p.upper_arm_thickness_cm*.82,p.forearm_thickness_cm*.72,hw,hw*.94,hw*.48),(p.upper_arm_thickness_cm*1.05,p.upper_arm_thickness_cm,p.upper_arm_thickness_cm*.82,p.forearm_thickness_cm*.72,hd,hd*.88,hd*.54))
        _append_branch(vertices,faces,openings[("shoulder",side)],ac,aw,ad)
        _append_anatomical_leg(vertices,faces,openings[("hip",side)],points["hip."+side],points["knee."+side],points["ankle."+side],p)
    vertices=tuple(vertices); faces=tuple(faces); uvs=_generate_face_atlas_uvs(vertices,faces)
    return ObjectMesh((MeshPart("human",vertices,faces,uvs),))
