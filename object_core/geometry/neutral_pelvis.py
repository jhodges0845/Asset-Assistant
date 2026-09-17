# SPDX-License-Identifier: GPL-3.0-or-later
"""Shared-edge patch -> tangent fairing -> regional sculpt pelvis experiment."""
from dataclasses import dataclass

from .patch_surface import (
    PatchNetwork,
    brush,
    curve_points,
    fair_boundaries,
    orient_faces_consistently,
    relax,
    vertex_normals,
)


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


def _crossline(xs, y, zs, bulge=0.0):
    count = len(xs)
    result = []
    for index, (x, z) in enumerate(zip(xs, zs)):
        t = index / (count - 1)
        result.append((x, y + bulge * 4.0 * t * (1.0 - t), z))
    return tuple(result)


def _build_network(p):
    """Author one manifold pair-of-openings surface from explicit shared edges."""
    w, d, h = p.width, p.depth, p.height
    gap = p.thigh_spacing * 0.5
    outlet_outer = gap + p.thigh_opening_width

    # The root saddle is intentionally wider and lower than the outlet gap.
    # That makes the groin a shallow bridge which narrows into two thigh openings,
    # instead of a tall vertical keyhole cut through the lower mass.
    saddle_half = max(gap, p.crotch_width * 0.44)
    root_outer = saddle_half + p.thigh_opening_width * 0.96

    level_z = (h * 0.50, h * 0.30, h * 0.05, -h * 0.20, -h * 0.55)
    half_width = (p.waist_width * 0.47, w * 0.485, w * 0.515)
    front_y = (p.waist_depth * 0.46, d * 0.49, d * 0.505, d * 0.405)
    rear_y = (
        -p.waist_depth * 0.46,
        -d * (0.50 + 0.018 * p.glute_projection),
        -d * (0.515 + 0.050 * p.glute_projection),
        -d * (0.455 + 0.050 * p.glute_projection),
    )
    net = PatchNetwork()
    upper = {}

    # Upper mass: independent front, rear and side patches share explicit edges.
    for level, (z, span) in enumerate(zip(level_z[:3], half_width)):
        left_x = (-span, -span * 0.52, 0.0)
        right_x = (0.0, span * 0.52, span)
        left_z = tuple(z - h * 0.030 * (abs(x) / span) ** 1.7 for x in left_x)
        right_z = tuple(z - h * 0.030 * (abs(x) / span) ** 1.7 for x in right_x)
        for side_name, y, bulge in (
            ("front", front_y[level], d * (0.006 + 0.003 * level)),
            ("rear", rear_y[level], -d * (0.010 + 0.008 * level) * p.glute_projection),
        ):
            upper[f"{side_name}.{level}.left"] = net.boundary(
                f"{side_name}.{level}.left", _crossline(left_x, y, left_z, bulge)
            )
            upper[f"{side_name}.{level}.right"] = net.boundary(
                f"{side_name}.{level}.right", _crossline(right_x, y, right_z, bulge)
            )
        net.boundary(
            f"side.{level}.left",
            curve_points(
                net.vertices[upper[f"front.{level}.left"][0]],
                net.vertices[upper[f"rear.{level}.left"][0]],
                6,
                (-w * 0.014, 0.0, -h * 0.003),
            ),
        )
        net.boundary(
            f"side.{level}.right",
            curve_points(
                net.vertices[upper[f"front.{level}.right"][-1]],
                net.vertices[upper[f"rear.{level}.right"][-1]],
                6,
                (w * 0.014, 0.0, -h * 0.003),
            ),
        )

    for level in (0, 1):
        for side_name in ("front", "rear"):
            for position in ("left", "center", "right"):
                if position == "left":
                    a = upper[f"{side_name}.{level}.left"][0]
                    b = upper[f"{side_name}.{level + 1}.left"][0]
                elif position == "center":
                    a = upper[f"{side_name}.{level}.left"][-1]
                    b = upper[f"{side_name}.{level + 1}.left"][-1]
                else:
                    a = upper[f"{side_name}.{level}.right"][-1]
                    b = upper[f"{side_name}.{level + 1}.right"][-1]
                depth_push = d * (0.014 if side_name == "front" else -0.022)
                net.boundary(
                    f"vertical.{side_name}.{level}.{position}",
                    curve_points(net.vertices[a], net.vertices[b], 4, (0.0, depth_push, 0.0)),
                )

        net.patch(
            f"front.{level}.left",
            upper[f"front.{level}.left"],
            f"vertical.front.{level}.center",
            upper[f"front.{level + 1}.left"],
            f"vertical.front.{level}.left",
            (0.0, d * 0.016, -h * 0.006),
        )
        net.patch(
            f"front.{level}.right",
            upper[f"front.{level}.right"],
            f"vertical.front.{level}.right",
            upper[f"front.{level + 1}.right"],
            f"vertical.front.{level}.center",
            (0.0, d * 0.016, -h * 0.006),
        )
        net.patch(
            f"rear.{level}.left",
            upper[f"rear.{level}.left"],
            f"vertical.rear.{level}.center",
            upper[f"rear.{level + 1}.left"],
            f"vertical.rear.{level}.left",
            (0.0, -d * 0.042 * p.glute_projection, -h * 0.008),
        )
        net.patch(
            f"rear.{level}.right",
            upper[f"rear.{level}.right"],
            f"vertical.rear.{level}.right",
            upper[f"rear.{level + 1}.right"],
            f"vertical.rear.{level}.center",
            (0.0, -d * 0.042 * p.glute_projection, -h * 0.008),
        )
        net.patch(
            f"side.{level}.left",
            f"side.{level}.left",
            f"vertical.rear.{level}.left",
            f"side.{level + 1}.left",
            f"vertical.front.{level}.left",
            (-w * 0.022 * p.hip_fullness, 0.0, -h * 0.006),
        )
        net.patch(
            f"side.{level}.right",
            f"side.{level}.right",
            f"vertical.rear.{level}.right",
            f"side.{level + 1}.right",
            f"vertical.front.{level}.right",
            (w * 0.022 * p.hip_fullness, 0.0, -h * 0.006),
        )

    # Lower root is wider at the saddle than at the eventual thigh gap.
    left_root_x = (-root_outer, -(root_outer + saddle_half) * 0.5, -saddle_half)
    right_root_x = (saddle_half, (root_outer + saddle_half) * 0.5, root_outer)
    saddle_z = level_z[3] + h * (0.035 - 0.015 * (p.crotch_drop - 1.0))
    left_root_z = (level_z[3] - h * 0.010, level_z[3] + h * 0.010, saddle_z)
    right_root_z = tuple(reversed(left_root_z))
    root = {}
    for side_name, y, z_offset, bulge in (
        ("front", front_y[3], 0.0, d * 0.004),
        ("rear", rear_y[3], -h * 0.018, -d * 0.012),
    ):
        root[f"{side_name}.left"] = net.boundary(
            f"root.{side_name}.left",
            _crossline(left_root_x, y, tuple(z + z_offset for z in left_root_z), bulge),
        )
        root[f"{side_name}.right"] = net.boundary(
            f"root.{side_name}.right",
            _crossline(right_root_x, y, tuple(z + z_offset for z in right_root_z), bulge),
        )

    net.boundary(
        "root.side.left",
        curve_points(
            net.vertices[root["front.left"][0]],
            net.vertices[root["rear.left"][0]],
            6,
            (-w * 0.024, 0.0, -h * 0.006),
        ),
    )
    net.boundary(
        "root.side.right",
        curve_points(
            net.vertices[root["front.right"][-1]],
            net.vertices[root["rear.right"][-1]],
            6,
            (w * 0.024, 0.0, -h * 0.006),
        ),
    )
    net.boundary(
        "root.inner.left",
        curve_points(
            net.vertices[root["front.left"][-1]],
            net.vertices[root["rear.left"][-1]],
            6,
            (p.crotch_width * 0.035, 0.0, h * 0.008),
        ),
    )
    net.boundary(
        "root.inner.right",
        curve_points(
            net.vertices[root["front.right"][0]],
            net.vertices[root["rear.right"][0]],
            6,
            (-p.crotch_width * 0.035, 0.0, h * 0.008),
        ),
    )
    front_center = upper["front.2.left"][-1]
    rear_center = upper["rear.2.left"][-1]
    net.boundary(
        "center.spine",
        curve_points(
            net.vertices[front_center],
            net.vertices[rear_center],
            6,
            (0.0, 0.0, h * 0.025),
        ),
    )

    transition = {}
    for side_name in ("front", "rear"):
        for half_name in ("left", "right"):
            top = upper[f"{side_name}.2.{half_name}"]
            bottom = root[f"{side_name}.{half_name}"]
            sign = -1.0 if half_name == "left" else 1.0
            top_outer = top[0] if half_name == "left" else top[-1]
            top_inner = top[-1] if half_name == "left" else top[0]
            bottom_outer = bottom[0] if half_name == "left" else bottom[-1]
            bottom_inner = bottom[-1] if half_name == "left" else bottom[0]
            transition[f"{side_name}.{half_name}.outer"] = net.boundary(
                f"transition.{side_name}.{half_name}.outer",
                curve_points(
                    net.vertices[top_outer],
                    net.vertices[bottom_outer],
                    4,
                    (sign * w * 0.014, 0.0, -h * 0.004),
                ),
            )
            transition[f"{side_name}.{half_name}.inner"] = net.boundary(
                f"transition.{side_name}.{half_name}.inner",
                curve_points(
                    net.vertices[top_inner],
                    net.vertices[bottom_inner],
                    4,
                    (-sign * p.crotch_width * 0.015, 0.0, h * 0.008),
                ),
            )

    for side_name, depth_push in (("front", d * 0.015), ("rear", -d * 0.028)):
        net.patch(
            f"transition.{side_name}.left",
            upper[f"{side_name}.2.left"],
            transition[f"{side_name}.left.inner"],
            root[f"{side_name}.left"],
            transition[f"{side_name}.left.outer"],
            (-w * 0.020, depth_push, -h * 0.006),
        )
        net.patch(
            f"transition.{side_name}.right",
            upper[f"{side_name}.2.right"],
            transition[f"{side_name}.right.outer"],
            root[f"{side_name}.right"],
            transition[f"{side_name}.right.inner"],
            (w * 0.020, depth_push, -h * 0.006),
        )

    net.patch(
        "transition.side.left",
        "side.2.left",
        transition["rear.left.outer"],
        "root.side.left",
        transition["front.left.outer"],
        (-w * 0.018, 0.0, -h * 0.006),
    )
    net.patch(
        "transition.side.right",
        "side.2.right",
        transition["rear.right.outer"],
        "root.side.right",
        transition["front.right.outer"],
        (w * 0.018, 0.0, -h * 0.006),
    )
    net.patch(
        "transition.inner.left",
        "center.spine",
        transition["rear.left.inner"],
        "root.inner.left",
        transition["front.left.inner"],
        (-p.crotch_width * 0.050, 0.0, -h * 0.004),
    )
    net.patch(
        "transition.inner.right",
        "center.spine",
        transition["rear.right.inner"],
        "root.inner.right",
        transition["front.right.inner"],
        (p.crotch_width * 0.050, 0.0, -h * 0.004),
    )

    # Outlets retain the requested spacing while the root saddle starts wider.
    left_outlet_x = (-outlet_outer, -(outlet_outer + gap) * 0.5, -gap)
    right_outlet_x = (gap, (outlet_outer + gap) * 0.5, outlet_outer)
    outlet = {}
    outlet_z = (level_z[4],) * 3
    for side_name, y in (
        ("front", p.thigh_opening_depth * 0.5),
        ("rear", -p.thigh_opening_depth * 0.5),
    ):
        outlet[f"{side_name}.left"] = net.boundary(
            f"outlet.{side_name}.left", _crossline(left_outlet_x, y, outlet_z)
        )
        outlet[f"{side_name}.right"] = net.boundary(
            f"outlet.{side_name}.right", _crossline(right_outlet_x, y, outlet_z)
        )
    net.boundary(
        "outlet.side.left",
        curve_points(net.vertices[outlet["front.left"][0]], net.vertices[outlet["rear.left"][0]], 6),
    )
    net.boundary(
        "outlet.side.right",
        curve_points(net.vertices[outlet["front.right"][-1]], net.vertices[outlet["rear.right"][-1]], 6),
    )
    net.boundary(
        "outlet.inner.left",
        curve_points(net.vertices[outlet["front.left"][-1]], net.vertices[outlet["rear.left"][-1]], 6),
    )
    net.boundary(
        "outlet.inner.right",
        curve_points(net.vertices[outlet["front.right"][0]], net.vertices[outlet["rear.right"][0]], 6),
    )

    descent = {}
    for side_name in ("front", "rear"):
        for half_name in ("left", "right"):
            sign = -1.0 if half_name == "left" else 1.0
            root_edge = root[f"{side_name}.{half_name}"]
            outlet_edge = outlet[f"{side_name}.{half_name}"]
            root_outer_id = root_edge[0] if half_name == "left" else root_edge[-1]
            root_inner_id = root_edge[-1] if half_name == "left" else root_edge[0]
            outlet_outer_id = outlet_edge[0] if half_name == "left" else outlet_edge[-1]
            outlet_inner_id = outlet_edge[-1] if half_name == "left" else outlet_edge[0]
            descent[f"{side_name}.{half_name}.outer"] = net.boundary(
                f"descent.{side_name}.{half_name}.outer",
                curve_points(
                    net.vertices[root_outer_id],
                    net.vertices[outlet_outer_id],
                    5,
                    (sign * w * 0.010, 0.0, 0.0),
                ),
            )
            descent[f"{side_name}.{half_name}.inner"] = net.boundary(
                f"descent.{side_name}.{half_name}.inner",
                curve_points(
                    net.vertices[root_inner_id],
                    net.vertices[outlet_inner_id],
                    5,
                    (-sign * p.crotch_width * 0.014, 0.0, h * 0.004),
                ),
            )

    for side_name, depth_push in (("front", d * 0.010), ("rear", -d * 0.018)):
        net.patch(
            f"descent.{side_name}.left",
            root[f"{side_name}.left"],
            descent[f"{side_name}.left.inner"],
            outlet[f"{side_name}.left"],
            descent[f"{side_name}.left.outer"],
            (-w * 0.010, depth_push, h * 0.004),
        )
        net.patch(
            f"descent.{side_name}.right",
            root[f"{side_name}.right"],
            descent[f"{side_name}.right.outer"],
            outlet[f"{side_name}.right"],
            descent[f"{side_name}.right.inner"],
            (w * 0.010, depth_push, h * 0.004),
        )

    net.patch(
        "descent.side.left",
        "root.side.left",
        descent["rear.left.outer"],
        "outlet.side.left",
        descent["front.left.outer"],
        (-w * 0.010, 0.0, 0.0),
    )
    net.patch(
        "descent.side.right",
        "root.side.right",
        descent["rear.right.outer"],
        "outlet.side.right",
        descent["front.right.outer"],
        (w * 0.010, 0.0, 0.0),
    )
    net.patch(
        "descent.inner.left",
        "root.inner.left",
        descent["rear.left.inner"],
        "outlet.inner.left",
        descent["front.left.inner"],
        (p.crotch_width * 0.020, 0.0, h * 0.006),
    )
    net.patch(
        "descent.inner.right",
        "root.inner.right",
        descent["rear.right.inner"],
        "outlet.inner.right",
        descent["front.right.inner"],
        (-p.crotch_width * 0.020, 0.0, h * 0.006),
    )

    torso = net.ordered_loop(
        (
            ("front.0.left", False),
            ("front.0.right", False),
            ("side.0.right", False),
            ("rear.0.right", True),
            ("rear.0.left", True),
            ("side.0.left", True),
        )
    )
    left = net.ordered_loop(
        (
            ("outlet.front.left", False),
            ("outlet.inner.left", False),
            ("outlet.rear.left", True),
            ("outlet.side.left", True),
        )
    )
    right = net.ordered_loop(
        (
            ("outlet.front.right", False),
            ("outlet.side.right", False),
            ("outlet.rear.right", True),
            ("outlet.inner.right", True),
        )
    )
    return net, torso, left, right


