# SPDX-License-Identifier: GPL-3.0-or-later
"""Quadruped rig and skin-weight generation."""

from math import sqrt

from ..models import Bone, BoneWeight, Skeleton, SkinWeights
from .quadruped_anatomy import CanineRecipe


def generate_quadruped_skeleton(dimensions):
    """Build a deterministic quadruped skeleton from validated dimensions."""
    return _build_quadruped_skeleton(CanineRecipe().resolve(dimensions))


def _build_quadruped_skeleton(anatomy):
    """Construct all bones directly from resolved chains and landmarks."""
    landmarks = {landmark.name: landmark.position for landmark in anatomy.landmarks}
    bones = []
    for chain in anatomy.chains:
        parent = chain.parent_bone
        for index, name in enumerate(chain.bones):
            bones.append(Bone(name, landmarks[chain.landmarks[index]],
                              landmarks[chain.landmarks[index + 1]], parent))
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


def _candidate_bones(vertex, bones, authored_side=None):
    """Prevent a vertex from being influenced by the opposite-side limb."""
    side = authored_side or ("left" if vertex[0] <= 0 else "right")
    return tuple(
        bone for bone in bones
        if not (bone.name.endswith(".left") or bone.name.endswith(".right"))
        or bone.name.endswith("." + side)
    )


def _weights_for_vertex(vertex, bones, max_influences=4, authored_side=None):
    candidates = _candidate_bones(vertex, bones, authored_side)
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


def generate_quadruped_skin_weights(mesh, skeleton, *, max_influences=4, anatomy=None):
    """Return normalized local weights for a connected quadruped surface."""
    owners = {}
    if anatomy is not None:
        anatomy.validate_mesh(mesh)
        owners = {(region.mesh_part, index): region.name.rsplit(".", 1)[1]
                  for region in anatomy.regions if region.name.startswith("leg.")
                  for index in region.vertex_indices}
    deform_bones = tuple(bone for bone in skeleton.bones if bone.name != "root")
    if not deform_bones:
        raise ValueError("Quadruped skeleton must contain deform bones")
    return tuple(
        SkinWeights(
            part.name,
            tuple(_weights_for_vertex(vertex, deform_bones, max_influences, owners.get((part.name, index)))
                  for index, vertex in enumerate(part.vertices)),
        )
        for part in mesh.parts
    )
