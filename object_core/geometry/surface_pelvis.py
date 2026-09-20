# SPDX-License-Identifier: GPL-3.0-or-later
"""Boundary-conforming longitudinal pelvis patches for the mathematical study.

The torso circumference resolves into the lateral halves of two thigh loops.
Front/rear fans are spread over longitudinal rows, leaving only short triangles
at the two unavoidable topological poles. All adjacent patches share indices.
"""
from math import sin, pi, sqrt


def append_surface_pelvis(surface, upper, upper_adjacent, left, right, lower_adjacent):
    n=len(upper);quarter=n//4;half=n//2;steps=8;columns=16
    if n%4 or not all(len(r)==n for r in (upper_adjacent,left,right)):
        raise ValueError('Pelvis needs equally sized boundaries divisible by four')

    def vertex(point):
        index=len(surface.v);surface.v.append(tuple(point));return index

    def bridge(a,b):
        for j in range(len(a)-1):
            surface.f.append((a[j],a[j+1],b[j+1],b[j]))

    # Each side is an open half-ring. Endpoints will also belong to front/rear
    # transition patches; they must not be duplicated or welded by tolerance.
    sides=[]
    for root,start in ((left,3*quarter),(right,quarter)):
        indices=[(start+j)%n for j in range(half+1)]
        rows=[[upper[j] for j in indices]]
        for k in range(1,steps+1):
            t=k/steps;row=[]
            for j in indices:
                if k==steps:row.append(root[j]);continue
                a=surface.v[upper[j]];b=surface.v[root[j]];prev=surface.v[upper_adjacent[j]]
                dz=b[2]-a[2];denom=a[2]-prev[2]
                slope=tuple((a[d]-prev[d])*dz/denom for d in range(3))
                # Endpoint slopes follow the abdomen into the patch, then become
                # vertical near the thigh. This is geometry, not a normal trick.
                end=(0.,0.,dz)
                p=tuple((2*t**3-3*t*t+1)*a[d]+(t**3-2*t*t+t)*slope[d]+(-2*t**3+3*t*t)*b[d]+(t**3-t*t)*end[d] for d in range(3))
                row.append(vertex(p))
            bridge(rows[-1],row);rows.append(row)
        sides.append(rows)

    def cross_row(a,b,j,amount=1.):
        p,r=surface.v[a],surface.v[b];row=[a]
        # Continue the actual first thigh strip into a rounded pelvic arch.
        # The previous straight cross-strip created a near-right-angle corner.
        left_index=j%n;right_index=(2*quarter-j)%n
        directions=[]
        for root,next_row,index in ((left,lower_adjacent[0],left_index),(right,lower_adjacent[1],right_index)):
            delta=tuple(surface.v[root[index]][d]-surface.v[next_row[index]][d] for d in range(3))
            length=sqrt(sum(v*v for v in delta))
            directions.append(tuple(v/length for v in delta))
        span=sqrt(sum((p[d]-r[d])**2 for d in range(3)))
        for k in range(1,columns):
            u=k/columns
            m0=tuple(v*span*.35 for v in directions[0])
            m1=tuple(-v*span*.35 for v in directions[1])
            point=tuple((2*u**3-3*u*u+1)*p[d]+(u**3-2*u*u+u)*m0[d]+(-2*u**3+3*u*u)*r[d]+(u**3-u*u)*m1[d] for d in range(3))
            point=(point[0],point[1]+.020*sin(2*pi*j/n)*4*u*(1-u)*amount,point[2])
            row.append(vertex(point))
        row.append(b);return row

    saddle=[cross_row(left[(quarter+j)%n],right[(quarter-j)%n],quarter+j) for j in range(half+1)]
    for a,b in zip(saddle,saddle[1:]):bridge(a,b)

    # Triangles touch only the first short row. The rest is a shared quad grid.
    for pole,side_end,saddle_end in ((quarter,-1,0),(3*quarter,0,-1)):
        rows=[]
        for k in range(1,steps):
            a=sides[0][k][side_end]
            b=sides[1][k][0 if side_end==-1 else -1]
            rows.append(cross_row(a,b,pole,k/steps))
        rows.append(saddle[saddle_end])
        for j in range(columns):surface.f.append((upper[pole],rows[0][j],rows[0][j+1]))
        for a,b in zip(rows,rows[1:]):bridge(a,b)
# Compact anatomical displacement fields use meters, before final height scaling.
def _compact(value, center, radius):
    t=abs(value-center)/radius
    return (1-t*t)**2 if t<1 else 0.0


def refine_pelvic_planes(vertices):
    """Shape connected tissue, with zero value/slope at the region boundaries.

    Broad posterior volume and shallow inguinal relief are deliberately separate
    from topology generation. No added spheres, global smoothing or remeshing.
    """
    result=[]
    for x,y,z in vertices:
        rear=min(1.,max(0.,-y/.105))**2
        front=min(1.,max(0.,y/.095))**2
        glute=.022*_compact(abs(x),.082,.082)*_compact(z,.965,.115)
        fold=.003*_compact(abs(x),.08,.065)*_compact(z,.905+.10*abs(x),.010)
        inguinal=.0025*_compact(abs(x),.075,.075)*_compact(z,.925+.48*abs(x),.010)
        pubic=.006*_compact(x,0.,.065)*_compact(z,.945,.06)
        result.append((x,y-rear*(glute-fold)-front*(inguinal+pubic),z))
    return result


def fair_pelvic_patch(vertices, faces):
    """Bounded positive diffusion removes patch-boundary folds without overshoot.

    This is local geometric fairing, not a replacement for anatomical profiles.
    No negative Laplacian step, topology changes, or global shrink operation.
    """
    from collections import defaultdict
    neighbors=defaultdict(set)
    for face in faces:
        for a,b in zip(face,face[1:]+face[:1]):
            neighbors[a].add(b);neighbors[b].add(a)
    original=list(vertices);current=list(vertices)
    weights={i:_compact(z,.995,.135) for i,(x,y,z) in enumerate(vertices)
             if .86<z<1.13 and abs(x)<.23}
    for _ in range(40):
        updated={}
        for i,w in weights.items():
            if not neighbors[i]:continue
            mean=tuple(sum(current[j][d] for j in neighbors[i])/len(neighbors[i]) for d in range(3))
            point=tuple(current[i][d]+.4*w*(mean[d]-current[i][d]) for d in range(3))
            delta=tuple(point[d]-original[i][d] for d in range(3))
            length=sqrt(sum(v*v for v in delta))
            factor=min(1.,.02/max(length,1e-12))
            updated[i]=tuple(original[i][d]+factor*delta[d] for d in range(3))
        for i,p in updated.items():current[i]=p
    return current
