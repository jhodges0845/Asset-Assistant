# SPDX-License-Identifier: GPL-3.0-or-later
"""Welded patch -> sculpt -> smooth pelvis experiment."""
from dataclasses import dataclass
from math import sqrt

@dataclass(frozen=True)
class NeutralPelvisShape:
    width: float=34.; depth: float=24.; height: float=20.; waist_width: float=28.; waist_depth: float=20.
    hip_fullness: float=1.; glute_projection: float=1.; crotch_width: float=7.; crotch_depth: float=8.; crotch_drop: float=1.
    thigh_opening_width: float=12.; thigh_opening_depth: float=13.; thigh_spacing: float=4.

def semantic_controls(): return tuple(NeutralPelvisShape.__dataclass_fields__)
def _lerp(a,b,t): return tuple(x+(y-x)*t for x,y in zip(a,b))
def _addv(a,b): return tuple(a[i]+b[i] for i in range(3))
def _mul(a,s): return tuple(x*s for x in a)
def _sub(a,b): return tuple(a[i]-b[i] for i in range(3))
def _cross(a,b): return (a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0])
def _norm(a):
    m=sqrt(sum(x*x for x in a)) or 1.; return tuple(x/m for x in a)
def _curve(a,b,bulge=(0,0,0),steps=4):
    return tuple(_addv(_lerp(a,b,i/steps),_mul(bulge,4*(i/steps)*(1-i/steps))) for i in range(steps+1))
def _add(vertices,cache,p):
    key=tuple(round(x,7) for x in p)
    if key not in cache: cache[key]=len(vertices); vertices.append(p)
    return cache[key]
def _patch(v,f,cache,top,bottom,control=(0,0,0),rows=4):
    if len(top)!=len(bottom): raise ValueError("patch boundaries require equal samples")
    grid=[]; cols=len(top)
    for r in range(rows+1):
        y=r/rows; row=[]
        for c,(a,b) in enumerate(zip(top,bottom)):
            x=c/(cols-1); influence=16*x*(1-x)*y*(1-y)
            row.append(_add(v,cache,_addv(_lerp(a,b,y),_mul(control,influence))))
        grid.append(row)
    for r in range(rows):
        for c in range(cols-1): f.append((grid[r][c],grid[r][c+1],grid[r+1][c+1],grid[r+1][c]))
def _crossline(xs,y,zs,bulge=0):
    n=len(xs); return tuple((x,y+bulge*4*(i/(n-1))*(1-i/(n-1)),z) for i,(x,z) in enumerate(zip(xs,zs)))
def _neighbors(f,n):
    out=[set() for _ in range(n)]
    for face in f:
        for i,a in enumerate(face): b=face[(i+1)%len(face)]; out[a].add(b); out[b].add(a)
    return out
def _normals(v,f):
    ns=[(0.,0.,0.) for _ in v]
    for face in f:
        if len(face)<3: continue
        a,b,c=(v[face[i]] for i in range(3)); n=_cross(_sub(b,a),_sub(c,a))
        for i in face: ns[i]=_addv(ns[i],n)
    return [_norm(x) for x in ns]
def _brush(v,ids,center,radius,delta=(0,0,0),normal_amount=0,normals=None):
    for i in ids:
        d=sqrt(sum((v[i][k]-center[k])**2 for k in range(3)))
        if d>=radius: continue
        t=1-d/radius; q=t*t*(3-2*t); move=_mul(delta,q)
        if normals and normal_amount: move=_addv(move,_mul(normals[i],normal_amount*q))
        v[i]=_addv(v[i],move)
def _smooth(v,f,ids,strength=.12,iters=2):
    nb=_neighbors(f,len(v)); selected=set(ids)
    for _ in range(iters):
        old=list(v); updates={}
        for i in selected:
            if not nb[i]: continue
            avg=tuple(sum(old[j][k] for j in nb[i])/len(nb[i]) for k in range(3))
            updates[i]=tuple(old[i][k]+(avg[k]-old[i][k])*strength for k in range(3))
        for i,p in updates.items(): v[i]=p
