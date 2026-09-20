# SPDX-License-Identifier: GPL-3.0-or-later
"""Curved-landmark pelvis experiment built on the preserved landmark baseline.

The topology, semantic landmarks, regional sculpt, and attachment loops are kept
identical to the previous experiment.  The only construction change is that
selected internal landmark-to-landmark boundaries are refit as single cubic
Bezier arcs before sculpting.  Endpoints never move, so landmarks remain exact.
"""
from .landmark_curves import fit_landmark_arc
from .neutral_pelvis_landmark_baseline import (
    NeutralPelvisShape,
    _build_network,
    semantic_controls,
)
from .patch_surface import (
    brush,
    fair_boundaries,
    orient_faces_consistently,
    relax,
    vertex_normals,
)


def _is_curved_span(name):
    """Return whether an internal boundary should become one smooth arc."""
    return (
        name.startswith("vertical.")
        or name.startswith("transition.")
        or name.startswith("descent.")
        or name in {
            "center.spine",
            "root.side.left",
            "root.side.right",
            "root.inner.left",
            "root.inner.right",
            "side.1.left",
            "side.1.right",
            "side.2.left",
            "side.2.right",
        }
    )


def _curve_landmark_spans(net):
    """Refit interior boundary samples while keeping every landmark endpoint fixed.

    Attachment loops are deliberately excluded.  This makes the experiment
    comparable with the preserved baseline and prevents curvature work from
    changing the torso/thigh interface contract.
    """
    for name, ids in net.boundaries.items():
        if not _is_curved_span(name) or len(ids) < 3:
            continue
        authored = tuple(net.vertices[index] for index in ids)
        curved = fit_landmark_arc(authored)
        for index, point in zip(ids[1:-1], curved[1:-1]):
            net.vertices[index] = point


