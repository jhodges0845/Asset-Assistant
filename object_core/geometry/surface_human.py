# SPDX-License-Identifier: GPL-3.0-or-later
"""Opt-in mathematical Human surface, independent of Blender and external meshes.

Versioned topology. Explicit torso/arm openings and a bilateral pelvic saddle;
no voxel union, downloaded mesh, or stochastic geometry. Not legacy-rig compatible.
"""
from dataclasses import dataclass, asdict
from math import sin, cos, pi, exp, sqrt, atan2, isfinite
from ..models.mesh import MeshPart, ObjectMesh
from .anatomical_human import _orient_faces_consistently
from .surface_pelvis import append_surface_pelvis, refine_pelvic_planes, fair_pelvic_patch

VERSION = 'surface-human-1'

@dataclass(frozen=True)
class SurfaceHumanSpec:
    height_cm: float = 175.0
    shoulder_scale: float = 1.0
    waist_scale: float = 1.0
    hip_scale: float = 1.0
    chest_fullness: float = 0.55
    muscle_definition: float = 0.45

    def __post_init__(self):
        for name, value in asdict(self).items():
            if isinstance(value, bool) or not isinstance(value, (float, int)) or not isfinite(value):
                raise ValueError(name + ' must be a finite number')
            lo, hi = (150., 200.) if name == 'height_cm' else ((0., 1.) if name in ('chest_fullness', 'muscle_definition') else (.85, 1.15))
            if not lo <= value <= hi:
                raise ValueError('%s must be in [%s, %s]' % (name, lo, hi))


def _bell(x, c, r):
    return exp(-((x-c)/r)**2)


def _sample(rows, x):
    """Cubic Hermite profile with clamped extrema; rows start with path parameter."""
    if x <= rows[0][0]: return rows[0][1:]
    if x >= rows[-1][0]: return rows[-1][1:]
    for i in range(len(rows)-1):
        a,b=rows[i:i+2]
        if x<=b[0]:
            before=rows[max(0,i-1)];after=rows[min(len(rows)-1,i+2)]
            h=b[0]-a[0];t=(x-a[0])/h;out=[]
            for j in range(1,len(a)):
                secant=(b[j]-a[j])/h
                prior=(a[j]-before[j])/(a[0]-before[0]) if i else secant
                following=(after[j]-b[j])/(after[0]-b[0]) if i+2<len(rows) else secant
                m0=2*prior*secant/(prior+secant) if prior*secant>0 else 0.
                m1=2*following*secant/(following+secant) if following*secant>0 else 0.
                q=(2*t**3-3*t*t+1)*a[j]+(t**3-2*t*t+t)*h*m0+(-2*t**3+3*t*t)*b[j]+(t**3-t*t)*h*m1
                out.append(max(min(a[j],b[j]),min(max(a[j],b[j]),q)))
            return tuple(out)


class _Surface:
    def __init__(self): self.v=[];self.f=[]
    def ring(self, points):
        ids=tuple(range(len(self.v),len(self.v)+len(points)));self.v.extend(points);return ids
    def band(self,a,b):
        if len(a)!=len(b):raise ValueError('boundary resolution mismatch')
        self.f.extend((a[j],a[(j+1)%len(a)],b[(j+1)%len(a)],b[j]) for j in range(len(a)))
    def cap(self,a):
        p=tuple(sum(self.v[i][k] for i in a)/len(a) for k in range(3));c=len(self.v);self.v.append(p)
        self.f.extend((a[j],a[(j+1)%len(a)],c) for j in range(len(a)))
    def split(self,upper,left,right,saddle=False,upper_adjacent=None,lower_adjacent=None):
        if saddle:
            return append_surface_pelvis(self,upper,upper_adjacent,left,right,lower_adjacent)
        n=len(upper);q=n//4;h=n//2
        for ring,start in ((left,3*q),(right,q)):
            for j in range(h):
                a,b=(start+j)%n,(start+j+1)%n
                self.f.append((upper[a],upper[b],ring[b],ring[a]))
        for j in range(h):
            a,b=(q+j)%n,(q+j+1)%n;c,d=(q-j)%n,(q-j-1)%n
            self.f.append((left[a],left[b],right[d],right[c]))
        self.f.extend(((upper[q],left[q],right[q]),(upper[3*q],right[3*q],left[3*q])))



def _ellipse(cx,cy,z,rx,ry,n):
    return [(cx+rx*cos(2*pi*j/n),cy+ry*sin(2*pi*j/n),z) for j in range(n)]


