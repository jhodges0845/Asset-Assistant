# SPDX-License-Identifier: GPL-3.0-or-later
"""Shared-edge patch -> regional sculpt -> smooth neutral-pelvis experiment."""
from dataclasses import dataclass

from .patch_surface import (
    PatchNetwork,
    brush,
    curve_points,
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
    outer = gap + p.thigh_opening_width
    level_z = (h * 0.50, h * 0.30, h * 0.05, -h * 0.20, -h * 0.55)
    half_width = (p.waist_width * 0.47, w * 0.485, w * 0.515)
    front_y = (p.waist_depth * 0.46, d * 0.49, d * 0.505, d * 0.405)
    rear_y = (
        -p.waist_depth * 0.46,
        -d * (0.50 + 0.020 * p.glute_projection),
        -d * (0.515 + 0.060 * p.glute_projection),
        -d * (0.455 + 0.050 * p.glute_projection),
    )
    net = PatchNetwork()
    upper = {}

    # The large mass is four-sided patchwork, not rings.  Each front/rear level
    # is split at the centre and joined to explicit depth boundaries at the sides.
    for level, (z, span) in enumerate(zip(level_z[:3], half_width)):
        left_x = (-span, -span * 0.52, 0.0)
        right_x = (0.0, span * 0.52, span)
        left_z = tuple(z - h * 0.030 * (abs(x) / span) ** 1.7 for x in left_x)
        right_z = tuple(z - h * 0.030 * (abs(x) / span) ** 1.7 for x in right_x)
        for side_name, y, bulge in (
            ("front", front_y[level], d * (0.008 + 0.004 * level)),
            ("rear", rear_y[level], -d * (0.012 + 0.010 * level) * p.glute_projection),
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
                (-w * 0.020, 0.0, -h * 0.005),
            ),
        )
        net.boundary(
            f"side.{level}.right",
            curve_points(
                net.vertices[upper[f"front.{level}.right"][-1]],
                net.vertices[upper[f"rear.{level}.right"][-1]],
                6,
                (w * 0.020, 0.0, -h * 0.005),
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
                depth_push = d * (0.020 if side_name == "front" else -0.035)
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
            (0.0, d * 0.025, -h * 0.010),
        )
        net.patch(
            f"front.{level}.right",
            upper[f"front.{level}.right"],
            f"vertical.front.{level}.right",
            upper[f"front.{level + 1}.right"],
            f"vertical.front.{level}.center",
            (0.0, d * 0.025, -h * 0.010),
        )
        net.patch(
            f"rear.{level}.left",
            upper[f"rear.{level}.left"],
            f"vertical.rear.{level}.center",
            upper[f"rear.{level + 1}.left"],
            f"vertical.rear.{level}.left",
            (0.0, -d * 0.060 * p.glute_projection, -h * 0.010),
        )
        net.patch(
            f"rear.{level}.right",
            upper[f"rear.{level}.right"],
            f"vertical.rear.{level}.right",
            upper[f"rear.{level + 1}.right"],
            f"vertical.rear.{level}.center",
            (0.0, -d * 0.060 * p.glute_projection, -h * 0.010),
        )
        net.patch(
            f"side.{level}.left",
            f"side.{level}.left",
            f"vertical.rear.{level}.left",
            f"side.{level + 1}.left",
            f"vertical.front.{level}.left",
            (-w * 0.035 * p.hip_fullness, 0.0, -h * 0.010),
        )
        net.patch(
            f"side.{level}.right",
            f"side.{level}.right",
            f"vertical.rear.{level}.right",
            f"side.{level + 1}.right",
            f"vertical.front.{level}.right",
            (w * 0.035 * p.hip_fullness, 0.0, -h * 0.010),
        )

    # Split the lower region into two openings around one shared centre spine.
    left_x = (-outer, -(outer + gap) * 0.5, -gap)
    right_x = (gap, (outer + gap) * 0.5, outer)
    inner_z = level_z[3] + h * 0.070
    left_root_z = (level_z[3] - h * 0.015, level_z[3] + h * 0.015, inner_z)
    right_root_z = tuple(reversed(left_root_z))
    root = {}
    for side_name, y, z_offset, bulge in (
        ("front", front_y[3], 0.0, d * 0.006),
        ("rear", rear_y[3], -h * 0.018, -d * 0.015),
    ):
        root[f"{side_name}.left"] = net.boundary(
            f"root.{side_name}.left",
            _crossline(left_x, y, tuple(z + z_offset for z in left_root_z), bulge),
        )
        root[f"{side_name}.right"] = net.boundary(
            f"root.{side_name}.right",
            _crossline(right_x, y, tuple(z + z_offset for z in right_root_z), bulge),
        )

    net.boundary(
        "root.side.left",
        curve_points(net.vertices[root["front.left"][0]], net.vertices[root["rear.left"][0]], 6, (-w * 0.040, 0.0, -h * 0.010)),
    )
    net.boundary(
        "root.side.right",
        curve_points(net.vertices[root["front.right"][-1]], net.vertices[root["rear.right"][-1]], 6, (w * 0.040, 0.0, -h * 0.010)),
    )
    net.boundary(
        "root.inner.left",
        curve_points(net.vertices[root["front.left"][-1]], net.vertices[root["rear.left"][-1]], 6, (p.crotch_width * 0.060, 0.0, h * 0.020)),
    )
    net.boundary(
        "root.inner.right",
        curve_points(net.vertices[root["front.right"][0]], net.vertices[root["rear.right"][0]], 6, (-p.crotch_width * 0.060, 0.0, h * 0.020)),
    )
    front_center = upper["front.2.left"][-1]
    rear_center = upper["rear.2.left"][-1]
    net.boundary(
        "center.spine",
        curve_points(net.vertices[front_center], net.vertices[rear_center], 6, (0.0, 0.0, h * 0.055)),
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
                curve_points(net.vertices[top_outer], net.vertices[bottom_outer], 4, (sign * w * 0.025, 0.0, -h * 0.010)),
            )
            transition[f"{side_name}.{half_name}.inner"] = net.boundary(
                f"transition.{side_name}.{half_name}.inner",
                curve_points(net.vertices[top_inner], net.vertices[bottom_inner], 4, (-sign * p.crotch_width * 0.030, 0.0, h * 0.020)),
            )

    for side_name, depth_push in (("front", d * 0.030), ("rear", -d * 0.060)):
        net.patch(
            f"transition.{side_name}.left",
            upper[f"{side_name}.2.left"],
            transition[f"{side_name}.left.inner"],
            root[f"{side_name}.left"],
            transition[f"{side_name}.left.outer"],
            (-w * 0.045, depth_push, -h * 0.015),
        )
        net.patch(
            f"transition.{side_name}.right",
            upper[f"{side_name}.2.right"],
            transition[f"{side_name}.right.outer"],
            root[f"{side_name}.right"],
            transition[f"{side_name}.right.inner"],
            (w * 0.045, depth_push, -h * 0.015),
        )

    net.patch(
        "transition.side.left",
        "side.2.left",
        transition["rear.left.outer"],
        "root.side.left",
        transition["front.left.outer"],
        (-w * 0.040, 0.0, -h * 0.015),
    )
    net.patch(
        "transition.side.right",
        "side.2.right",
        transition["rear.right.outer"],
        "root.side.right",
        transition["front.right.outer"],
        (w * 0.040, 0.0, -h * 0.015),
    )
    net.patch(
        "transition.inner.left",
        "center.spine",
        transition["rear.left.inner"],
        "root.inner.left",
        transition["front.left.inner"],
        (-p.crotch_width * 0.080, 0.0, h * 0.010),
    )
    net.patch(
        "transition.inner.right",
        "center.spine",
        transition["rear.right.inner"],
        "root.inner.right",
        transition["front.right.inner"],
        (p.crotch_width * 0.080, 0.0, h * 0.010),
    )

    # Continue each opening with the same four-sided construction so the inner,
    # outer, front and rear surfaces are all longitudinal patch regions.
    outlet = {}
    outlet_z = (level_z[4],) * 3
    for side_name, y in (("front", p.thigh_opening_depth * 0.5), ("rear", -p.thigh_opening_depth * 0.5)):
        outlet[f"{side_name}.left"] = net.boundary(
            f"outlet.{side_name}.left", _crossline(left_x, y, outlet_z)
        )
        outlet[f"{side_name}.right"] = net.boundary(
            f"outlet.{side_name}.right", _crossline(right_x, y, outlet_z)
        )
    net.boundary("outlet.side.left", curve_points(net.vertices[outlet["front.left"][0]], net.vertices[outlet["rear.left"][0]], 6))
    net.boundary("outlet.side.right", curve_points(net.vertices[outlet["front.right"][-1]], net.vertices[outlet["rear.right"][-1]], 6))
    net.boundary("outlet.inner.left", curve_points(net.vertices[outlet["front.left"][-1]], net.vertices[outlet["rear.left"][-1]], 6))
    net.boundary("outlet.inner.right", curve_points(net.vertices[outlet["front.right"][0]], net.vertices[outlet["rear.right"][0]], 6))

    descent = {}
    for side_name in ("front", "rear"):
        for half_name in ("left", "right"):
            sign = -1.0 if half_name == "left" else 1.0
            root_edge = root[f"{side_name}.{half_name}"]
            outlet_edge = outlet[f"{side_name}.{half_name}"]
            root_outer = root_edge[0] if half_name == "left" else root_edge[-1]
            root_inner = root_edge[-1] if half_name == "left" else root_edge[0]
            outlet_outer = outlet_edge[0] if half_name == "left" else outlet_edge[-1]
            outlet_inner = outlet_edge[-1] if half_name == "left" else outlet_edge[0]
            descent[f"{side_name}.{half_name}.outer"] = net.boundary(
                f"descent.{side_name}.{half_name}.outer",
                curve_points(net.vertices[root_outer], net.vertices[outlet_outer], 5, (sign * w * 0.015, 0.0, 0.0)),
            )
            descent[f"{side_name}.{half_name}.inner"] = net.boundary(
                f"descent.{side_name}.{half_name}.inner",
                curve_points(net.vertices[root_inner], net.vertices[outlet_inner], 5, (-sign * p.crotch_width * 0.025, 0.0, h * 0.010)),
            )

    for side_name, depth_push in (("front", d * 0.020), ("rear", -d * 0.025)):
        net.patch(
            f"descent.{side_name}.left",
            root[f"{side_name}.left"],
            descent[f"{side_name}.left.inner"],
            outlet[f"{side_name}.left"],
            descent[f"{side_name}.left.outer"],
            (-w * 0.015, depth_push, h * 0.010),
        )
        net.patch(
            f"descent.{side_name}.right",
            root[f"{side_name}.right"],
            descent[f"{side_name}.right.outer"],
            outlet[f"{side_name}.right"],
            descent[f"{side_name}.right.inner"],
            (w * 0.015, depth_push, h * 0.010),
        )

    net.patch("descent.side.left", "root.side.left", descent["rear.left.outer"], "outlet.side.left", descent["front.left.outer"], (-w * 0.020, 0.0, 0.0))
    net.patch("descent.side.right", "root.side.right", descent["rear.right.outer"], "outlet.side.right", descent["front.right.outer"], (w * 0.020, 0.0, 0.0))
    net.patch("descent.inner.left", "root.inner.left", descent["rear.left.inner"], "outlet.inner.left", descent["front.left.inner"], (p.crotch_width * 0.040, 0.0, h * 0.015))
    net.patch("descent.inner.right", "root.inner.right", descent["rear.right.inner"], "outlet.inner.right", descent["front.right.inner"], (-p.crotch_width * 0.040, 0.0, h * 0.015))

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
        (("outlet.front.left", False), ("outlet.inner.left", False), ("outlet.rear.left", True), ("outlet.side.left", True))
    )
    right = net.ordered_loop(
        (("outlet.front.right", False), ("outlet.side.right", False), ("outlet.rear.right", True), ("outlet.inner.right", True))
    )
    return net, torso, left, right


