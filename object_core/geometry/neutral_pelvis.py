# SPDX-License-Identifier: GPL-3.0-or-later
"""Recipe-driven patch-and-stitch pelvis experiment.

Generic boundaries and controlled four-sided surface patches form the geometry
layer. Object meaning lives only in the recipe/control locations.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class NeutralPelvisShape:
    width: float=34.0; depth: float=24.0; height: float=20.0
    waist_width: float=28.0; waist_depth: float=20.0
    hip_fullness: float=1.0; glute_projection: float=1.0
    crotch_width: float=7.0; crotch_depth: float=8.0; crotch_drop: float=1.0
    thigh_opening_width: float=12.0; thigh_opening_depth: float=13.0; thigh_spacing: float=4.0


def semantic_controls(): return tuple(NeutralPelvisShape.__dataclass_fields__)
def _lerp(a,b,t): return tuple(x+(y-x)*t for x,y in zip(a,b))
def _vadd(a,b): return tuple(x+y for x,y in zip(a,b))
def _vscale(a,s): return tuple(x*s for x in a)


def _curve(a,b,bulge=(0,0,0),steps=4):
    out=[]
    for i in range(steps+1):
        t=i/steps; q=4*t*(1-t); p=_lerp(a,b,t)
        out.append(_vadd(p,_vscale(bulge,q)))
    return tuple(out)


def _add(vertices,cache,p):
    key=tuple(round(v,7) for v in p)
    if key not in cache: cache[key]=len(vertices); vertices.append(p)
    return cache[key]


def _surface_patch(vertices,faces,cache,top,bottom,control=(0,0,0),rows=4):
    """Generic controlled surface patch between equal sampled boundaries.

    Unlike a ruled strip, displacement varies in both patch directions.  The
    supplied vector reaches full influence at the patch center and zero on all
    four edges, so neighboring patches retain exact shared boundaries.
    """
    if len(top)!=len(bottom): raise ValueError("patch boundaries require equal samples")
    cols=len(top); grid=[]
    for r in range(rows+1):
        v=r/rows; rv=4*v*(1-v); row=[]
        for c,(a,b) in enumerate(zip(top,bottom)):
            u=c/(cols-1); ru=4*u*(1-u)
            p=_lerp(a,b,v)
            p=_vadd(p,_vscale(control,ru*rv))
            row.append(_add(vertices,cache,p))
        grid.append(row)
    for r in range(rows):
        for c in range(cols-1):
            faces.append((grid[r][c],grid[r][c+1],grid[r+1][c+1],grid[r+1][c]))


def _cross(xs,y,zs,bulge=0):
    n=len(xs); out=[]
    for i,(x,z) in enumerate(zip(xs,zs)):
        t=i/(n-1); out.append((x,y+bulge*4*t*(1-t),z))
    return tuple(out)


def generate_neutral_pelvis(shape=None):
    p=shape or NeutralPelvisShape(); w,d,h=p.width,p.depth,p.height
    vertices=[]; faces=[]; cache={}; gap=p.thigh_spacing*.5; outer=gap+p.thigh_opening_width
    z=(h*.50,h*.30,h*.06,-h*.20,-h*.55)
    spans=(p.waist_width*.47,w*.485,w*.515)
    fy=(p.waist_depth*.46,d*.49,d*.505,d*.405)
    ry=(-p.waist_depth*.46,-d*(.50+.020*p.glute_projection),-d*(.515+.060*p.glute_projection),-d*(.455+.050*p.glute_projection))

    def xs(s): return (-s,-s*.78,-s*.48,-s*.20,0,s*.20,s*.48,s*.78,s)
    front=[]; rear=[]
    for k in range(3):
        xx=xs(spans[k]); zz=tuple(z[k]-h*(.030*(abs(x)/spans[k])**1.7) for x in xx)
        front.append(_cross(xx,fy[k],zz,d*(.008+.004*k)))
        rear.append(_cross(xx,ry[k],zz,-d*(.012+.010*k)*p.glute_projection))

    lx=(-outer,-outer*.78,-outer*.50,-gap); rx=(gap,outer*.50,outer*.78,outer)
    inner=z[3]+h*.075; zl=(z[3]-h*.01,z[3],z[3]+h*.03,inner); zr=tuple(reversed(zl))
    rfl=_cross(lx,fy[3],zl,d*.006); rfr=_cross(rx,fy[3],zr,d*.006)
    rrl=_cross(lx,ry[3],tuple(q-h*.018 for q in zl),-d*.015); rrr=_cross(rx,ry[3],tuple(q-h*.018 for q in zr),-d*.015)
    ofl=_cross(lx,p.thigh_opening_depth*.5,(z[4],)*4); ofr=_cross(rx,p.thigh_opening_depth*.5,(z[4],)*4)
    orl=_cross(lx,-p.thigh_opening_depth*.5,(z[4],)*4); orr=_cross(rx,-p.thigh_opening_depth*.5,(z[4],)*4)

    # Upper front and rear regions now have local center controls.  The front
    # gains a gentle convex volume while the rear gets independent projection.
    _surface_patch(vertices,faces,cache,front[0],front[1],(0,d*.030,-h*.010),4)
    _surface_patch(vertices,faces,cache,front[1],front[2],(0,d*.050,-h*.018),5)
    _surface_patch(vertices,faces,cache,rear[0],rear[1],(0,-d*.045*p.glute_projection,-h*.008),4)
    _surface_patch(vertices,faces,cache,rear[1],rear[2],(0,-d*.095*p.glute_projection,-h*.016),5)

    fl=front[2][:4]; fr=front[2][5:]; rl=rear[2][:4]; rr=rear[2][5:]
    _surface_patch(vertices,faces,cache,fl,rfl,(-w*.055,d*.025,-h*.025),5)
    _surface_patch(vertices,faces,cache,fr,rfr,(w*.055,d*.025,-h*.025),5)
    _surface_patch(vertices,faces,cache,rl,rrl,(-w*.060,-d*.070*p.glute_projection,-h*.018),5)
    _surface_patch(vertices,faces,cache,rr,rrr,(w*.060,-d*.070*p.glute_projection,-h*.018),5)

    # Dedicated center arch regions; their center control creates curvature
    # without pulling their shared edges away from adjacent lower regions.
    aft=front[2][3:6]; art=rear[2][3:6]
    afb=(rfl[-1],(0,fy[3]*.92,inner+h*.035),rfr[0]); arb=(rrl[-1],(0,ry[3]*.94,inner+h*.020),rrr[0])
    _surface_patch(vertices,faces,cache,aft,afb,(0,d*.065,h*.035),5)
    _surface_patch(vertices,faces,cache,art,arb,(0,-d*.075*p.glute_projection,h*.025),5)

    # Side regions use four-sided patches too, so side-view volume can bow in
    # depth and width while every perimeter edge remains stitched.
    for fa,fb,ra,rb,amount in ((front[0],front[1],rear[0],rear[1],.045),(front[1],front[2],rear[1],rear[2],.065)):
        _surface_patch(vertices,faces,cache,(fa[0],fb[0]),(ra[0],rb[0]),(-w*amount,0,-h*.010),6)
        _surface_patch(vertices,faces,cache,(fa[-1],fb[-1]),(ra[-1],rb[-1]),(w*amount,0,-h*.010),6)
    _surface_patch(vertices,faces,cache,(fl[0],rfl[0]),(rl[0],rrl[0]),(-w*.055,0,-h*.012),6)
    _surface_patch(vertices,faces,cache,(fr[-1],rfr[-1]),(rr[-1],rrr[-1]),(w*.055,0,-h*.012),6)

    # Four explicit patches per outlet, with local controls for front/rear and
    # inner/outer curvature rather than a hidden tube primitive.
    for sign,rf,rb,of,ob in ((-1,rfl,rrl,ofl,orl),(1,rfr,rrr,ofr,orr)):
        _surface_patch(vertices,faces,cache,rf,of,(sign*w*.025,d*.035,h*.025),5)
        _surface_patch(vertices,faces,cache,rb,ob,(sign*w*.025,-d*.045,h*.020),5)
        oi=0 if sign<0 else -1; ii=-1 if sign<0 else 0
        _surface_patch(vertices,faces,cache,(rf[oi],of[oi]),(rb[oi],ob[oi]),(sign*w*.030,0,0),6)
        _surface_patch(vertices,faces,cache,(rf[ii],of[ii]),(rb[ii],ob[ii]),(-sign*p.crotch_width*.12,0,h*.025),6)

    sl=_curve(rfl[-1],rrl[-1],(0,0,h*.035),5); sr=_curve(rfr[0],rrr[0],(0,0,h*.035),5)
    _surface_patch(vertices,faces,cache,sl,sr,(0,0,-h*.045*p.crotch_drop),6)

    torso=tuple(_add(vertices,cache,q) for q in _curve((-p.waist_width*.5,fy[0],z[0]),(p.waist_width*.5,fy[0],z[0]),steps=15))
    left=tuple(_add(vertices,cache,q) for q in _curve((-outer,p.thigh_opening_depth*.5,z[4]),(-gap,p.thigh_opening_depth*.5,z[4]),steps=15))
    right=tuple(_add(vertices,cache,q) for q in _curve((gap,p.thigh_opening_depth*.5,z[4]),(outer,p.thigh_opening_depth*.5,z[4]),steps=15))
    return tuple(vertices),tuple(tuple(reversed(f)) for f in faces),{"torso":torso,"left_thigh":left,"right_thigh":right}
