# SPDX-License-Identifier: GPL-3.0-or-later
"""Read-only admission checks for future skinned LOD reduction.

This does not reduce a mesh, alter weights, or enable the static LOD path for rigs.
"""
from dataclasses import dataclass
from math import isfinite
from .validation import inspect_objects


@dataclass(frozen=True)
class SkinLODSource:
    armature: object
    weights: tuple
    deform_bones: tuple


def inspect_skin_lod_source(source):
    """Require explicit, normalized bone weights before deriving skinned copies."""
    if source is None or source.type != 'MESH' or source.mode != 'OBJECT':
        raise ValueError('Choose a skinned mesh in Object Mode')
    if source.constraints or source.animation_data or source.data.animation_data or source.data.shape_keys:
        raise ValueError('Skinned LOD source cannot have mesh animation, constraints or shape keys')
    if len(source.modifiers) != 1 or source.modifiers[0].type != 'ARMATURE':
        raise ValueError('Skinned LOD source requires exactly one Armature modifier')
    modifier = source.modifiers[0]
    rig = modifier.object
    if rig is None or rig.type != 'ARMATURE' or rig.mode == 'EDIT':
        raise ValueError('Skinned LOD source requires an available armature outside Edit Mode')
    if (not modifier.use_vertex_groups or modifier.use_bone_envelopes or
            modifier.vertex_group or modifier.use_multi_modifier or
            not modifier.show_viewport or not modifier.show_render):
        raise ValueError('Skinned LOD requires enabled vertex-group deformation without envelopes or masks')
    if inspect_objects([source], require_manifold_geometry=False).invalid_meshes:
        raise ValueError('Resolve invalid source geometry before skinned LOD reduction')
    bones = tuple(bone.name for bone in rig.data.bones if bone.use_deform)
    bone_set = set(bones)
    names = {group.index: group.name for group in source.vertex_groups}
    weights = []
    for vertex in source.data.vertices:
        row = []
        for entry in vertex.groups:
            weight = entry.weight
            if not isfinite(weight) or weight < 0:
                raise ValueError('Skin weights must be finite and nonnegative')
            if weight == 0:
                continue
            name = names.get(entry.group)
            if name not in bone_set:
                raise ValueError('Positive non-deform groups need an explicit preservation policy')
            row.append((name, weight))
        total = sum(weight for _, weight in row)
        if not row or abs(total - 1.0) > 1e-5:
            raise ValueError('Every source vertex needs normalized deform-bone weights')
        weights.append(tuple(sorted(row)))
    if not weights:
        raise ValueError('Skinned LOD source has no vertices')
    return SkinLODSource(rig, tuple(weights), bones)
