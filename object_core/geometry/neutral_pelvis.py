# SPDX-License-Identifier: GPL-3.0-or-later
"""Recipe-driven patch-and-stitch pelvis experiment.

Generic curves and shared-vertex strips form the construction layer.  This file
currently also contains the neutral pelvis recipe so its coarse surface can be
iterated visually before recipes are split into their own package.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class NeutralPelvisShape:
    width: float = 34.0
    depth: float = 24.0
    height: float = 20.0
    waist_width: float = 28.0
    waist_depth: float = 20.0
    hip_fullness: float = 1.0
    glute_projection: float = 1.0
    crotch_width: float = 7.0
    crotch_depth: float = 8.0
    crotch_drop: float = 1.0
    thigh_opening_width: float = 12.0
    thigh_opening_depth: float = 13.0
    thigh_spacing: float = 4.0


def semantic_controls(): return tuple(NeutralPelvisShape.__dataclass_fields__)
def _lerp(a,b,t): return tuple(x+(y-x)*t for x,y in zip(a,b))


def _curve(a,b,bulge=(0,0,0),steps=4):
    out=[]
    for i in range(steps+1):
        t=i/steps; q=4*t*(1-t); p=_lerp(a,b,t)
        out.append(tuple(p[j]+bulge[j]*q for j in range(3)))
    return tuple(out)


def _add(vertices,cache,p):
    key=tuple(round(v,7) for v in p)
    if key not in cache: cache[key]=len(vertices); vertices.append(p)
    return cache[key]


def _strip(vertices,faces,cache,a,b,bow=(0,0,0),rows=2):
    if len(a)!=len(b): raise ValueError("region boundaries require equal samples")
    grid=[]
    for r in range(rows+1):
        t=r/rows; q=4*t*(1-t); row=[]
        for pa,pb in zip(a,b):
            p=_lerp(pa,pb,t); p=tuple(p[j]+bow[j]*q for j in range(3))
            row.append(_add(vertices,cache,p))
        grid.append(row)
    for r in range(rows):
        for c in range(len(a)-1):
            faces.append((grid[r][c],grid[r][c+1],grid[r+1][c+1],grid[r+1][c]))


def _cross(xs,y,zs,bulge=0):
    n=len(xs); out=[]
    for i,(x,z) in enumerate(zip(xs,zs)):
        t=i/(n-1); out.append((x,y+bulge*4*t*(1-t),z))
    return tuple(out)


def generate_neutral_pelvis(shape=None):
    p=shape or NeutralPelvisShape(); w,d,h=p.width,p.depth,p.height
    vertices=[]; faces=[]; cache={}
    gap=p.thigh_spacing*.5; outer=gap+p.thigh_opening_width

    # Five recipe levels.  Width now blooms gradually below the waist and then
    # turns inward before the split instead of holding a rectangular maximum.
    z=(h*.50,h*.30,h*.07,-h*.20,-h*.55)
    spans=(p.waist_width*.47,w*.485,w*.515,w*.445)
    fy=(p.waist_depth*.46,d*.49,d*.505,d*.405)
    ry=(-p.waist_depth*.46,-d*(.50+.020*p.glute_projection),
        -d*(.515+.060*p.glute_projection),-d*(.455+.050*p.glute_projection))

    def xs(span): return (-span,-span*.78,-span*.48,-span*.20,0,span*.20,span*.48,span*.78,span)
    front=[]; rear=[]
    for k in range(3):
        xx=xs(spans[k])
        # Outer controls sit lower than the center, producing a rounded crest
        # and moving maximum width away from the very top edge.
        zz=tuple(z[k]-h*(.030*(abs(x)/spans[k])**1.7) for x in xx)
        front.append(_cross(xx,fy[k],zz,d*(.008+.004*k)))
        rear.append(_cross(xx,ry[k],zz,-d*(.012+.010*k)*p.glute_projection))

    # Split roots are narrower and higher on their inner edges.  This makes the
    # outlet surfaces begin inside the body rather than below a horizontal ledge.
    lx=(-outer,-outer*.78,-outer*.50,-gap)
    rx=(gap,outer*.50,outer*.78,outer)
    root_z_outer=z[3]-h*.010; root_z_inner=z[3]+h*.075
    rz_l=(root_z_outer,z[3]-h*.005,z[3]+h*.030,root_z_inner)
    rz_r=tuple(reversed(rz_l))
    rfl=_cross(lx,fy[3],rz_l,d*.006); rfr=_cross(rx,fy[3],rz_r,d*.006)
    rrl=_cross(lx,ry[3],tuple(v-h*.018 for v in rz_l),-d*.015)
    rrr=_cross(rx,ry[3],tuple(v-h*.018 for v in rz_r),-d*.015)
    ofl=_cross(lx,p.thigh_opening_depth*.50,(z[4],)*4)
    ofr=_cross(rx,p.thigh_opening_depth*.50,(z[4],)*4)
    orl=_cross(lx,-p.thigh_opening_depth*.50,(z[4],)*4)
    orr=_cross(rx,-p.thigh_opening_depth*.50,(z[4],)*4)

    # Broad upper regions.
    _strip(vertices,faces,cache,front[0],front[1],(0,d*.012,-h*.010),2)
    _strip(vertices,faces,cache,front[1],front[2],(0,d*.022,-h*.014),3)
    _strip(vertices,faces,cache,rear[0],rear[1],(0,-d*.020,-h*.008),2)
    _strip(vertices,faces,cache,rear[1],rear[2],(0,-d*.050*p.glute_projection,-h*.012),3)

    # Lower left/right regions use four samples each, leaving the three center
    # samples for independent arch regions.
    fl=front[2][:4]; fr=front[2][5:]; rl=rear[2][:4]; rr=rear[2][5:]
    _strip(vertices,faces,cache,fl,rfl,(-w*.020,d*.006,-h*.010),3)
    _strip(vertices,faces,cache,fr,rfr,(w*.020,d*.006,-h*.010),3)
    _strip(vertices,faces,cache,rl,rrl,(-w*.022,-d*.035,-h*.006),3)
    _strip(vertices,faces,cache,rr,rrr,(w*.022,-d*.035,-h*.006),3)

    # Front/rear center regions deliberately curve upward toward the split.
    aft=front[2][3:6]; art=rear[2][3:6]
    afb=(rfl[-1],(0,fy[3]*.92,root_z_inner+h*.035),rfr[0])
    arb=(rrl[-1],(0,ry[3]*.94,root_z_inner+h*.020),rrr[0])
    _strip(vertices,faces,cache,aft,afb,(0,d*.018,h*.020),3)
    _strip(vertices,faces,cache,art,arb,(0,-d*.025,h*.015),3)

    # Side regions are intentionally rounded in depth and width.  Three bands
    # let the side silhouette roll continuously from waist to outlet root.
    for fa,fb,ra,rb,bx in ((front[0],front[1],rear[0],rear[1],w*.020),
                            (front[1],front[2],rear[1],rear[2],w*.026)):
        _strip(vertices,faces,cache,(fa[0],fb[0]),(ra[0],rb[0]),(-bx,0,-h*.006),5)
        _strip(vertices,faces,cache,(fa[-1],fb[-1]),(ra[-1],rb[-1]),(bx,0,-h*.006),5)
    _strip(vertices,faces,cache,(fl[0],rfl[0]),(rl[0],rrl[0]),(-w*.018,0,0),4)
    _strip(vertices,faces,cache,(fr[-1],rfr[-1]),(rr[-1],rrr[-1]),(w*.018,0,0),4)

    # Each outlet remains four explicit surface regions.  The inner wall bows
    # outward slightly so the gap narrows near the root and opens toward z4.
    for sign,rf,rr0,of,or0 in ((-1,rfl,rrl,ofl,orl),(1,rfr,rrr,ofr,orr)):
        _strip(vertices,faces,cache,rf,of,(sign*w*.008,d*.008,h*.015),3)
        _strip(vertices,faces,cache,rr0,or0,(sign*w*.008,-d*.020,h*.012),3)
        oi=0 if sign<0 else -1; ii=-1 if sign<0 else 0
        _strip(vertices,faces,cache,(rf[oi],of[oi]),(rr0[oi],or0[oi]),(sign*w*.012,0,0),5)
        _strip(vertices,faces,cache,(rf[ii],of[ii]),(rr0[ii],or0[ii]),(-sign*p.crotch_width*.07,0,h*.008),5)

    # Saddle is shallow and high at its front/rear ends; the visible split is
    # therefore formed by the two outlet walls rather than a deep rectangular cut.
    sl=_curve(rfl[-1],rrl[-1],(0,0,h*.035),5)
    sr=_curve(rfr[0],rrr[0],(0,0,h*.035),5)
    _strip(vertices,faces,cache,sl,sr,(0,0,-h*.018*p.crotch_drop),5)

    torso=tuple(_add(vertices,cache,q) for q in _curve((-p.waist_width*.5,fy[0],z[0]),(p.waist_width*.5,fy[0],z[0]),steps=15))
    left=tuple(_add(vertices,cache,q) for q in _curve((-outer,p.thigh_opening_depth*.5,z[4]),(-gap,p.thigh_opening_depth*.5,z[4]),steps=15))
    right=tuple(_add(vertices,cache,q) for q in _curve((gap,p.thigh_opening_depth*.5,z[4]),(outer,p.thigh_opening_depth*.5,z[4]),steps=15))
    return tuple(vertices),tuple(tuple(reversed(f)) for f in faces),{"torso":torso,"left_thigh":left,"right_thigh":right}
