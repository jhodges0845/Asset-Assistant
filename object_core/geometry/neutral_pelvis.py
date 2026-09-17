# SPDX-License-Identifier: GPL-3.0-or-later
"""Recipe-driven patch-and-stitch pelvis experiment.

Generic helpers create curves and stitched surface grids.  The recipe below
supplies control locations; the helpers deliberately know nothing about human
anatomy so the construction approach can be reused by other object recipes.
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


def semantic_controls():
    return tuple(NeutralPelvisShape.__dataclass_fields__)


def _lerp(a, b, t):
    return tuple(x + (y - x) * t for x, y in zip(a, b))


def _add_vertex(vertices, cache, point):
    key = tuple(round(v, 7) for v in point)
    if key not in cache:
        cache[key] = len(vertices)
        vertices.append(point)
    return cache[key]


def _curve(a, b, bulge=(0.0, 0.0, 0.0), steps=4):
    result = []
    for i in range(steps + 1):
        t = i / steps
        q = 4.0 * t * (1.0 - t)
        p = _lerp(a, b, t)
        result.append(tuple(p[j] + bulge[j] * q for j in range(3)))
    return result


def _patch(vertices, faces, cache, a, b, bow=(0.0, 0.0, 0.0), rows=3):
    """Create a shared-vertex surface strip between equal control curves."""
    if len(a) != len(b):
        raise ValueError("Patch boundaries must have equal point counts")
    grid = []
    for r in range(rows + 1):
        t = r / rows
        q = 4.0 * t * (1.0 - t)
        row = []
        for p0, p1 in zip(a, b):
            p = _lerp(p0, p1, t)
            p = tuple(p[j] + bow[j] * q for j in range(3))
            row.append(_add_vertex(vertices, cache, p))
        grid.append(row)
    for r in range(rows):
        for c in range(len(a) - 1):
            faces.append((grid[r][c], grid[r][c + 1], grid[r + 1][c + 1], grid[r + 1][c]))
    return tuple(grid[0]), tuple(grid[-1])


def _edge(a, b):
    return [a, b]


def generate_neutral_pelvis(shape=None):
    p = shape or NeutralPelvisShape()
    w, d, h = p.width, p.depth, p.height
    vertices, faces, cache = [], [], {}

    # Recipe controls.  Generic construction code only sees curves and patches.
    gap = p.thigh_spacing * .5
    outlet_outer = gap + p.thigh_opening_width
    side = w * .515
    z0, z1, z2, z3 = h*.50, h*.13, -h*.18, -h*.55
    ft, rt = p.waist_depth*.50, -p.waist_depth*.50
    f1, r1 = d*.51, -d*(.51 + .055*p.glute_projection)
    f2, r2 = d*.43, -d*(.47 + .045*p.glute_projection)
    fo, ro = p.thigh_opening_depth*.50, -p.thigh_opening_depth*.50

    # Each half has four longitudinal control rails: center/inner, quarter,
    # lateral, then rear counterparts.  Their endpoints are shared exactly.
    def span(z, y, inner, outer, sign, depth_bulge=0.0):
        return _curve((sign*inner, y, z), (sign*outer, y*.88, z),
                      bulge=(sign*w*.012*p.hip_fullness, depth_bulge, 0.0), steps=4)

    halves = {}
    for sign, key in ((1.0, "a"), (-1.0, "b")):
        tf = span(z0, ft, 0.0, p.waist_width*.5, sign, .15)
        tr = span(z0, rt, 0.0, p.waist_width*.5, sign, -.15)
        mf = span(z1, f1, 0.0, side, sign, .30)
        mr = span(z1, r1, 0.0, side, sign, -.50*p.glute_projection)
        lf = span(z2, f2, gap, outlet_outer, sign, .12)
        lr = span(z2, r2, gap, outlet_outer, sign, -.35*p.glute_projection)
        of = span(z3, fo, gap, outlet_outer, sign)
        orr = span(z3, ro, gap, outlet_outer, sign)
        halves[key] = (tf, tr, mf, mr, lf, lr, of, orr)

        # Front and rear recipe regions.  More of the taper occurs above z2 so
        # the outlets descend from the mass rather than hanging below a shelf.
        _patch(vertices, faces, cache, tf, mf, bow=(sign*w*.018, .10, 0), rows=2)
        _patch(vertices, faces, cache, mf, lf, bow=(sign*w*.025, -.10, -h*.018), rows=3)
        _patch(vertices, faces, cache, lf, of, bow=(sign*w*.008, -.18, h*.012), rows=2)
        _patch(vertices, faces, cache, tr, mr, bow=(sign*w*.018, -d*.025, 0), rows=2)
        _patch(vertices, faces, cache, mr, lr, bow=(sign*w*.026, -d*.045, -h*.012), rows=3)
        _patch(vertices, faces, cache, lr, orr, bow=(sign*w*.008, -d*.020, h*.010), rows=2)

        # Continuous outside wall.  Using corresponding endpoints makes this a
        # true stitched boundary rather than a visually adjacent surface.
        for front, rear in ((tf, tr), (mf, mr), (lf, lr), (of, orr)):
            _patch(vertices, faces, cache, _edge(front[-1], rear[-1]),
                   _edge(front[-1], rear[-1]), rows=1)  # endpoint registration
        for fa, fb, ra, rb in ((tf, mf, tr, mr), (mf, lf, mr, lr), (lf, of, lr, orr)):
            _patch(vertices, faces, cache, _edge(fa[-1], fb[-1]), _edge(ra[-1], rb[-1]),
                   bow=(sign*w*.030, -d*.012, 0), rows=4)

        # Close the inner wall of each outlet all the way from front to rear.
        _patch(vertices, faces, cache, _edge(lf[0], of[0]), _edge(lr[0], orr[0]),
               bow=(-sign*p.crotch_width*.06, 0, -h*.018), rows=4)

    ap = halves["a"]
    bp = halves["b"]

    # Close the upper center front and rear seams separately.  The first
    # experiment accidentally bridged front to rear here, leaving visible
    # diamond openings.  These strips now join mirrored halves across x=0.
    for ai, bi in ((ap[0], bp[0]), (ap[2], bp[2])):
        _patch(vertices, faces, cache, _edge(bi[0], ai[0]), _edge(bi[1], ai[1]), rows=1)
    for ai, bi in ((ap[1], bp[1]), (ap[3], bp[3])):
        _patch(vertices, faces, cache, _edge(ai[0], bi[0]), _edge(ai[1], bi[1]), rows=1)

    # Central lower saddle joins the two inner control rails.  It is broad at
    # z2 and bows upward toward the front/rear so the split reads as a shallow
    # arch instead of a rectangular hole.
    alf, alr = ap[4], ap[5]
    blf, blr = bp[4], bp[5]
    left_inner = _curve(blf[0], blr[0], bulge=(0, 0, h*.035), steps=4)
    right_inner = _curve(alf[0], alr[0], bulge=(0, 0, h*.035), steps=4)
    _patch(vertices, faces, cache, left_inner, right_inner,
           bow=(0, 0, -h*.035*p.crotch_drop), rows=4)

    # Explicit open attachment boundaries are recipe outputs.  They need not
    # dictate the internal patch topology.
    torso = tuple(_add_vertex(vertices, cache, q) for q in _curve(
        (-p.waist_width*.5, ft, z0), (p.waist_width*.5, ft, z0), steps=15))
    left_thigh = tuple(_add_vertex(vertices, cache, q) for q in _curve(
        (gap, fo, z3), (outlet_outer, fo, z3), steps=15))
    right_thigh = tuple(_add_vertex(vertices, cache, q) for q in _curve(
        (-outlet_outer, fo, z3), (-gap, fo, z3), steps=15))
    boundaries = {"torso": torso, "left_thigh": left_thigh, "right_thigh": right_thigh}
    return tuple(vertices), tuple(tuple(reversed(f)) for f in faces), boundaries
