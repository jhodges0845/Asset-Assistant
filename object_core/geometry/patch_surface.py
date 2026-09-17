# SPDX-License-Identifier: GPL-3.0-or-later
"""Generic shared-edge patch-surface construction and sculpt helpers.

A patch boundary is sampled exactly once and then referenced by every adjacent
patch.  Patches therefore share vertex ids along complete edges instead of being
welded later by coordinate coincidence.  The module intentionally contains no
object/anatomy vocabulary; recipes own all semantic meaning.
"""
from collections import defaultdict, deque
from math import sqrt


def lerp(a, b, t):
    return tuple(x + (y - x) * t for x, y in zip(a, b))


def add(a, b):
    return tuple(a[i] + b[i] for i in range(3))


def mul(a, s):
    return tuple(x * s for x in a)


def sub(a, b):
    return tuple(a[i] - b[i] for i in range(3))


def cross(a, b):
    return (
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    )


def normalized(a):
    length = sqrt(sum(x * x for x in a)) or 1.0
    return tuple(x / length for x in a)


def curve_points(a, b, segments, bulge=(0.0, 0.0, 0.0)):
    """Sample a generic bowed boundary from ``a`` to ``b``."""
    if segments < 1:
        raise ValueError("boundary requires at least one segment")
    result = []
    for i in range(segments + 1):
        t = i / segments
        result.append(add(lerp(a, b, t), mul(bulge, 4.0 * t * (1.0 - t))))
    return tuple(result)


class PatchNetwork:
    """Editable quad-patch network whose shared boundaries own shared vertices."""

    def __init__(self):
        self.vertices = []
        self.faces = []
        self.boundaries = {}
        self.regions = {}
        self._point_cache = {}

    def _vertex(self, point):
        key = tuple(round(float(value), 8) for value in point)
        if key not in self._point_cache:
            self._point_cache[key] = len(self.vertices)
            self.vertices.append(tuple(float(value) for value in point))
        return self._point_cache[key]

    def boundary(self, name, points):
        if name in self.boundaries:
            raise ValueError("duplicate patch boundary: " + name)
        ids = tuple(self._vertex(point) for point in points)
        if len(ids) < 2 or len(set(ids)) != len(ids):
            raise ValueError("patch boundary must contain distinct ordered vertices")
        self.boundaries[name] = ids
        return ids

    def boundary_ids(self, name):
        return self.boundaries[name]

    def _resolve(self, value):
        return self.boundaries[value] if isinstance(value, str) else tuple(value)

    def patch(self, name, top, right, bottom, left, control=(0.0, 0.0, 0.0)):
        """Fill four already-authored shared boundaries with a Coons-style patch.

        Boundary orientation is explicit:
        ``top`` and ``bottom`` run left->right, while ``left`` and ``right`` run
        top->bottom.  Opposite boundaries must have matching sample counts.  The
        patch creates only interior vertices; every edge vertex belongs to its
        boundary object and is therefore genuinely shared with neighbouring patches.
        """
        top = self._resolve(top)
        right = self._resolve(right)
        bottom = self._resolve(bottom)
        left = self._resolve(left)
        if len(top) != len(bottom) or len(left) != len(right):
            raise ValueError("opposite patch boundaries require matching samples: " + name)
        if not (
            top[0] == left[0]
            and top[-1] == right[0]
            and bottom[0] == left[-1]
            and bottom[-1] == right[-1]
        ):
            raise ValueError("patch boundaries do not share corner vertices: " + name)

        rows, cols = len(left), len(top)
        p00 = self.vertices[top[0]]
        p10 = self.vertices[top[-1]]
        p01 = self.vertices[bottom[0]]
        p11 = self.vertices[bottom[-1]]
        grid = []
        region = set()
        for row_index in range(rows):
            t = row_index / (rows - 1)
            row = []
            for col_index in range(cols):
                s = col_index / (cols - 1)
                if row_index == 0:
                    vertex = top[col_index]
                elif row_index == rows - 1:
                    vertex = bottom[col_index]
                elif col_index == 0:
                    vertex = left[row_index]
                elif col_index == cols - 1:
                    vertex = right[row_index]
                else:
                    top_point = self.vertices[top[col_index]]
                    bottom_point = self.vertices[bottom[col_index]]
                    left_point = self.vertices[left[row_index]]
                    right_point = self.vertices[right[row_index]]
                    bilinear = tuple(
                        (1.0 - s) * (1.0 - t) * p00[axis]
                        + s * (1.0 - t) * p10[axis]
                        + (1.0 - s) * t * p01[axis]
                        + s * t * p11[axis]
                        for axis in range(3)
                    )
                    point = tuple(
                        (1.0 - t) * top_point[axis]
                        + t * bottom_point[axis]
                        + (1.0 - s) * left_point[axis]
                        + s * right_point[axis]
                        - bilinear[axis]
                        for axis in range(3)
                    )
                    influence = 16.0 * s * (1.0 - s) * t * (1.0 - t)
                    point = add(point, mul(control, influence))
                    vertex = len(self.vertices)
                    self.vertices.append(point)
                row.append(vertex)
                region.add(vertex)
            grid.append(tuple(row))

        for row_index in range(rows - 1):
            for col_index in range(cols - 1):
                self.faces.append(
                    (
                        grid[row_index][col_index],
                        grid[row_index][col_index + 1],
                        grid[row_index + 1][col_index + 1],
                        grid[row_index + 1][col_index],
                    )
                )
        self.regions[name] = tuple(sorted(region))
        return self.regions[name]

    def ordered_loop(self, parts):
        """Join named boundary pieces into one closed ordered loop."""
        result = []
        for name, reverse in parts:
            ids = self.boundaries[name]
            if reverse:
                ids = tuple(reversed(ids))
            if not result:
                result.extend(ids)
            else:
                if result[-1] != ids[0]:
                    raise ValueError("boundary pieces do not form a continuous loop")
                result.extend(ids[1:])
        if result[-1] != result[0]:
            raise ValueError("boundary loop is not closed")
        result.pop()
        return tuple(result)

    def region_vertices(self, names):
        result = set()
        for name in names:
            result.update(self.regions[name])
        return tuple(sorted(result))