def generate_neutral_pelvis(shape=None):
    p = shape or NeutralPelvisShape()
    net, torso, left, right = _build_network(p)
    net.faces = list(orient_faces_consistently(net.faces))

    # Regional sculpt now follows authored surface groups rather than broad global
    # spheres. Front, rear, side and inner-root behavior can therefore diverge.
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
    # Keep the anterior root comparatively flat instead of letting the smoothing
    # stage turn it into the same rounded volume as the rear.
    brush(
        net.vertices, front_lower,
        (0.0, p.depth * 0.40, -p.height * 0.12),
        p.depth * 0.58,
        (0.0, -p.depth * 0.018, -p.height * 0.004),
    )
    # Spread the inner roots laterally and lower them slightly: a shallow saddle,
    # not a tall keyhole. The two mirrored calls preserve bilateral symmetry.
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
    # Let the side root descend into the outlet instead of retaining an upper
    # shelf/scallop at the transition.
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

    normals = vertex_normals(net.vertices, net.faces)
    brush(
        net.vertices,
        transition_regions,
        (0.0, 0.0, -p.height * 0.04),
        p.width * 0.44,
        normal_amount=p.width * 0.0035,
        normals=normals,
    )

    locked = set(torso) | set(left) | set(right)

    # Make shared edges C1-like before global relaxation. Open attachment edges
    # are ignored by the generic fairing operation because they have only one
    # patch side.
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
    return (
        tuple(net.vertices),
        tuple(net.faces),
        {"torso": torso, "left_thigh": left, "right_thigh": right},
    )
