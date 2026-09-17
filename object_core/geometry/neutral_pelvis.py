# SPDX-License-Identifier: GPL-3.0-or-later
"""Recipe-driven patch-and-stitch pelvis experiment.

The mesh is assembled from generic named boundaries and rectangular regions.
Adjacent regions reference the same boundary coordinates; object meaning stays
in this recipe rather than in the patch builder.
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
    return tuple(x + (y-x)*t for x, y in zip(a, b))


def _curve(a, b, bulge=(0.0, 0.0, 0.0), steps=4):
    points = []
    for i in range(steps+1):
        t = i/steps
        q = 4*t*(1-t)
        p = _lerp(a, b, t)
        points.append(tuple(p[j] + bulge[j]*q for j in range(3)))
    return tuple(points)


def _add(vertices, cache, p):
    key = tuple(round(v, 7) for v in p)
    if key not in cache:
        cache[key] = len(vertices)
        vertices.append(p)
    return cache[key]


def _strip(vertices, faces, cache, a, b, bow=(0, 0, 0), rows=2):
    """Generic shared-vertex strip between two equal sampled boundaries."""
    if len(a) != len(b):
        raise ValueError("region boundaries require equal samples")
    grid = []
    for r in range(rows+1):
        t = r/rows
        q = 4*t*(1-t)
        row = []
        for pa, pb in zip(a, b):
            p = _lerp(pa, pb, t)
            p = tuple(p[j] + bow[j]*q for j in range(3))
            row.append(_add(vertices, cache, p))
        grid.append(row)
    for r in range(rows):
        for c in range(len(a)-1):
            faces.append((grid[r][c], grid[r][c+1], grid[r+1][c+1], grid[r+1][c]))


def _cross_curve(x_values, y, z_values, depth_bulge=0.0):
    """Sample a recipe cross-boundary without assuming a ring."""
    result = []
    count = len(x_values)
    for i, (x, z) in enumerate(zip(x_values, z_values)):
        t = i/(count-1)
        q = 4*t*(1-t)
        result.append((x, y + depth_bulge*q, z))
    return tuple(result)


def generate_neutral_pelvis(shape=None):
    p = shape or NeutralPelvisShape()
    w, d, h = p.width, p.depth, p.height
    vertices, faces, cache = [], [], {}

    # The recipe intentionally uses more regions than the first prototype.
    # Five vertical levels let the upper mass, widest area, lower taper, root,
    # and outlet be controlled independently instead of forcing one patch to
    # describe several different curvature changes.
    z = (h*.50, h*.27, h*.04, -h*.22, -h*.55)
    half = (p.waist_width*.50, w*.50, w*.515, w*.43, 0.0)
    gap = p.thigh_spacing*.5
    outer = gap + p.thigh_opening_width

    # Seven samples across the full width at the upper three levels.  They are
    # control boundaries, not closed loops.  Denser sampling around the center
    # and lateral shoulders gives the patches room to describe silhouette.
    def upper_x(span):
        return (-span, -span*.62, -span*.24, 0.0, span*.24, span*.62, span)

    front_y = (p.waist_depth*.50, d*.515, d*.52, d*.43)
    rear_y = (-p.waist_depth*.50,
              -d*(.515 + .025*p.glute_projection),
              -d*(.53 + .055*p.glute_projection),
              -d*(.47 + .035*p.glute_projection))

    front, rear = [], []
    for level in range(3):
        xs = upper_x(half[level])
        # Slight vertical crown at the outer quarter avoids horizontal shelves.
        zs = tuple(z[level] - h*(.012 if abs(x) > half[level]*.55 else 0) for x in xs)
        front.append(_cross_curve(xs, front_y[level], zs, depth_bulge=d*.010))
        rear.append(_cross_curve(xs, rear_y[level], zs, depth_bulge=-d*.018*p.glute_projection))

    # Root level is split into two independent boundaries, which is where the
    # single upper mass actually branches.  No fake center seam is generated.
    left_x = (-outer, -(outer*.72), -gap)
    right_x = (gap, outer*.72, outer)
    root_front_l = _cross_curve(left_x, front_y[3], (z[3], z[3]-h*.018, z[3]-h*.045))
    root_front_r = _cross_curve(right_x, front_y[3], (z[3]-h*.045, z[3]-h*.018, z[3]))
    root_rear_l = _cross_curve(left_x, rear_y[3], (z[3]-h*.015, z[3]-h*.025, z[3]-h*.050), -d*.010)
    root_rear_r = _cross_curve(right_x, rear_y[3], (z[3]-h*.050, z[3]-h*.025, z[3]-h*.015), -d*.010)

    outlet_front_l = _cross_curve(left_x, p.thigh_opening_depth*.5, (z[4],)*3)
    outlet_front_r = _cross_curve(right_x, p.thigh_opening_depth*.5, (z[4],)*3)
    outlet_rear_l = _cross_curve(left_x, -p.thigh_opening_depth*.5, (z[4],)*3)
    outlet_rear_r = _cross_curve(right_x, -p.thigh_opening_depth*.5, (z[4],)*3)

    # Upper front/rear regions: 3 horizontal bands x front/rear.  Boundaries are
    # reused exactly by adjacent strips, so there is no post-hoc seam closure.
    _strip(vertices, faces, cache, front[0], front[1], bow=(0, d*.010, -h*.006), rows=2)
    _strip(vertices, faces, cache, front[1], front[2], bow=(0, d*.018, -h*.010), rows=2)
    _strip(vertices, faces, cache, rear[0], rear[1], bow=(0, -d*.018, -h*.004), rows=2)
    _strip(vertices, faces, cache, rear[1], rear[2], bow=(0, -d*.035*p.glute_projection, -h*.010), rows=2)

    # Split the lower front/rear into four regions.  The center region terminates
    # at the root arch while the lateral regions continue into each outlet.
    upper_l = front[2][:3]
    upper_r = front[2][4:]
    upper_rl = rear[2][:3]
    upper_rr = rear[2][4:]
    _strip(vertices, faces, cache, upper_l, root_front_l, bow=(-w*.018, 0, -h*.015), rows=3)
    _strip(vertices, faces, cache, upper_r, root_front_r, bow=(w*.018, 0, -h*.015), rows=3)
    _strip(vertices, faces, cache, upper_rl, root_rear_l, bow=(-w*.018, -d*.025, -h*.012), rows=3)
    _strip(vertices, faces, cache, upper_rr, root_rear_r, bow=(w*.018, -d*.025, -h*.012), rows=3)

    # Center front and rear arch patches use the actual central upper samples.
    # They meet the two root endpoints instead of leaving a vertical slit.
    front_arch_top = front[2][2:5]
    rear_arch_top = rear[2][2:5]
    front_arch_bottom = (root_front_l[-1], (0.0, front_y[3]*.94, z[3]-h*.085), root_front_r[0])
    rear_arch_bottom = (root_rear_l[-1], (0.0, rear_y[3]*.96, z[3]-h*.090), root_rear_r[0])
    _strip(vertices, faces, cache, front_arch_top, front_arch_bottom, bow=(0, d*.012, h*.010), rows=3)
    _strip(vertices, faces, cache, rear_arch_top, rear_arch_bottom, bow=(0, -d*.018, h*.008), rows=3)

    # Left/right outside walls are separate regions at each height band.  Their
    # edges are the exact endpoints of the front/rear boundaries.
    for fa, fb, ra, rb in ((front[0], front[1], rear[0], rear[1]),
                           (front[1], front[2], rear[1], rear[2])):
        _strip(vertices, faces, cache, (fa[0], fb[0]), (ra[0], rb[0]), bow=(-w*.020, 0, 0), rows=4)
        _strip(vertices, faces, cache, (fa[-1], fb[-1]), (ra[-1], rb[-1]), bow=(w*.020, 0, 0), rows=4)

    _strip(vertices, faces, cache, (upper_l[0], root_front_l[0]), (upper_rl[0], root_rear_l[0]), bow=(-w*.018, 0, 0), rows=4)
    _strip(vertices, faces, cache, (upper_r[-1], root_front_r[-1]), (upper_rr[-1], root_rear_r[-1]), bow=(w*.018, 0, 0), rows=4)

    # Four regions per outlet: front, rear, outer wall and inner wall.  This is
    # deliberately explicit patch-and-stitch rather than a hidden ring/tube.
    for sign, rf, rr, of, orr in ((-1, root_front_l, root_rear_l, outlet_front_l, outlet_rear_l),
                                  (1, root_front_r, root_rear_r, outlet_front_r, outlet_rear_r)):
        _strip(vertices, faces, cache, rf, of, bow=(sign*w*.006, -d*.008, h*.008), rows=2)
        _strip(vertices, faces, cache, rr, orr, bow=(sign*w*.006, -d*.015, h*.006), rows=2)
        _strip(vertices, faces, cache, (rf[0 if sign < 0 else -1], of[0 if sign < 0 else -1]),
               (rr[0 if sign < 0 else -1], orr[0 if sign < 0 else -1]),
               bow=(sign*w*.010, 0, 0), rows=4)
        _strip(vertices, faces, cache, (rf[-1 if sign < 0 else 0], of[-1 if sign < 0 else 0]),
               (rr[-1 if sign < 0 else 0], orr[-1 if sign < 0 else 0]),
               bow=(-sign*p.crotch_width*.05, 0, -h*.010), rows=4)

    # The lower-center saddle is its own region between the two inner root
    # boundaries.  It shares all four corner points with the arch/outlet walls.
    saddle_l = _curve(root_front_l[-1], root_rear_l[-1], bulge=(0, 0, h*.030), steps=4)
    saddle_r = _curve(root_front_r[0], root_rear_r[0], bulge=(0, 0, h*.030), steps=4)
    _strip(vertices, faces, cache, saddle_l, saddle_r, bow=(0, 0, -h*.028*p.crotch_drop), rows=4)

    # Preserve the established 16-sample public attachment contract while the
    # internal recipe remains independent of ring topology.
    torso = tuple(_add(vertices, cache, q) for q in _curve(
        (-p.waist_width*.5, front_y[0], z[0]), (p.waist_width*.5, front_y[0], z[0]), steps=15))
    left_thigh = tuple(_add(vertices, cache, q) for q in _curve(
        (-outer, p.thigh_opening_depth*.5, z[4]), (-gap, p.thigh_opening_depth*.5, z[4]), steps=15))
    right_thigh = tuple(_add(vertices, cache, q) for q in _curve(
        (gap, p.thigh_opening_depth*.5, z[4]), (outer, p.thigh_opening_depth*.5, z[4]), steps=15))
    return tuple(vertices), tuple(tuple(reversed(f)) for f in faces), {
        "torso": torso, "left_thigh": left_thigh, "right_thigh": right_thigh,
    }