def vertex_neighbors(faces, vertex_count):
    result = [set() for _ in range(vertex_count)]
    for face in faces:
        for index, a in enumerate(face):
            b = face[(index + 1) % len(face)]
            result[a].add(b)
            result[b].add(a)
    return result


def vertex_normals(vertices, faces):
    result = [(0.0, 0.0, 0.0) for _ in vertices]
    for face in faces:
        if len(face) < 3:
            continue
        a, b, c = (vertices[face[index]] for index in range(3))
        normal = cross(sub(b, a), sub(c, a))
        for index in face:
            result[index] = add(result[index], normal)
    return tuple(normalized(normal) for normal in result)


def brush(vertices, indices, center, radius, delta=(0.0, 0.0, 0.0), normal_amount=0.0, normals=None):
    """Generic proportional grab/inflate operation over an explicit region."""
    for index in indices:
        distance = sqrt(sum((vertices[index][axis] - center[axis]) ** 2 for axis in range(3)))
        if distance >= radius:
            continue
        t = 1.0 - distance / radius
        weight = t * t * (3.0 - 2.0 * t)
        move = mul(delta, weight)
        if normals is not None and normal_amount:
            move = add(move, mul(normals[index], normal_amount * weight))
        vertices[index] = add(vertices[index], move)


def relax(vertices, faces, indices, locked=(), strength=0.10, iterations=2):
    """Laplacian relax over a selected region while preserving locked boundaries."""
    neighbors = vertex_neighbors(faces, len(vertices))
    selected = set(indices) - set(locked)
    for _ in range(iterations):
        old = list(vertices)
        updates = {}
        for index in selected:
            adjacent = neighbors[index]
            if not adjacent:
                continue
            average = tuple(
                sum(old[other][axis] for other in adjacent) / len(adjacent)
                for axis in range(3)
            )
            updates[index] = tuple(
                old[index][axis] + (average[axis] - old[index][axis]) * strength
                for axis in range(3)
            )
        for index, point in updates.items():
            vertices[index] = point


def orient_faces_consistently(faces):
    """Orient a connected manifold surface so every shared edge is opposite."""
    edge_faces = defaultdict(list)
    for face_index, face in enumerate(faces):
        for index, a in enumerate(face):
            b = face[(index + 1) % len(face)]
            edge_faces[tuple(sorted((a, b)))].append((face_index, a, b))
    flip = [None] * len(faces)
    for seed in range(len(faces)):
        if flip[seed] is not None:
            continue
        flip[seed] = False
        pending = deque([seed])
        while pending:
            face_index = pending.popleft()
            face = faces[face_index]
            for index, a in enumerate(face):
                b = face[(index + 1) % len(face)]
                for other, oa, ob in edge_faces[tuple(sorted((a, b)))]:
                    if other == face_index:
                        continue
                    same_direction = a == oa and b == ob
                    required = flip[face_index] ^ same_direction
                    if flip[other] is None:
                        flip[other] = required
                        pending.append(other)
                    elif flip[other] != required:
                        raise ValueError("patch surface cannot be oriented consistently")
    return tuple(
        tuple(reversed(face)) if flip[index] else tuple(face)
        for index, face in enumerate(faces)
    )