def generate_surface_human(spec=SurfaceHumanSpec()):
    if not isinstance(spec,SurfaceHumanSpec):raise TypeError('expected SurfaceHumanSpec')
    b=_Surface();n=64
    # z, half breadth, front depth, back depth, sagittal center offset.
    profile=[(.99,.172,.093,.113,.012),(1.035,.178,.096,.112,.008),(1.09,.155,.086,.091,.004),(1.16,.127,.078,.072,.002),(1.23,.138,.087,.083,0),(1.30,.161,.092,.09,0),(1.36,.173,.096,.088,0),(1.40,.171,.085,.077,0),(1.435,.145,.063,.06,0),(1.465,.072,.046,.05,-.003),(1.50,.047,.042,.048,-.004),(1.53,.046,.043,.049,0),(1.548,.038,.057,.057,.009),(1.566,.051,.060,.064,.002),(1.59,.063,.064,.071,0),(1.622,.071,.068,.082,-.003),(1.654,.072,.069,.084,-.004),(1.687,.072,.070,.081,-.004),(1.716,.064,.064,.073,-.005),(1.739,.042,.046,.053,-.006),(1.750,.003,.004,.004,-.006)]
    zs=[1.06+i*.005 for i in range(89)]+[1.505+i*.0025 for i in range(99)]
    rings=[]
    for z in zs:
        rx,front,back,cy=_sample(profile,z)
        rx*=1+(spec.waist_scale-1)*_bell(z,1.16,.085)+(spec.hip_scale-1)*_bell(z,1.02,.09)+(spec.shoulder_scale-1)*_bell(z,1.40,.06)
        points=[]
        for j in range(n):
            a=2*pi*j/n;c,s=cos(a),sin(a);x=rx*c;y=cy+(front if s>=0 else back)*s
            if s>0:
                mask=s**6
                # Chest tissue emerges continuously from ribcage; no helper spheres.
                y+=.027*spec.chest_fullness*_bell(abs(x),.075,.047)*_bell(z,1.325,.042)*mask
                y-=.003*spec.muscle_definition*_bell(x,0,.016)*_bell(z,1.28,.11)*mask
                y-=.0025*_bell(x,0,.01)*_bell(z,1.10,.014)*mask
                y+=.004*spec.muscle_definition*_bell(z,1.414-abs(x)*.13,.009)*mask
                if z>1.54:
                    y+=mask*(.020*_bell(x,0,.010)*_bell(z,1.624,.030)+.024*_bell(x,0,.014)*_bell(z,1.605,.010)
                        -.010*_bell(abs(x),.030,.018)*_bell(z,1.631,.013)
                        +.004*_bell(abs(x),.032,.023)*_bell(z,1.648,.007)
                        +.006*_bell(abs(x),.046,.016)*_bell(z,1.610,.013)
                        +.006*_bell(x,0,.028)*_bell(z,1.577,.007)
                        +.004*_bell(x,0,.024)*_bell(z,1.587,.003)
                        -.003*_bell(x,0,.025)*_bell(z,1.583,.0018))
            else:
                y+=.003*spec.muscle_definition*_bell(x,0,.014)*_bell(z,1.27,.14)*(-s)**4
                y-=.005*spec.muscle_definition*_bell(abs(x),.065,.033)*_bell(z,1.36,.046)*(-s)**4
            # Integrated ear relief in the same surface, with a shallow concha.
            ear=_bell(z,1.627,.024)*abs(c)**30
            x+=(1 if c>=0 else -1)*.012*ear
            points.append((x,y,z))
        rings.append(b.ring(points))
    # Shoulder windows: remove a rectangular patch and stitch its actual perimeter.
    lower=zs.index(1.335) if 1.335 in zs else min(range(len(zs)),key=lambda i:abs(zs[i]-1.335))
    upper=min(range(len(zs)),key=lambda i:abs(zs[i]-1.425))
    holes={}
    for sign,center in ((1,0),(-1,32)):
        start=center-5;end=center+5
        perimeter=[rings[lower][j%n] for j in range(start,end+1)]
        perimeter += [rings[i][end%n] for i in range(lower+1,upper+1)]
        perimeter += [rings[upper][j%n] for j in range(end-1,start-1,-1)]
        perimeter += [rings[i][start%n] for i in range(upper-1,lower,-1)]
        holes[sign]=perimeter
    for i in range(len(rings)-1):
        for j in range(n):
            if lower<=i<upper and (j in [k%n for k in range(-5,5)] or 27<=j<37):continue
            b.f.append((rings[i][j],rings[i][(j+1)%n],rings[i+1][(j+1)%n],rings[i+1][j]))
    b.cap(rings[-1])
    # Pelvis: a true pair-of-pants surface. The inner thigh rises to the saddle.
    roots={}
    for sign in (1,-1):
        pts=[]
        for j in range(n):
            a=2*pi*j/n;c,s=cos(a),sin(a);outer=max(0,sign*c);inner=max(0,-sign*c)
            x=sign*.089*spec.hip_scale+.083*spec.hip_scale*c
            y=.007+(.088 if s>0 else .108)*s
            z=.965+.030*sign*c-.025*c*c-.008*max(0,-s)
            pts.append((x,y,z))
        roots[sign]=b.ring(pts)
    first_leg_rows={}
    leg_profile=[(.09,.022,.026,.187,.005),(.17,.024,.029,.183,.004),(.28,.036,.043,.176,-.008),(.36,.048,.054,.168,-.016),(.43,.047,.051,.162,-.01),(.50,.037,.037,.155,.008),(.55,.042,.043,.149,.011),(.65,.057,.06,.135,.005),(.76,.071,.075,.115,0),(.86,.078,.084,.098,0),(.94,.083,.092,.089,0)]
    for sign in (1,-1):
        previous=roots[sign]
        for k in range(1,91):
            t=k/90;z=.928*(1-t)+.09*t;rx,ry,cx,cy=_sample(leg_profile,z)
            pts=[]
            for j in range(n):
                a=2*pi*j/n;c,s=cos(a),sin(a);outer=max(0,sign*c);inner=max(0,-sign*c)
                fade=max(0,1-t/.22)**2
                zz=z+fade*(b.v[roots[sign][j]][2]-.928)
                xx=sign*cx+rx*c;yy=cy+ry*s
                yy+=.003*spec.muscle_definition*_bell(z,.53,.025)*max(0,s)**5
                yy-=.006*fade*max(0,-s)**3
                # Crossfade exactly to the authored root, preventing a join shelf.
                root=b.v[roots[sign][j]]
                blend=max(0,1-t/.06)
                pts.append((xx*(1-blend)+root[0]*blend,yy*(1-blend)+root[1]*blend,zz))
            current=b.ring(pts);b.band(previous,current);previous=current
            if k==1:first_leg_rows[sign]=current
        # Ankle -> heel -> instep -> toe: one bent surface, no floating feet.
        for k in range(1,33):
            t=k/32;rx=_sample([(0,.022),(.20,.031),(.65,.045),(.95,.039),(1,.032)],t)[0];ry=.026*(1-t)+.014*t
            center=(sign*.187,-.006+.18*t,.09-.059*min(t/.24,1)-.003*t)
            angle=pi/2*min(1,t*2)
            pts=[(center[0]+rx*cos(2*pi*j/n),center[1]+ry*sin(2*pi*j/n)*cos(angle),center[2]+ry*sin(2*pi*j/n)*sin(angle)) for j in range(n)]
            current=b.ring(pts);b.band(previous,current);previous=current
        b.cap(previous)
    b.split(rings[0],roots[1],roots[-1],saddle=True,upper_adjacent=rings[1],lower_adjacent=(first_leg_rows[1],first_leg_rows[-1]))
    # Arms use the perimeter of a real torso opening. No independent limb shells.
    for sign in (1,-1):
        root=holes[sign];count=len(root)
        root=sorted(root,key=lambda i:atan2(b.v[i][2]-1.38,b.v[i][1]))
        arm=[(0,.192,1.385,.044,.048),(.07,.218,1.37,.046,.047),(.15,.234,1.33,.043,.043),(.40,.263,1.19,.032,.034),(.57,.28,1.12,.037,.034),(.83,.302,.99,.026,.025),(1,.308,.923,.018,.018)]
        previous=root
        # Match each root's angular position to avoid spiraling the shoulder seam.
        angles=[atan2(b.v[i][2]-1.38,b.v[i][1]) for i in root]
        for k in range(1,65):
            t=k/64;cx,z,rx,ry=_sample(arm,t);pts=[]
            cx+=.19*(spec.shoulder_scale-1)*max(0,1-t/.5)
            for j,original_angle in enumerate(angles):
                uniform=-pi+2*pi*j/count
                blend_angle=min(1,t/.25)
                a=original_angle*(1-blend_angle)+uniform*blend_angle
                rotation=1.19*min(1,t/.18)
                target=(sign*(cx+rx*sin(a)*sin(rotation)),ry*cos(a),z+rx*sin(a)*cos(rotation))
                q=min(1,t/.14);q=q*q*(3-2*q);p=b.v[root[j]]
                pts.append(tuple(p[d]*(1-q)+target[d]*q for d in range(3)))
            current=b.ring(pts);b.band(previous,current);previous=current
        # Reparameterize to a vertical palm ring, then split twice into four digits.
        hand_n=count
        palm=b.ring(_ellipse(sign*.316,0,.89,.028,.014,hand_n))
        # Root is angularly sorted; nearest cyclic correspondence minimizes twist.
        def connect(a,c):
            best=min((sum(sum((b.v[a[j]][d]-b.v[c[(j*direction+shift)%len(c)]][d])**2 for d in range(3)) for j in range(len(a))),direction,shift) for direction in (-1,1) for shift in range(len(c)))
            ordered=tuple(c[(j*best[1]+best[2])%len(c)] for j in range(len(c)));b.band(a,ordered)
        connect(previous,palm)
        end=b.ring(_ellipse(sign*.316,0,.855,.029,.012,hand_n));b.band(palm,end)
        # Pair-of-pants topology needs counts divisible by four (56 here).
        pairs=[]
        for dx in (.014,-.014):pairs.append(b.ring(_ellipse(sign*.316+dx,0,.843,.0135,.010,hand_n)))
        b.split(end,*pairs)
        for idx,pair in enumerate(pairs):
            center=sign*.316+(.014 if idx==0 else -.014);digits=[]
            for dx in (.007,-.007):digits.append(b.ring(_ellipse(center+dx,0,.835,.0065,.008,hand_n)))
            b.split(pair,*digits)
            for digit in digits:
                cx=sum(b.v[i][0] for i in digit)/hand_n;prev=digit
                length=.050+.014*(1-min(1,abs(cx-sign*.316)/.025))
                for k in range(1,13):
                    t=k/12;r=max(.12,sqrt(max(0,1-t*t)))
                    cur=b.ring(_ellipse(cx,-.006*sin(t*pi/2),.835-length*t,.0065*r,.008*r,hand_n));b.band(prev,cur);prev=cur
                b.cap(prev)
        # Thumb branches from one palm quad, preserving topological connection.
        target=min(range(len(b.f)),key=lambda i:sum((sum(b.v[v][d] for v in b.f[i])/len(b.f[i])-q)**2 for d,q in enumerate((sign*.292,0,.873))))
        opening=b.f.pop(target);prev=opening
        for k in range(1,13):
            t=k/12;cx=sign*(.287-.034*t);z=.873-.032*t;r=.007*(1-.85*t)
            cur=b.ring([(cx,r*cos(2*pi*j/len(opening)),z+r*sin(2*pi*j/len(opening))) for j in range(len(opening))]);connect(prev,cur);prev=cur
        b.cap(prev)
    # Bounded two-step relaxation at shoulder junctions.
    # This removes sampling-density creases; it does not supply missing anatomy.
    from collections import defaultdict
    neighbors=defaultdict(set)
    for face in b.f:
        for j,a in enumerate(face):
            c=face[(j+1)%len(face)];neighbors[a].add(c);neighbors[c].add(a)
    weights={}
    for i,(x,y,z) in enumerate(b.v):
        if 1.30<z<1.465 and abs(x)>.11:weights[i]=.8*_bell(z,1.38,.06)
    for _ in range(12):
        for factor in (.45,-.46):
            updated={}
            for i,w in weights.items():
                if neighbors[i]:
                    avg=tuple(sum(b.v[j][d] for j in neighbors[i])/len(neighbors[i]) for d in range(3))
                    updated[i]=tuple(b.v[i][d]+factor*w*(avg[d]-b.v[i][d]) for d in range(3))
            for i,p in updated.items():b.v[i]=p
    b.v=fair_pelvic_patch(refine_pelvic_planes(b.v),b.f)
    used=sorted({v for face in b.f for v in face})
    remap={old:new for new,old in enumerate(used)}
    b.v=[b.v[i] for i in used]
    faces=_orient_faces_consistently(tuple(tuple(remap[i] for i in f) for f in b.f))
    scale=spec.height_cm/1.75
    low=min(p[2] for p in b.v);high=max(p[2] for p in b.v)
    vertices=tuple((x*scale,y*scale,(z-low)*spec.height_cm/(high-low)) for x,y,z in b.v)
    # Determine global orientation after stitching; enforce positive signed volume.
    volume=0.
    for f in faces:
        a=vertices[f[0]]
        for j in range(1,len(f)-1):
            c,d=vertices[f[j]],vertices[f[j+1]]
            volume+=a[0]*(c[1]*d[2]-c[2]*d[1])+a[1]*(c[2]*d[0]-c[0]*d[2])+a[2]*(c[0]*d[1]-c[1]*d[0])
    if volume<0:faces=tuple(tuple(reversed(f)) for f in faces)
    return ObjectMesh((MeshPart('human_surface',vertices,faces),))