def generate_neutral_pelvis(shape=None):
    p = shape or NeutralPelvisShape()
    net, torso, left, right = _build_network(p)

    # Preserve the authored bilateral correspondence before any sculpt/fairing
    # operation.  Later operations may visit mirrored vertices in a different
    # order, so coordinate equality alone is not a reliable symmetry contract.
    authored = tuple(net.vertices)
    authored_lookup = {
        (round(x, 6), round(y, 6), round(z, 6)): i
        for i, (x, y, z) in enumerate(authored)
    }
    mirror_pairs = []
    centerline = []
    for i, (x, y, z) in enumerate(authored):
        if abs(x) < 1.0e-6:
            centerline.append(i)
        elif x > 0.0:
            mate = authored_lookup.get((round(-x, 6), round(y, 6), round(z, 6)))
            if mate is not None:
                mirror_pairs.append((mate, i))

    _curve_landmark_spans(net)
    net.faces = list(orient_faces_consistently(net.faces))

    # Keep the baseline regional sculpt unchanged so the visual test isolates
    # the effect of smooth arcs between the same landmarks.
    upper_side_l = net.region_vertices(("side.0.left", "side.1.left", "transition.side.left"))
    upper_side_r = net.region_vertices(("side.0.right", "side.1.right", "transition.side.right"))
    lower_side_l = net.region_vertices(("transition.side.left", "descent.side.left"))
    lower_side_r = net.region_vertices(("transition.side.right", "descent.side.right"))
    rear_regions = net.region_vertices(
        (
            "rear.0.left", "rear.0.right", "rear.1.left", "rear.1.right",
            "transition.rear.left", "transition.rear.right",
            "descent.rear.left", "descent.rear.right",
        )
    )
    front_lower = net.region_vertices(
        (
            "transition.front.left", "transition.front.right",
            "descent.front.left", "descent.front.right",
        )
    )
    inner_left = net.region_vertices(("transition.inner.left", "descent.inner.left"))
    inner_right = net.region_vertices(("transition.inner.right", "descent.inner.right"))
    transition_regions = net.region_vertices(
        (
            "transition.front.left", "transition.front.right",
            "transition.rear.left", "transition.rear.right",
            "transition.side.left", "transition.side.right",
            "transition.inner.left", "transition.inner.right",
        )
    )

    brush(
        net.vertices, upper_side_l,
        (-p.width * 0.43, 0.0, p.height * 0.04),
        p.width * 0.30,
        (-p.width * 0.014, 0.0, p.height * 0.008),
    )
    brush(
        net.vertices, upper_side_r,
        (p.width * 0.43, 0.0, p.height * 0.04),
        p.width * 0.30,
        (p.width * 0.014, 0.0, p.height * 0.008),
    )
    brush(
        net.vertices, rear_regions,
        (0.0, -p.depth * 0.46, -p.height * 0.04),
        p.depth * 0.76,
        (0.0, -p.depth * 0.055 * p.glute_projection, -p.height * 0.012),
    )
    brush(
        net.vertices, front_lower,
        (0.0, p.depth * 0.40, -p.height * 0.12),
        p.depth * 0.58,
        (0.0, -p.depth * 0.018, -p.height * 0.004),
    )
    brush(
        net.vertices, inner_left,
        (-p.crotch_width * 0.34, 0.0, -p.height * 0.18),
        p.width * 0.25,
        (-p.crotch_width * 0.030, 0.0, -p.height * 0.016),
    )
    brush(
        net.vertices, inner_right,
        (p.crotch_width * 0.34, 0.0, -p.height * 0.18),
        p.width * 0.25,
        (p.crotch_width * 0.030, 0.0, -p.height * 0.016),
    )
    brush(
        net.vertices, lower_side_l,
        (-p.width * 0.40, 0.0, -p.height * 0.18),
        p.width * 0.27,
        (p.width * 0.008, 0.0, -p.height * 0.010),
    )
    brush(
        net.vertices, lower_side_r,
        (p.width * 0.40, 0.0, -p.height * 0.18),
        p.width * 0.27,
        (-p.width * 0.008, 0.0, -p.height * 0.010),
    )

    # Inflate the transition symmetrically. Averaged polygon normals are
    # sensitive to mirrored face ordering at the sagittal seam, so applying
    # them independently can introduce a small but real left/right drift.
    # Compute the positive-X side, then mirror its displacement onto the
    # coordinate-matched negative-X side.
    normals = vertex_normals(net.vertices, net.faces)
    before_inflate = list(net.vertices)
    positive = tuple(i for i in transition_regions if net.vertices[i][0] > 1.0e-8)
    brush(
        net.vertices,
        positive,
        (0.0, 0.0, -p.height * 0.04),
        p.width * 0.44,
        normal_amount=p.width * 0.0035,
        normals=normals,
    )
    mirror_lookup = {
        (round(-x, 6), round(y, 6), round(z, 6)): i
        for i, (x, y, z) in enumerate(before_inflate)
        if x < -1.0e-8
    }
    for i in positive:
        x0, y0, z0 = before_inflate[i]
        mate = mirror_lookup.get((round(x0, 6), round(y0, 6), round(z0, 6)))
        if mate is None:
            continue
        dx = net.vertices[i][0] - x0
        dy = net.vertices[i][1] - y0
        dz = net.vertices[i][2] - z0
        mx, my, mz = before_inflate[mate]
        net.vertices[mate] = (mx - dx, my + dy, mz + dz)

    locked = set(torso) | set(left) | set(right)

    # Existing seam fairing now acts on the curved spans: it aligns the first
    # patch rows without moving authored landmarks or attachment boundaries.
    fair_boundaries(
        net.vertices,
        net.faces,
        net.boundaries.values(),
        locked=locked,
        strength=0.34,
        iterations=2,
    )
    relax(
        net.vertices,
        net.faces,
        range(len(net.vertices)),
        locked=locked,
        strength=0.055,
        iterations=2,
    )
    net.faces = list(orient_faces_consistently(net.faces))

    # Reconcile each authored mirror pair after all sculpt/fairing passes.
    # Averaging the pair (rather than copying one side) preserves the intended
    # deformation while making bilateral symmetry exact and deterministic.
    for left_i, right_i in mirror_pairs:
        lx, ly, lz = net.vertices[left_i]
        rx, ry, rz = net.vertices[right_i]
        half_x = (abs(lx) + abs(rx)) * 0.5
        y = (ly + ry) * 0.5
        z = (lz + rz) * 0.5
        net.vertices[left_i] = (-half_x, y, z)
        net.vertices[right_i] = (half_x, y, z)
    for i in centerline:
        _, y, z = net.vertices[i]
        net.vertices[i] = (0.0, y, z)
    return (
        tuple(net.vertices),
        tuple(net.faces),
        {"torso": torso, "left_thigh": left, "right_thigh": right},
    )
