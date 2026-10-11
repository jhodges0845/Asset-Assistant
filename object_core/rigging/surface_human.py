# SPDX-License-Identifier: GPL-3.0-or-later
"""Construct the Human rest rig from resolved chains and model-space landmarks."""
from ..models.skeleton import Bone, Skeleton


def surface_skeleton(anatomy):
    points = {landmark.name: landmark.position for landmark in anatomy.landmarks}
    bones = []
    for chain in anatomy.chains:
        parent = chain.parent_bone
        for index, name in enumerate(chain.bones):
            bones.append(Bone(name, points[chain.landmarks[index]],
                              points[chain.landmarks[index + 1]], parent))
            parent = name
    return Skeleton(tuple(bones))