def _catmull(v,faces):
    old=list(v); fps=[]; edge_faces={}; vf=[[] for _ in old]; ve=[set() for _ in old]
    for fi,face in enumerate(faces):
        fps.append(tuple(sum(old[i][k] for i in face)/len(face) for k in range(3)))
        for j,a in enumerate(face):
            b=face[(j+1)%len(face)]; e=tuple(sorted((a,b))); edge_faces.setdefault(e,[]).append(fi); ve[a].add(e); ve[b].add(e); vf[a].append(fi)
    new=list(old); boundary=set()
    for e,fs in edge_faces.items():
        if len(fs)==1: boundary.update(e)
    for i,p in enumerate(old):
        if i in boundary or not vf[i]: continue
        fs=vf[i]; F=tuple(sum(fps[j][k] for j in fs)/len(fs) for k in range(3)); mids=[tuple((old[e[0]][k]+old[e[1]][k])*.5 for k in range(3)) for e in ve[i]]; R=tuple(sum(q[k] for q in mids)/len(mids) for k in range(3)); n=len(fs)
        new[i]=tuple((F[k]+2*R[k]+(n-3)*p[k])/n for k in range(3))
    ei={}
    for e,fs in edge_faces.items():
        p=tuple((old[e[0]][k]+old[e[1]][k]+fps[fs[0]][k]+fps[fs[1]][k])*.25 for k in range(3)) if len(fs)==2 else tuple((old[e[0]][k]+old[e[1]][k])*.5 for k in range(3)); ei[e]=len(new); new.append(p)
    fi=[]
    for p in fps: fi.append(len(new)); new.append(p)
    out=[]
    for q,face in enumerate(faces):
        for j,a in enumerate(face): out.append((a,ei[tuple(sorted((a,face[(j+1)%len(face)])))],fi[q],ei[tuple(sorted((face[j-1],a))) ]))
    return new,out

