# SPDX-License-Identifier: GPL-3.0-or-later
"""Human-specific limb cross-section refinement."""

from math import cos, pi, sqrt

from ..models.mesh import MeshPart, ObjectMesh
from ..models.proportions import HumanoidProportions
from ..proportions.landmarks import generate_landmarks


_EPSILON = 1e-7
_OCTAGON_CHORD_CORRECTION = 1.0 / cos(pi / 8.0)
_MAX_STATION_DELTA = 0.035
_SEAM_GUARD = 0.055


def _edge_key(first, second):
    return (first, second) if first < second else (second, first)


def _subtract(first, second):
    return tuple(first[index] - second[index] for index in range(3))


def _add(first, second):
    return tuple(first[index] + second[index] for index in range(3))


def _scale(point, amount):
    return tuple(value * amount for value in point)


def _dot(first, second):
    return sum(first[index] * second[index] for index in range(3))


def _length(vector):
    return sqrt(_dot(vector, vector))


def _midpoint(first, second):
    return tuple((first[index] + second[index]) * 0.5 for index in range(len(first)))


def _polyline_projection(point, path):
    """Return closest point, normalized station and distance on a 3D polyline."""
    segment_lengths = [_length(_subtract(path[index + 1], path[index])) for index in range(len(path) - 1)]
    total_length = sum(segment_lengths)
    if total_length <= _EPSILON:
        raise ValueError("limb centerline must have nonzero length")

    best = None
    traversed = 0.0
    for index, segment_length in enumerate(segment_lengths):
        start = path[index]
        end = path[index + 1]
        axis = _subtract(end, start)
        axis_length_sq = _dot(axis, axis)
        amount = 0.0 if axis_length_sq <= _EPSILON else _dot(_subtract(point, start), axis) / axis_length_sq
        amount = max(0.0, min(1.0, amount))
        projection = _add(start, _scale(axis, amount))
        distance = _length(_subtract(point, projection))
        station = (traversed + segment_length * amount) / total_length
        candidate = (distance, station, projection)
        if best is None or candidate[0] < best[0]:
            best = candidate
        traversed += segment_length
    return best[2], best[1], best[0]


def _limb_paths(proportions):
    """Return only the anatomical arm/leg shafts targeted by this slice.

    Hands and feet deliberately remain outside this pass. Their generated forms
    use different proportions and ground/contact constraints, so they need their
    own topology treatment rather than being rounded as extensions of the long
    limb centerlines.
    """
    points = generate_landmarks(proportions)
    result = []
    for side in ("left", "right"):
        shoulder = points["shoulder." + side]
        elbow = points["elbow." + side]
        wrist = points["wrist." + side]
        result.append((
            "arm." + side,
            (shoulder, elbow, wrist),
            max(proportions.upper_arm_thickness_cm, proportions.forearm_thickness_cm) * 0.80,
        ))

        hip = points["hip." + side]
        knee = points["knee." + side]
        ankle = points["ankle." + side]
        result.append((
            "leg." + side,
            (hip, knee, ankle),
            max(proportions.thigh_thickness_cm, proportions.calf_thickness_cm) * 0.80,
        ))
    return tuple(result)


def _edge_limb_projection(first, second, paths):
    """Return centerline data when an edge is a limb-ring chord."""
    best = None
    for name, path, radius_limit in paths:
        first_projection, first_station, first_distance = _polyline_projection(first, path)
        second_projection, second_station, second_distance = _polyline_projection(second, path)
        if first_distance > radius_limit or second_distance > radius_limit:
            continue
        # Keep both attachment and terminal rings unchanged. The support points
        # we add should round the limb shafts, not alter the shoulder/hip seams
        # or overshoot the wrist/ankle endpoints.
        if min(first_station, second_station) <= _SEAM_GUARD:
            continue
        if max(first_station, second_station) >= 1.0 - _SEAM_GUARD:
            continue
        station_delta = abs(first_station - second_station)
        if station_delta > _MAX_STATION_DELTA:
            continue
        score = first_distance + second_distance + station_delta * radius_limit
        if best is None or score < best[0]:
            best = (score, name, path)
    return best


def refine_human_limb_cross_sections(mesh: ObjectMesh, proportions: HumanoidProportions) -> ObjectMesh:
    """Round generated Human arm/leg ring chords without changing branch seams.

    The base Human branches are eight-point elliptical rings. Circumferential
    edges are recognized from their shared station along anatomical upper/lower
    arm and upper/lower leg centerlines. A shared midpoint is inserted and
    radially corrected from the centerline onto the original ellipse.
    Longitudinal edges, torso geometry, hands, feet, and the attachment/terminal
    rings nearest each shoulder/hip and wrist/ankle remain untouched.
    """
    if not isinstance(mesh, ObjectMesh) or len(mesh.parts) != 1:
        raise TypeError("limb refinement expects one generated ObjectMesh part")
    if not isinstance(proportions, HumanoidProportions):
        raise TypeError("proportions must be HumanoidProportions")

    part = mesh.parts[0]
    paths = _limb_paths(proportions)
    selected_edges = {}
    for face in part.faces:
        for index, first_index in enumerate(face):
            second_index = face[(index + 1) % len(face)]
            edge = _edge_key(first_index, second_index)
            if edge in selected_edges:
                continue
            projection = _edge_limb_projection(
                part.vertices[first_index],
                part.vertices[second_index],
                paths,
            )
            if projection is not None:
                selected_edges[edge] = projection[2]

    if not selected_edges:
        return mesh

    vertices = list(part.vertices)
    edge_vertices = {}
    for edge in sorted(selected_edges):
        first_index, second_index = edge
        midpoint = _midpoint(part.vertices[first_index], part.vertices[second_index])
        path = selected_edges[edge]
        center, _station, _distance = _polyline_projection(midpoint, path)
        radial = _subtract(midpoint, center)
        if _length(radial) <= _EPSILON:
            continue
        corrected = _add(center, _scale(radial, _OCTAGON_CHORD_CORRECTION))
        edge_vertices[edge] = len(vertices)
        vertices.append(corrected)

    faces = []
    uvs = []
    for face_index, face in enumerate(part.faces):
        face_uvs = part.uvs[face_index] if part.uvs else ()
        refined_face = []
        refined_uvs = []
        for index, first_index in enumerate(face):
            second_index = face[(index + 1) % len(face)]
            refined_face.append(first_index)
            if part.uvs:
                refined_uvs.append(face_uvs[index])
            midpoint_index = edge_vertices.get(_edge_key(first_index, second_index))
            if midpoint_index is None:
                continue
            refined_face.append(midpoint_index)
            if part.uvs:
                refined_uvs.append(_midpoint(face_uvs[index], face_uvs[(index + 1) % len(face)]))
        faces.append(tuple(refined_face))
        if part.uvs:
            uvs.append(tuple(refined_uvs))

    refined = MeshPart(part.name, tuple(vertices), tuple(faces), tuple(uvs) if part.uvs else ())
    return ObjectMesh((refined,))
