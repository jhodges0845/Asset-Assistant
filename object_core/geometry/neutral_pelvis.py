# SPDX-License-Identifier: GPL-3.0-or-later
"""Procedural construct -> sculpt -> smooth pelvis experiment."""
from dataclasses import dataclass
from math import cos, pi, sin, sqrt

@dataclass(frozen=True)
class NeutralPelvisShape:
    width: float=34.; depth: float=24.; height: float=20.; waist_width: float=28.; waist_depth: float=20.
    hip_fullness: float=1.; glute_projection: float=1.; crotch_width: float=7.; crotch_depth: float=8.; crotch_drop: float=1.
    thigh_opening_width: float=12.; thigh_opening_depth: float=13.; thigh_spacing: float=4.

def semantic_controls(): return tuple(NeutralPelvisShape.__dataclass_fields__)
def _add(a,b): return tuple(a[i]+b[i] for i in range(3))
def _mul(a,s): return tuple(x*s for x in a)
def _sub(a,b): return tuple(a[i]-b[i] for i in range(3))
def _cross(a,b): return (a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0])
def _norm(a):
    m=sqrt(sum(x*x for x in a)) or 1.; return tuple(x/m for x in a)
def _loop(cx,z,w,d,n=16,rear=0,drop=0):
    return tuple((cx+w*.5*cos(2*pi*i/n),d*.5*sin(2*pi*i/n)+rear*max(0,-sin(2*pi*i/n))**2,z-drop*abs(cos(2*pi*i/n))**1.7) for i in range(n))
def _append(v,pts): s=len(v); v.extend(pts); return tuple(range(s,s+len(pts)))
def _bridge(f,a,b):
    for i in range(len(a)): j=(i+1)%len(a); f.append((a[i],a[j],b[j],b[i]))
def _extrude(v,f,b,pts): q=_append(v,pts); _bridge(f,b,q); return q

def _neighbors(f,n):
    out=[set() for _ in range(n)]
    for face in f:
        for i,a in enumerate(face):
            b=face[(i+1)%len(face)]; out[a].add(b); out[b].add(a)
    return out

def _normals(v,f):
    ns=[(0.,0.,0.) for _ in v]
    for face in f:
        if len(face)<3: continue
        a,b,c=(v[face[i]] for i in range(3)); n=_cross(_sub(b,a),_sub(c,a))
        for i in face: ns[i]=_add(ns[i],n)
    return [_norm(n) for n in ns]
def _brush(v,indices,center,radius,delta=None,normal_amount=0.,normals=None):
    for i in indices:
        d=sqrt(sum((v[i][k]-center[k])**2 for k in range(3)))
        if d>=radius: continue
        t=1-d/radius; q=t*t*(3-2*t); move=(0.,0.,0.)
        if delta: move=_mul(delta,q)
        if normals and normal_amount: move=_add(move,_mul(normals[i],normal_amount*q))
        v[i]=_add(v[i],move)
def _smooth(v,f,indices,strength=.18,iters=2):
    nb=_neighbors(f,len(v)); selected=set(indices)
    for _ in range(iters):
        old=list(v); updates={}
        for i in selected:
            if not nb[i]: continue
            avg=tuple(sum(old[j][k] for j in nb[i])/len(nb[i]) for k in range(3))
            updates[i]=tuple(old[i][k]+(avg[k]-old[i][k])*strength for k in range(3))
        for i,p in updates.items(): v[i]=p

def _catmull_clark(v,faces):
    """One Catmull-Clark pass with boundary vertices held to avoid open-edge shrinkage."""
    old=list(v); face_pts=[]; edge_faces={}; vertex_faces=[[] for _ in old]; vertex_edges=[set() for _ in old]
    for fi,face in enumerate(faces):
        fp=tuple(sum(old[i][k] for i in face)/len(face) for k in range(3)); face_pts.append(fp)
        for i,a in enumerate(face):
            b=face[(i+1)%len(face)]; e=tuple(sorted((a,b))); edge_faces.setdefault(e,[]).append(fi); vertex_edges[a].add(e); vertex_edges[b].add(e); vertex_faces[a].append(fi)
    new=list(old); boundary=set()
    for e,fs in edge_faces.items():
        if len(fs)==1: boundary.update(e)
    for i,p in enumerate(old):
        if i in boundary or not vertex_faces[i]: continue
        fs=vertex_faces[i]; F=tuple(sum(face_pts[j][k] for j in fs)/len(fs) for k in range(3))
        mids=[tuple((old[e[0]][k]+old[e[1]][k])*.5 for k in range(3)) for e in vertex_edges[i]]
        R=tuple(sum(q[k] for q in mids)/len(mids) for k in range(3)); n=len(fs)
        new[i]=tuple((F[k]+2*R[k]+(n-3)*p[k])/n for k in range(3))
    edge_idx={}
    for e,fs in edge_faces.items():
        if len(fs)==2: p=tuple((old[e[0]][k]+old[e[1]][k]+face_pts[fs[0]][k]+face_pts[fs[1]][k])*.25 for k in range(3))
        else: p=tuple((old[e[0]][k]+old[e[1]][k])*.5 for k in range(3))
        edge_idx[e]=len(new); new.append(p)
    fp_idx=[]
    for p in face_pts: fp_idx.append(len(new)); new.append(p)
    out=[]
    for fi,face in enumerate(faces):
        for j,a in enumerate(face):
            prev=face[j-1]; nxt=face[(j+1)%len(face)]
            out.append((a,edge_idx[tuple(sorted((a,nxt)))],fp_idx[fi],edge_idx[tuple(sorted((prev,a)))]))
    return new,out

