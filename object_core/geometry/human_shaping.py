# SPDX-License-Identifier: GPL-3.0-or-later
"""Human-specific body-control mapping shared by recipe resolution and surface construction."""

def shape_surface_point(point, proportions, reference):
    """Apply existing weight/body-type girth ratios smoothly along height."""
    x, y, z = point
    t = z / proportions.standing_height_cm
    rows = (
        (0.0, "hip"),
        (0.55, "hip"),
        (0.66, "waist"),
        (0.77, "chest"),
        (0.82, "shoulder"),
        (0.90, "head"),
        (1.0, "head"),
    )

    def ratios(name):
        width = name + "_width_cm"
        depth = ("chest" if name == "shoulder" else name) + "_depth_cm"
        return (
            getattr(proportions, width) / getattr(reference, width),
            getattr(proportions, depth) / getattr(reference, depth),
        )

    for (a, first), (b, second) in zip(rows, rows[1:]):
        if t <= b:
            blend = max(0.0, min(1.0, (t - a) / (b - a)))
            blend = blend * blend * (3 - 2 * blend)
            u, v = ratios(first), ratios(second)
            return (
                x * (u[0] + (v[0] - u[0]) * blend),
                y * (u[1] + (v[1] - u[1]) * blend),
                z,
            )
    u = ratios("head")
    return x * u[0], y * u[1], z


def shape_human_surface(neutral, anatomy):
    """Shape the audited neutral topology using one resolved Human recipe."""
    from ..models.mesh import MeshPart, ObjectMesh
    part = neutral.parts[0]
    height_scale = dict(anatomy.parameters)["height_cm"] / 175.0
    vertices = tuple(
        shape_surface_point(tuple(v * height_scale for v in point),
                            anatomy.proportions, anatomy.surface_reference)
        for point in part.vertices
    )
    return ObjectMesh((MeshPart("human", vertices, part.faces, part.uvs),))
