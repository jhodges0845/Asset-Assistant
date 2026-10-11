# SPDX-License-Identifier: GPL-3.0-or-later
"""Avian rig and skin-weight generation."""

from collections import deque
from math import sqrt

from .avian_anatomy import AvianRecipe

from ..models import Bone, BoneWeight, Skeleton, SkinWeights


def generate_avian_skeleton(dimensions):
    """Build the rest rig through the single Avian recipe."""
    return _build_avian_skeleton(AvianRecipe().resolve(dimensions))


def _build_avian_skeleton(anatomy):
    points = {p.name: p.position for p in anatomy.landmarks}
    bones = []
    for chain in anatomy.chains:
        parent = chain.parent_bone
        for index, name in enumerate(chain.bones):
            bones.append(Bone(name, points[chain.landmarks[index]],
                              points[chain.landmarks[index + 1]], parent))
            parent = name
    return Skeleton(tuple(bones))


def _distance_to_segment(point, start, end):
    axis = tuple(end[i] - start[i] for i in range(3))
    offset = tuple(point[i] - start[i] for i in range(3))
    length_sq = sum(value * value for value in axis)
    amount = sum(offset[i] * axis[i] for i in range(3)) / length_sq
    amount = max(0.0, min(1.0, amount))
    closest = tuple(start[i] + axis[i] * amount for i in range(3))
    return sqrt(sum((point[i] - closest[i]) ** 2 for i in range(3)))


def _candidate_bones(vertex, bones):
    side = "left" if vertex[0] <= 0 else "right"
    return tuple(
        bone for bone in bones
        if not (bone.name.endswith(".left") or bone.name.endswith(".right"))
        or bone.name.endswith("." + side)
    )


def _weights_for_vertex(vertex, bones, max_influences=4, *, side_filter=True):
    candidates = _candidate_bones(vertex, bones) if side_filter else bones
    ranked = sorted(
        ((_distance_to_segment(vertex, bone.head, bone.tail), bone) for bone in candidates),
        key=lambda item: (item[0], item[1].name),
    )
    nearest = ranked[0][1]
    local_names = {nearest.name}
    if nearest.parent:
        local_names.add(nearest.parent)
    local_names.update(bone.name for bone in candidates if bone.parent == nearest.name)
    local = [(distance, bone) for distance, bone in ranked if bone.name in local_names][:max_influences]
    raw = [(bone.name, 1.0 / ((distance + 1e-3) ** 2)) for distance, bone in local]
    total = sum(value for _name, value in raw)
    normalized = [(name, value / total) for name, value in raw]
    correction = 1.0 - sum(value for _name, value in normalized)
    normalized[0] = (normalized[0][0], normalized[0][1] + correction)
    return tuple(BoneWeight(name, value) for name, value in normalized if value > 0)


def _wing_ownership(mesh, anatomy, bones):
    """Use authored membership, not current coordinates, for wing ownership."""
    anatomy.validate_mesh(mesh)
    regions = {r.name: r for r in anatomy.regions}
    chains = {c.name: c for c in anatomy.chains}
    parts = {p.name: p for p in mesh.parts}
    result, attachments = {}, {}
    for name in ('wing.left', 'wing.right'):
        region, chain = regions[name], chains[name]
        owned = set(region.vertex_indices)
        local = tuple(b for b in bones if b.name in chain.bones)
        if len(local) != len(chain.bones) or chain.parent_bone not in {b.name for b in bones}:
            raise ValueError('Avian skeleton is missing an authored wing bone')
        connection = next(c for c in anatomy.connections if c.regions == ('body', name))
        root, first = map(set, connection.boundaries)
        if not root or not first or not first <= owned or not root <= set(regions['body'].vertex_indices):
            raise ValueError('Avian wing requires authored attachment boundaries')
        # One edge interval past the attachment gives a short parent fade.
        graph = {i: set() for i in owned}
        for face in parts[region.mesh_part].faces:
            for a, b in zip(face, face[1:] + face[:1]):
                if a in owned and b in owned:
                    graph[a].add(b)
                    graph[b].add(a)
        depths = dict.fromkeys(first, 0)
        pending = deque(sorted(first))
        while pending:
            index = pending.popleft()
            if depths[index] == 1:
                continue
            for neighbor in sorted(graph[index]):
                if neighbor not in depths:
                    depths[neighbor] = depths[index] + 1
                    pending.append(neighbor)
        for index in owned:
            key = (region.mesh_part, index)
            if key in result:
                raise ValueError('Avian wing regions must be disjoint')
            result[key] = local
            if index in depths:
                parent = .25 if depths[index] == 0 else .10
                attachments[key] = ((chain.bones[0], 1 - parent), (chain.parent_bone, parent))
        for index in root:
            attachments[(region.mesh_part, index)] = ((chain.parent_bone, 1.0),)
    return result, attachments


def generate_avian_skin_weights(mesh, skeleton, *, anatomy, max_influences=4):
    """Keep wing motion within authored wings, with a short shoulder collar."""
    if type(max_influences) is not int or max_influences < 1:
        raise ValueError('Avian max influences must be a positive integer')
    deform_bones = tuple(bone for bone in skeleton.bones if bone.name != 'root')
    if not deform_bones:
        raise ValueError('Avian skeleton must contain deform bones')
    wing_candidates, attachments = _wing_ownership(mesh, anatomy, deform_bones)
    nonwing = tuple(b for b in deform_bones if not b.name.startswith('wing.'))
    results = []
    for part in mesh.parts:
        weights = []
        for index, vertex in enumerate(part.vertices):
            key = (part.name, index)
            if key in attachments:
                raw = attachments[key][:max_influences]
                total = sum(weight for _, weight in raw)
                weights.append(tuple(BoneWeight(name, weight / total) for name, weight in raw))
            else:
                owned = key in wing_candidates
                candidates = wing_candidates[key] if owned else nonwing
                weights.append(_weights_for_vertex(vertex, candidates, max_influences, side_filter=not owned))
        results.append(SkinWeights(part.name, tuple(weights)))
    return tuple(results)
