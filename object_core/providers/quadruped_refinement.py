# SPDX-License-Identifier: GPL-3.0-or-later
"""Portable canine surface subdivision with authored-region propagation.

The control cage is an intermediate construction result, never another provider.
Refinement rejects open/non-manifold or inconsistently wound cages.
"""
from dataclasses import replace
from ..models import MeshPart, ObjectMesh


def _mean(points):
    points = tuple(points)
    return tuple(sum(p[k] for p in points) / len(points) for k in range(3))


def _densify_paw_cages(mesh, anatomy):
    """Split terminal paw quads before smoothing, with conforming transitions.

    Cage limb ownership ends with two eight-vertex rings and the cap center.
    Split-edge midpoints are also inserted into adjacent unsplit polygons; the
    normal subdivision pass then produces quads with no hanging seam vertices.
    """
    part = mesh.parts[0]
    selected = set()
    for region in anatomy.regions:
        if region.name.startswith('leg.'):
            terminal = set(region.vertex_indices[-17:])
            selected.update(i for i, face in enumerate(part.faces) if set(face) <= terminal)
    return _split_cage_faces(mesh, anatomy, selected)


def _split_cage_faces(mesh, anatomy, selected, *, smooth=False):
    """Conforming local refinement with source-based region propagation."""
    part = mesh.parts[0]
    edges = sorted({tuple(sorted((a, b))) for i in selected
                    for a, b in zip(part.faces[i], part.faces[i][1:] + part.faces[i][:1])})
    vertices = list(part.vertices)
    sources = [(i,) for i in range(len(vertices))]
    face_points = [_mean(part.vertices[i] for i in f) for f in part.faces]
    edge_faces, vertex_faces, neighbors = {}, {}, {}
    if smooth:
        for fi, face in enumerate(part.faces):
            for a, b in zip(face, face[1:] + face[:1]):
                edge_faces.setdefault(tuple(sorted((a,b))), []).append(fi)
                vertex_faces.setdefault(a, []).append(fi)
                neighbors.setdefault(a, set()).update((b,))
                neighbors.setdefault(b, set()).update((a,))
        for i, adjacent in vertex_faces.items():
            if set(adjacent) <= selected:
                n = len(neighbors[i])
                f = _mean(face_points[j] for j in adjacent)
                r = _mean(_mean((part.vertices[i], part.vertices[j])) for j in sorted(neighbors[i]))
                vertices[i] = tuple((f[k]+2*r[k]+(n-3)*part.vertices[i][k])/n for k in range(3))
    midpoints = {}
    for edge in edges:
        midpoints[edge] = len(vertices)
        adjacent = edge_faces.get(edge, ())
        vertices.append(_mean(tuple(part.vertices[i] for i in edge)
                             + tuple(face_points[j] for j in adjacent))
                        if smooth and len(adjacent) == 2 and set(adjacent) <= selected
                        else _mean(part.vertices[i] for i in edge))
        sources.append(edge)
    faces = []
    for fi, face in enumerate(part.faces):
        if fi in selected:
            center = len(vertices)
            vertices.append(_mean(part.vertices[i] for i in face))
            sources.append(face)
            for i, a in enumerate(face):
                b, previous = face[(i + 1) % len(face)], face[i - 1]
                faces.append((a, midpoints[tuple(sorted((a, b)))], center,
                              midpoints[tuple(sorted((previous, a)))]))
        else:
            expanded = []
            for a, b in zip(face, face[1:] + face[:1]):
                expanded.append(a)
                mid = midpoints.get(tuple(sorted((a, b))))
                if mid is not None:
                    expanded.append(mid)
            faces.append(tuple(expanded))
    regions = []
    for region in anatomy.regions:
        owned = set(region.vertex_indices)
        regions.append(replace(region, vertex_indices=tuple(
            i for i, source in enumerate(sources) if all(j in owned for j in source))))
    # Propagate every split boundary edge as well as face/region ownership.
    connections = tuple(replace(c, boundaries=tuple(tuple(
        j for a, b in zip(loop, loop[1:] + loop[:1])
        for j in ((a, midpoints[tuple(sorted((a, b)))])
                  if tuple(sorted((a, b))) in midpoints else (a,)))
        for loop in c.boundaries)) for c in anatomy.connections)
    result = ObjectMesh((MeshPart(part.name, tuple(vertices), tuple(faces)),))
    resolved = replace(anatomy, regions=tuple(regions), connections=connections)
    resolved.validate_mesh(result)
    return result, resolved