def generate_neutral_pelvis(shape=None):
    p=shape or NeutralPelvisShape(); w,d,h=p.width,p.depth,p.height; v=[]; f=[]; cache={}; gap=p.thigh_spacing*.5; outer=gap+p.thigh_opening_width
    z=(h*.50,h*.30,h*.06,-h*.20,-h*.55); spans=(p.waist_width*.47,w*.485,w*.515); fy=(p.waist_depth*.46,d*.49,d*.505,d*.405); ry=(-p.waist_depth*.46,-d*(.50+.020*p.glute_projection),-d*(.515+.060*p.glute_projection),-d*(.455+.050*p.glute_projection))
    def xs(s): return (-s,-s*.78,-s*.48,-s*.20,0,s*.20,s*.48,s*.78,s)
    front=[]; rear=[]
    for k in range(3):
        xx=xs(spans[k]); zz=tuple(z[k]-h*(.030*(abs(x)/spans[k])**1.7) for x in xx); front.append(_crossline(xx,fy[k],zz,d*(.008+.004*k))); rear.append(_crossline(xx,ry[k],zz,-d*(.012+.010*k)*p.glute_projection))
    lx=(-outer,-outer*.78,-outer*.50,-gap); rx=(gap,outer*.50,outer*.78,outer); inner=z[3]+h*.075; zl=(z[3]-h*.01,z[3],z[3]+h*.03,inner); zr=tuple(reversed(zl))
    rfl=_crossline(lx,fy[3],zl,d*.006); rfr=_crossline(rx,fy[3],zr,d*.006); rrl=_crossline(lx,ry[3],tuple(q-h*.018 for q in zl),-d*.015); rrr=_crossline(rx,ry[3],tuple(q-h*.018 for q in zr),-d*.015)
    ofl=_crossline(lx,p.thigh_opening_depth*.5,(z[4],)*4); ofr=_crossline(rx,p.thigh_opening_depth*.5,(z[4],)*4); orl=_crossline(lx,-p.thigh_opening_depth*.5,(z[4],)*4); orr=_crossline(rx,-p.thigh_opening_depth*.5,(z[4],)*4)
    _patch(v,f,cache,front[0],front[1],(0,d*.03,-h*.01),4); _patch(v,f,cache,front[1],front[2],(0,d*.05,-h*.018),5); _patch(v,f,cache,rear[0],rear[1],(0,-d*.045,-h*.008),4); _patch(v,f,cache,rear[1],rear[2],(0,-d*.095*p.glute_projection,-h*.016),5)
    fl,fr,rl,rr=front[2][:4],front[2][5:],rear[2][:4],rear[2][5:]
    for a,b,c in ((fl,rfl,(-w*.055,d*.025,-h*.025)),(fr,rfr,(w*.055,d*.025,-h*.025)),(rl,rrl,(-w*.06,-d*.07,-h*.018)),(rr,rrr,(w*.06,-d*.07,-h*.018))): _patch(v,f,cache,a,b,c,5)
    aft,art=front[2][3:6],rear[2][3:6]; afb=(rfl[-1],(0,fy[3]*.92,inner+h*.035),rfr[0]); arb=(rrl[-1],(0,ry[3]*.94,inner+h*.020),rrr[0]); _patch(v,f,cache,aft,afb,(0,d*.065,h*.035),5); _patch(v,f,cache,art,arb,(0,-d*.075,h*.025),5)
    for fa,fb,ra,rb,amount in ((front[0],front[1],rear[0],rear[1],.045),(front[1],front[2],rear[1],rear[2],.065)):
        _patch(v,f,cache,(fa[0],fb[0]),(ra[0],rb[0]),(-w*amount,0,-h*.01),6); _patch(v,f,cache,(fa[-1],fb[-1]),(ra[-1],rb[-1]),(w*amount,0,-h*.01),6)
    _patch(v,f,cache,(fl[0],rfl[0]),(rl[0],rrl[0]),(-w*.055,0,-h*.012),6); _patch(v,f,cache,(fr[-1],rfr[-1]),(rr[-1],rrr[-1]),(w*.055,0,-h*.012),6)
    for sign,rf,rb,of,ob in ((-1,rfl,rrl,ofl,orl),(1,rfr,rrr,ofr,orr)):
        _patch(v,f,cache,rf,of,(sign*w*.025,d*.035,h*.025),5); _patch(v,f,cache,rb,ob,(sign*w*.025,-d*.045,h*.02),5); oi=0 if sign<0 else -1; ii=-1 if sign<0 else 0; _patch(v,f,cache,(rf[oi],of[oi]),(rb[oi],ob[oi]),(sign*w*.03,0,0),6); _patch(v,f,cache,(rf[ii],of[ii]),(rb[ii],ob[ii]),(-sign*p.crotch_width*.12,0,h*.025),6)
    sl=_curve(rfl[-1],rrl[-1],(0,0,h*.035),5); sr=_curve(rfr[0],rrr[0],(0,0,h*.035),5); _patch(v,f,cache,sl,sr,(0,0,-h*.045*p.crotch_drop),6)
    # Weld is inherent in the coordinate cache: every coincident patch edge resolves to one vertex id.
    cage=tuple(range(len(v))); ns=_normals(v,f)
    _brush(v,cage,(-w*.42,0,h*.04),w*.34,(-w*.035,0,h*.02)); _brush(v,cage,(w*.42,0,h*.04),w*.34,(w*.035,0,h*.02)); _brush(v,cage,(0,d*.43,h*.02),d*.60,(0,d*.04,0)); _brush(v,cage,(0,-d*.45,0),d*.68,(0,-d*.085*p.glute_projection,-h*.01)); _brush(v,cage,(0,0,-h*.17),w*.28,(0,0,h*.05)); ns=_normals(v,f); _brush(v,cage,(0,0,-h*.05),w*.44,normal_amount=w*.018,normals=ns)
    # Smooth only vertices that are not public attachment edges; attachments are added after finish.
    _smooth(v,f,cage,.10,2); v,f=_catmull(v,f)
    torso=tuple(_add(v,cache,q) for q in _curve((-p.waist_width*.5,fy[0],z[0]),(p.waist_width*.5,fy[0],z[0]),steps=15)); left=tuple(_add(v,cache,q) for q in _curve((-outer,p.thigh_opening_depth*.5,z[4]),(-gap,p.thigh_opening_depth*.5,z[4]),steps=15)); right=tuple(_add(v,cache,q) for q in _curve((gap,p.thigh_opening_depth*.5,z[4]),(outer,p.thigh_opening_depth*.5,z[4]),steps=15))
    return tuple(v),tuple(tuple(reversed(x)) for x in f),{"torso":torso,"left_thigh":left,"right_thigh":right}