def generate_neutral_pelvis(shape=None):
    p = shape or NeutralPelvisShape()
    net, torso, left, right = _build_network(p)
    net.faces = list(orient_faces_consistently(net.faces))

    # SCULPT: region selection is based on authored patch membership rather than
    # global coordinate-only brushes.  The engine remains generic; this recipe
    # decides which connected surface regions receive which operations.
    upper_side = net.region_vertices(("side.0.left", "side.1.left", "transition.side.left"))
    upper_side_r = net.region_vertices(("side.0.right", "side.1.right", "transition.side.right"))
    rear_regions = net.region_vertices(
        (
            "rear.0.left", "rear.0.right", "rear.1.left", "rear.1.right",
            "transition.rear.left", "transition.rear.right",
        )
    )
    inner_regions = net.region_vertices(("transition.inner.left", "transition.inner.right", "descent.inner.left", "descent.inner.right"))
    transition_regions = net.region_vertices(
        (
            "transition.front.left", "transition.front.right", "transition.rear.left", "transition.rear.right",
            "transition.side.left", "transition.side.right", "transition.inner.left", "transition.inner.right",
        )
    )

    brush(net.vertices, upper_side, (-p.width * 0.43, 0.0, p.height * 0.04), p.width * 0.34, (-p.width * 0.032, 0.0, p.height * 0.018))
    brush(net.vertices, upper_side_r, (p.width * 0.43, 0.0, p.height * 0.04), p.width * 0.34, (p.width * 0.032, 0.0, p.height * 0.018))
    brush(net.vertices, rear_regions, (0.0, -p.depth * 0.47, 0.0), p.depth * 0.72, (0.0, -p.depth * 0.080 * p.glute_projection, -p.height * 0.008))
    brush(net.vertices, inner_regions, (0.0, 0.0, -p.height * 0.17), p.width * 0.30, (0.0, 0.0, p.height * 0.040))
    normals = vertex_normals(net.vertices, net.faces)
    brush(net.vertices, transition_regions, (0.0, 0.0, -p.height * 0.02), p.width * 0.46, normal_amount=p.width * 0.010, normals=normals)

    locked = set(torso) | set(left) | set(right)
    relax(net.vertices, net.faces, range(len(net.vertices)), locked=locked, strength=0.085, iterations=3)
    net.faces = list(orient_faces_consistently(net.faces))
    return (
        tuple(net.vertices),
        tuple(net.faces),
        {"torso": torso, "left_thigh": left, "right_thigh": right},
    )
