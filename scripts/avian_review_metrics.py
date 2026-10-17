# SPDX-License-Identifier: GPL-3.0-or-later
"""Blender surface-crossing diagnostics; not a volumetric clearance proof."""
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from mathutils.geometry import tessellate_polygon


def surface_crossings(vertices, faces):
    """Return non-adjacent intersecting face pairs, excluding shared vertices.

    Tessellate each polygon before querying so warped quads use explicit triangles.
    Adjacent faces are excluded because their authored shared boundary is expected.
    Containment, coplanar contact and intersections within a polygon are not covered.
    """
    triangles, owners = [], []
    for index, face in enumerate(faces):
        points = [Vector(vertices[i]) for i in face]
        for triangle in tessellate_polygon([points]):
            triangles.append(tuple(face[point if isinstance(point, int) else points.index(point)] for point in triangle))
            owners.append(index)
    tree = BVHTree.FromPolygons(vertices, triangles, all_triangles=True, epsilon=0.0)
    pairs = set()
    for a, b in tree.overlap(tree):
        first, second = sorted((owners[a], owners[b]))
        if first != second and not set(faces[first]).intersection(faces[second]):
            pairs.add((first, second))
    return sorted(pairs)


def crossing_details(faces, regions, pairs):
    """Describe face ownership without hiding mixed-region attachment faces.

    Counts are authored vertex membership, not a guessed dominant region. A
    bridge face therefore retains both body and wing labels.
    """
    memberships = [(region.name, set(region.vertex_indices)) for region in regions]
    def describe(index):
        vertices = set(faces[index])
        return dict(face_index=index, vertex_indices=list(faces[index]),
                    regions={name: len(vertices & indices) for name, indices in memberships
                             if vertices & indices})
    return [dict(faces=[describe(first), describe(second)]) for first, second in pairs]
