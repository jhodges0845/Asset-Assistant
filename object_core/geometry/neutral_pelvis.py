# SPDX-License-Identifier: GPL-3.0-or-later
"""Recipe-driven patch-and-stitch pelvis experiment.

The construction below deliberately avoids stacked anatomical rings.  A recipe
places generic control rows on front and rear surfaces; rectangular patches are
then stitched through shared vertices.  Human meaning lives in the recipe data,
not in the patch helpers.
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
    """Generic bowed boundary curve used by recipes."""
    result = []
    for i in range(steps + 1):
        t = i / steps
        q = 4.0 * t * (1.0 - t)
        p = _lerp(a, b, t)
        result.append(tuple(p[j] + bulge[j] * q for j in range(3)))
    return result


def _patch(vertices, faces, cache, top, bottom, bow=(0.0, 0.0, 0.0), rows=3):
    """Stitch two equal boundary curves with shared, optionally bowed rows."""
    grid = []
    for r in range(rows + 1):
        t = r / rows
        q = 4.0 * t * (1.0 - t)
        row = []
        for a, b in zip(top, bottom):
            p = _lerp(a, b, t)
            p = tuple(p[j] + bow[j] * q for j in range(3))
            row.append(_add_vertex(vertices, cache, p))
        grid.append(row)
    for r in range(rows):
        for c in range(len(top) - 1):
            faces.append((grid[r][c], grid[r][c + 1], grid[r + 1][c + 1], grid[r + 1][c]))
    return tuple(grid[0]), tuple(grid[-1])


def generate_neutral_pelvis(shape=None):
    p = shape or NeutralPelvisShape()
    w, d, h = p.width, p.depth, p.height
    vertices, faces, cache = [], [], {}

    # Recipe landmarks.  These names describe positions, not anatomy; the patch
    # engine above is reusable for unrelated object recipes.
    x0 = p.thigh_spacing * .5
    x1 = x0 + p.thigh_opening_width
    x2 = w * .52
    z_top, z_mid, z_split, z_out = h * .50, h * .02, -h * .27, -h * .55
    yf_top, yr_top = p.waist_depth * .50, -p.waist_depth * .50
    yf_mid, yr_mid = d * .50, -d * (.50 + .055 * p.glute_projection)
    yf_low, yr_low = d * .39, -d * (.45 + .035 * p.glute_projection)
    yf_out, yr_out = p.thigh_opening_depth * .50, -p.thigh_opening_depth * .50

    # Five-point curves give four patch columns per half. Mirroring these curves
    # produces the opposite half while preserving a shared center seam.
    def half_curve(z, y, inner, outer, front=True):
        bulge = (0.0, (0.35 if front else -0.55) * p.hip_fullness, 0.0)
        return _curve((inner, y, z), (outer, y * .84, z), bulge=bulge, steps=4)

    for sign in (1.0, -1.0):
        # Front and rear are independent surface regions sharing their side and
        # center boundaries with adjacent patches through the vertex cache.
        top_f = half_curve(z_top, yf_top, 0.0, sign * p.waist_width * .50, True)
        mid_f = half_curve(z_mid, yf_mid, 0.0, sign * x2, True)
        split_f = half_curve(z_split, yf_low, sign * x0, sign * x1, True)
        out_f = half_curve(z_out, yf_out, sign * x0, sign * x1, True)

        top_r = half_curve(z_top, yr_top, 0.0, sign * p.waist_width * .50, False)
        mid_r = half_curve(z_mid, yr_mid, 0.0, sign * x2, False)
        split_r = half_curve(z_split, yr_low, sign * x0, sign * x1, False)
        out_r = half_curve(z_out, yr_out, sign * x0, sign * x1, False)

        _patch(vertices, faces, cache, top_f, mid_f, bow=(sign * w * .018, 0.0, 0.0), rows=2)
        _patch(vertices, faces, cache, mid_f, split_f, bow=(sign * w * .028, 0.0, -h * .025), rows=3)
        _patch(vertices, faces, cache, split_f, out_f, bow=(0.0, -d * .025, 0.0), rows=2)
        _patch(vertices, faces, cache, top_r, mid_r, bow=(sign * w * .018, -d * .035, 0.0), rows=2)
        _patch(vertices, faces, cache, mid_r, split_r, bow=(sign * w * .030, -d * .050, -h * .020), rows=3)
        _patch(vertices, faces, cache, split_r, out_r, bow=(0.0, -d * .025, 0.0), rows=2)

        # Lateral region: stitch front to rear with deliberately rounded depth.
        for af, ar, bf, br in ((top_f, top_r, mid_f, mid_r),
                               (mid_f, mid_r, split_f, split_r),
                               (split_f, split_r, out_f, out_r)):
            front_edge = [af[-1], bf[-1]]
            rear_edge = [ar[-1], br[-1]]
            _patch(vertices, faces, cache, front_edge, rear_edge,
                   bow=(sign * w * .035, -d * .02, 0.0), rows=4)

        # Inner outlet wall is another generic patch, not a generated tube.
        _patch(vertices, faces, cache,
               [split_f[0], out_f[0]], [split_r[0], out_r[0]],
               bow=(-sign * p.crotch_width * .10, 0.0, -h * .035), rows=4)

    # Center front/rear regions stitch the two mirrored halves above the split.
    center_top_f = _curve((0.0, yf_top, z_top), (0.0, yf_mid, z_mid), steps=4)
    center_top_r = _curve((0.0, yr_top, z_top), (0.0, yr_mid, z_mid), steps=4)
    _patch(vertices, faces, cache, center_top_f, center_top_r, bow=(0.0, 0.0, h * .015), rows=4)

    # Lower center saddle: a narrow patch only between the two outlet roots.
    lf = _curve((-x0, yf_low, z_split), (-x0, yr_low, z_split), bulge=(0, 0, -h*.055), steps=4)
    rf = _curve((x0, yf_low, z_split), (x0, yr_low, z_split), bulge=(0, 0, -h*.055), steps=4)
    _patch(vertices, faces, cache, lf, rf, bow=(0.0, 0.0, -h * .025), rows=3)

    # The experiment currently exposes geometric edge sets rather than assuming
    # that every attachment must itself have been generated as a ring.
    torso = tuple(_add_vertex(vertices, cache, q) for q in
                  _curve((-p.waist_width*.5, yf_top, z_top),
                         (p.waist_width*.5, yf_top, z_top), steps=15))
    left_thigh = tuple(_add_vertex(vertices, cache, q) for q in
                       _curve((x0, yf_out, z_out), (x1, yf_out, z_out), steps=15))
    right_thigh = tuple(_add_vertex(vertices, cache, q) for q in
                        _curve((-x1, yf_out, z_out), (-x0, yf_out, z_out), steps=15))
    boundaries = {"torso": torso, "left_thigh": left_thigh, "right_thigh": right_thigh}
    return tuple(vertices), tuple(tuple(reversed(f)) for f in faces), boundaries
