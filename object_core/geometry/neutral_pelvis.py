# SPDX-License-Identifier: GPL-3.0-or-later
"""Procedural construct -> sculpt -> finish pelvis experiment.

The recipe first builds an editable cage, then applies generic proportional
vertex sculpting and relaxation before a generic subdivision finish. Object
meaning remains in the recipe; the modeling operations are reusable.
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

def _loop(cx,z,width,depth,sides=16,rear=0,side_drop=0):
    out=[]
    for i in range(sides):
        a=2*pi*i/sides; c=cos(a); s=sin(a)
        out.append((cx+width*.5*c,depth*.5*s+rear*max(0,-s)**2,z-side_drop*abs(c)**1.7))
    return tuple(out)

def _append(v,pts): start=len(v); v.extend(pts); return tuple(range(start,start+len(pts)))
def _bridge(f,a,b):
    for i in range(len(a)): j=(i+1)%len(a); f.append((a[i],a[j],b[j],b[i]))
def _extrude(v,f,boundary,pts): result=_append(v,pts); _bridge(f,boundary,result); return result


def _sculpt(vertices, indices, center, radius, delta):
    """Generic proportional-edit push/pull with smooth radial falloff."""
    cx,cy,cz=center
    for i in indices:
        x,y,z=vertices[i]; dist=((x-cx)**2+(y-cy)**2+(z-cz)**2)**.5
        if dist>=radius: continue
        t=1-dist/radius; weight=t*t*(3-2*t)
        vertices[i]=(x+delta[0]*weight,y+delta[1]*weight,z+delta[2]*weight)


def _relax(vertices, faces, indices, strength=.18, iterations=2):
    """Generic Laplacian relax used on selected cage vertices."""
    selected=set(indices); neighbors={i:set() for i in selected}
    for face in faces:
        for a,b in zip(face,face[1:]+face[:1]):
            if a in selected: neighbors[a].add(b)
            if b in selected: neighbors[b].add(a)
    for _ in range(iterations):
        updates={}
        for i,ns in neighbors.items():
            if not ns: continue
            avg=tuple(sum(vertices[j][k] for j in ns)/len(ns) for k in range(3))
            updates[i]=tuple(vertices[i][k]+(avg[k]-vertices[i][k])*strength for k in range(3))
        for i,p in updates.items(): vertices[i]=p


def _subdivide(vertices, faces):
    """One generic face-center/edge-midpoint subdivision pass."""
    source=list(vertices); result=list(vertices); cache={}; out=[]
    def midpoint(a,b):
        key=tuple(sorted((a,b)))
        if key not in cache:
            pa,pb=source[a],source[b]; cache[key]=len(result)
            result.append(tuple((pa[k]+pb[k])*.5 for k in range(3)))
        return cache[key]
    for face in faces:
        center=len(result); result.append(tuple(sum(source[i][k] for i in face)/len(face) for k in range(3)))
        mids=[midpoint(face[i],face[(i+1)%len(face)]) for i in range(len(face))]
        for i,v in enumerate(face): out.append((v,mids[i],center,mids[i-1]))
    return result,out


def generate_neutral_pelvis(shape=None):
    p=shape or NeutralPelvisShape(); w,d,h=p.width,p.depth,p.height
    v=[]; f=[]; n=16

    # CONSTRUCT: deliberately simple cage.
    top=_append(v,_loop(0,h*.50,p.waist_width*.94,p.waist_depth*.94,n,side_drop=h*.018))
    upper=_append(v,_loop(0,h*.30,w*.91,d*.91,n,rear=-d*.025*p.glute_projection,side_drop=h*.045))
    widest=_append(v,_loop(0,h*.04,w*1.00*p.hip_fullness,d*.98,n,rear=-d*.080*p.glute_projection,side_drop=h*.075))
    lower=_append(v,_loop(0,-h*.17,w*.88,d*.84,n,rear=-d*.060*p.glute_projection,side_drop=h*.070))
    _bridge(f,top,upper); _bridge(f,upper,widest); _bridge(f,widest,lower)

    gap=p.thigh_spacing*.5; cut_z=-h*.17; front_y=d*.34; rear_y=-d*(.38+.025*p.glute_projection)
    lf=_append(v,((-gap,front_y,cut_z+h*.09),))[0]; lr=_append(v,((-gap,rear_y,cut_z+h*.055),))[0]
    rf=_append(v,(( gap,front_y,cut_z+h*.09),))[0]; rr=_append(v,(( gap,rear_y,cut_z+h*.055),))[0]
    left_open=(lower[8],lower[7],lower[6],lower[5],lower[4],lf,lr,lower[12])
    right_open=(lower[0],lower[15],lower[14],lower[13],lower[12],rr,rf,lower[4])
    f.extend([(lower[8],lower[9],lower[10],lower[11],lower[12],lr),
              (lower[8],lf,lower[4],lower[5],lower[6],lower[7]),
              (lower[12],lower[13],lower[14],lower[15],lower[0],rr),
              (lower[4],rf,lower[0],lower[1],lower[2],lower[3]),(lf,rf,rr,lr)])

    center=gap+p.thigh_opening_width*.5
    def target(sign,z,width,depth):
        return tuple((sign*center+width*.5*cos(pi*i/4),depth*.5*sin(pi*i/4),z) for i in range(8))
    left_root=_extrude(v,f,left_open,target(-1,-h*.27,p.thigh_opening_width*1.16,p.thigh_opening_depth*1.18))
    right_root=_extrude(v,f,right_open,target(1,-h*.27,p.thigh_opening_width*1.16,p.thigh_opening_depth*1.18))
    out_z=-h*.55
    left_out=_extrude(v,f,left_root,target(-1,out_z,p.thigh_opening_width,p.thigh_opening_depth))
    right_out=_extrude(v,f,right_root,target(1,out_z,p.thigh_opening_width,p.thigh_opening_depth))

    # SCULPT: operate on the cage after construction, as an artist would.
    cage=tuple(range(len(v)))
    # Round the lateral upper mass and pull the lower sides inward/upward.
    _sculpt(v,cage,(-w*.43,0,h*.08),w*.34,(-w*.045,0,h*.025))
    _sculpt(v,cage,( w*.43,0,h*.08),w*.34,( w*.045,0,h*.025))
    # Build front volume and a distinct, stronger rear volume.
    _sculpt(v,cage,(0,d*.42,h*.03),d*.55,(0,d*.055,-h*.005))
    _sculpt(v,cage,(0,-d*.43,-h*.01),d*.62,(0,-d*.115*p.glute_projection,-h*.015))
    # Lift and soften the center root while pulling each outlet slightly outward.
    _sculpt(v,cage,(0,0,-h*.18),w*.27,(0,0,h*.075))
    _sculpt(v,cage,(-center,0,-h*.31),w*.22,(-w*.018,0,h*.015))
    _sculpt(v,cage,( center,0,-h*.31),w*.22,( w*.018,0,h*.015))
    # Relax only interior construction rings; preserve attachment openings.
    _relax(v,f,upper+widest+lower+left_root+right_root,strength=.12,iterations=2)

    # FINISH: one subdivision pass. It increases surface continuity without
    # being asked to invent the underlying silhouette.
    v,f=_subdivide(v,f)

    # Attachment metadata remains stable and independent from finished topology.
    def public(cx,z,width,depth): return _append(v,_loop(cx,z,width,depth,16))
    torso=public(0,h*.50,p.waist_width,p.waist_depth)
    left=public(-center,out_z,p.thigh_opening_width,p.thigh_opening_depth)
    right=public(center,out_z,p.thigh_opening_width,p.thigh_opening_depth)
    return tuple(v),tuple(tuple(reversed(face)) for face in f),{"torso":torso,"left_thigh":left,"right_thigh":right}