def generate_neutral_pelvis(shape=None):
    p=shape or NeutralPelvisShape(); w,d,h=p.width,p.depth,p.height; v=[]; f=[]; n=16
    top=_append(v,_loop(0,h*.50,p.waist_width*.94,p.waist_depth*.94,n,drop=h*.018))
    upper=_append(v,_loop(0,h*.30,w*.91,d*.91,n,rear=-d*.025*p.glute_projection,drop=h*.045))
    widest=_append(v,_loop(0,h*.04,w,d*.98,n,rear=-d*.08*p.glute_projection,drop=h*.075))
    lower=_append(v,_loop(0,-h*.17,w*.88,d*.84,n,rear=-d*.06*p.glute_projection,drop=h*.07))
    _bridge(f,top,upper); _bridge(f,upper,widest); _bridge(f,widest,lower)
    gap=p.thigh_spacing*.5; z=-h*.17; fy=d*.34; ry=-d*(.38+.025*p.glute_projection)
    lf=_append(v,((-gap,fy,z+h*.09),))[0]; lr=_append(v,((-gap,ry,z+h*.055),))[0]; rf=_append(v,((gap,fy,z+h*.09),))[0]; rr=_append(v,((gap,ry,z+h*.055),))[0]
    lo=(lower[8],lower[7],lower[6],lower[5],lower[4],lf,lr,lower[12]); ro=(lower[0],lower[15],lower[14],lower[13],lower[12],rr,rf,lower[4])
    f.extend([(lower[8],lower[9],lower[10],lower[11],lower[12],lr),(lower[8],lf,lower[4],lower[5],lower[6],lower[7]),(lower[12],lower[13],lower[14],lower[15],lower[0],rr),(lower[4],rf,lower[0],lower[1],lower[2],lower[3]),(lf,rf,rr,lr)])
    center=gap+p.thigh_opening_width*.5
    def target(sign,z,wid,dep): return tuple((sign*center+wid*.5*cos(pi*i/4),dep*.5*sin(pi*i/4),z) for i in range(8))
    lroot=_extrude(v,f,lo,target(-1,-h*.27,p.thigh_opening_width*1.16,p.thigh_opening_depth*1.18)); rroot=_extrude(v,f,ro,target(1,-h*.27,p.thigh_opening_width*1.16,p.thigh_opening_depth*1.18))
    outz=-h*.55; lout=_extrude(v,f,lroot,target(-1,outz,p.thigh_opening_width,p.thigh_opening_depth)); rout=_extrude(v,f,rroot,target(1,outz,p.thigh_opening_width,p.thigh_opening_depth))
    cage=tuple(range(len(v))); ns=_normals(v,f)
    _brush(v,cage,(-w*.42,0,h*.06),w*.34,(-w*.035,0,h*.025)); _brush(v,cage,(w*.42,0,h*.06),w*.34,(w*.035,0,h*.025))
    _brush(v,cage,(0,d*.42,h*.02),d*.55,(0,d*.045,0)); _brush(v,cage,(0,-d*.43,0),d*.62,(0,-d*.09*p.glute_projection,-h*.01))
    ns=_normals(v,f); _brush(v,cage,(0,0,-h*.12),w*.34,normal_amount=w*.025,normals=ns)
    _brush(v,cage,(0,0,-h*.19),w*.25,(0,0,h*.06)); _smooth(v,f,upper+widest+lower+lroot+rroot,.14,3)
    v,f=_catmull_clark(v,f)
    def public(cx,z,wid,dep): return _append(v,_loop(cx,z,wid,dep,16))
    torso=public(0,h*.50,p.waist_width,p.waist_depth); left=public(-center,outz,p.thigh_opening_width,p.thigh_opening_depth); right=public(center,outz,p.thigh_opening_width,p.thigh_opening_depth)
    return tuple(v),tuple(tuple(reversed(x)) for x in f),{"torso":torso,"left_thigh":left,"right_thigh":right}