def refine_canine_surface(mesh, anatomy, levels=2):
    mesh, anatomy = _densify_paw_cages(mesh, anatomy)
    vertices, faces = mesh.parts[0].vertices, mesh.parts[0].faces
    regions = {r.name: set(r.vertex_indices) for r in anatomy.regions}
    boundaries = [c.boundaries for c in anatomy.connections]
    for level in range(levels):
        if level == levels - 1:
            # Refine an already smoothed head so detail does not lock the
            # original octagonal cage into a faceted facial silhouette.
            mesh = ObjectMesh((MeshPart(mesh.parts[0].name, vertices, faces),))
            anatomy = replace(anatomy,
                regions=tuple(replace(r, vertex_indices=tuple(sorted(regions[r.name]))) for r in anatomy.regions),
                connections=tuple(replace(c, boundaries=b) for c, b in zip(anatomy.connections, boundaries)))
            mesh, anatomy = _densify_face(mesh, anatomy)
            vertices, faces = mesh.parts[0].vertices, mesh.parts[0].faces
            regions = {r.name: set(r.vertex_indices) for r in anatomy.regions}
            boundaries = [c.boundaries for c in anatomy.connections]
        edge_faces, neighbors, vertex_faces = {}, [set() for v in vertices], [[] for v in vertices]
        directed = set()
        for fi, face in enumerate(faces):
            for i, a in enumerate(face):
                b = face[(i + 1) % len(face)]
                if (a, b) in directed:
                    raise ValueError('Canine cage has inconsistent winding')
                directed.add((a, b))
                edge_faces.setdefault(tuple(sorted((a, b))), []).append(fi)
                neighbors[a].add(b)
                vertex_faces[a].append(fi)
        if any(len(adjacent) != 2 for adjacent in edge_faces.values()):
            raise ValueError('Canine refinement requires a closed manifold cage')
        face_points = [_mean(vertices[i] for i in face) for face in faces]
        updated = []
        for i, point in enumerate(vertices):
            n = len(neighbors[i])
            if n < 3 or len(vertex_faces[i]) != n:
                raise ValueError('Canine cage has a non-manifold vertex')
            f = _mean(face_points[j] for j in vertex_faces[i])
            r = _mean(_mean((point, vertices[j])) for j in sorted(neighbors[i]))
            updated.append(tuple((f[k] + 2*r[k] + (n-3)*point[k]) / n for k in range(3)))
        edge_indices = {}
        sources = [(i,) for i in range(len(vertices))]
        for edge, adjacent in sorted(edge_faces.items()):
            edge_indices[edge] = len(updated)
            updated.append(_mean((vertices[edge[0]], vertices[edge[1]],
                                  face_points[adjacent[0]], face_points[adjacent[1]])))
            sources.append(edge)
        face_start = len(updated)
        updated.extend(face_points)
        sources.extend(faces)
        refined = []
        for fi, face in enumerate(faces):
            for i, vertex in enumerate(face):
                nxt, prev = face[(i+1) % len(face)], face[i-1]
                refined.append((vertex, edge_indices[tuple(sorted((vertex, nxt)))],
                                face_start + fi, edge_indices[tuple(sorted((prev, vertex)))]))
        regions = {name: {i for i, source in enumerate(sources) if all(j in owned for j in source)}
                   for name, owned in regions.items()}
        boundaries = [tuple(tuple(j for i, a in enumerate(loop)
                                  for j in (a, edge_indices[tuple(sorted((a, loop[(i+1) % len(loop)])))]))
                            for loop in pair) for pair in boundaries]
        vertices, faces = tuple(updated), tuple(refined)
    # UVs are projected by the sole construction wrapper after refinement.
    result = ObjectMesh((MeshPart(mesh.parts[0].name, vertices, faces),))
    resolved = replace(anatomy,
        regions=tuple(replace(r, vertex_indices=tuple(sorted(regions[r.name]))) for r in anatomy.regions),
        connections=tuple(replace(c, boundaries=b) for c, b in zip(anatomy.connections, boundaries)))
    resolved.validate_mesh(result)
    return result, resolved


def _densify_face(mesh, anatomy):
    # Facial relief needs local resolution, without raising global ring counts
    # with matching subdivision of the authored ear attachment boundaries.
    for _ in range(2):
        regions = {r.name: set(r.vertex_indices) for r in anatomy.regions}
        facial = regions['head'] - regions['ear.left'] - regions['ear.right']
        selected = {i for i, face in enumerate(mesh.parts[0].faces)
                    if set(face) <= facial}
        mesh, anatomy = _split_cage_faces(mesh, anatomy, selected, smooth=True)
    return mesh, anatomy
