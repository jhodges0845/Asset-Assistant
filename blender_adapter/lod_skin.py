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


def plan_skin_lod_weights(source, reduced, *, max_distance=None):
    """Plan barycentric transfer on rest surfaces without modifying either mesh.

    The target must be an independent, unrigged static mesh. Each target vertex
    uses the closest source triangle in world-space rest geometry; source pose
    evaluation is deliberately excluded. This is a plan, not a deformation proof.
    """
    from mathutils.bvhtree import BVHTree
    from .lod import _validate_source
    if max_distance is not None and (isinstance(max_distance, bool) or not isinstance(max_distance, (int, float)) or not isfinite(max_distance) or max_distance < 0):
        raise ValueError('Maximum transfer distance must be finite and nonnegative')
    contract = inspect_skin_lod_source(source)
    _validate_source(reduced)
    if reduced.data == source.data:
        raise ValueError('Skin transfer requires an independent target mesh')
    source.data.calc_loop_triangles()
    triangles = [tuple(face.vertices) for face in source.data.loop_triangles]
    vertices = [source.matrix_world @ vertex.co for vertex in source.data.vertices]
    targets = [reduced.matrix_world @ vertex.co for vertex in reduced.data.vertices]
    if any(not isfinite(value) for point in vertices + targets for value in point):
        raise ValueError('Skin transfer requires finite world-space geometry')
    if not triangles or not targets:
        raise ValueError('Skin transfer requires source triangles and target vertices')
    tree = BVHTree.FromPolygons(vertices, triangles, all_triangles=True)
    weights = []
    for point in targets:
        nearest = tree.find_nearest(point)
        if nearest is None or nearest[0] is None:
            raise ValueError('Could not locate a source triangle for skin transfer')
        location, _, index, distance = nearest
        if max_distance is not None and distance > max_distance:
            raise ValueError('Target exceeds the maximum skin transfer distance')
        triangle = triangles[index]
        a, b, c = (vertices[i] for i in triangle)
        ab, ac, ap = b - a, c - a, location - a
        aa, bb, cc = ab.dot(ab), ab.dot(ac), ac.dot(ac)
        denominator = aa * cc - bb * bb
        if denominator <= 0:
            raise ValueError('Skin transfer encountered a degenerate source triangle')
        v = (cc * ap.dot(ab) - bb * ap.dot(ac)) / denominator
        w = (aa * ap.dot(ac) - bb * ap.dot(ab)) / denominator
        factors = [max(0.0, min(1.0, value)) for value in (1 - v - w, v, w)]
        factor_total = sum(factors)
        row = {}
        for vertex_index, factor in zip(triangle, factors):
            for name, weight in contract.weights[vertex_index]:
                row[name] = row.get(name, 0.0) + weight * factor / factor_total
        total = sum(row.values())
        if not isfinite(total) or total <= 0:
            raise ValueError('Skin transfer produced invalid weights')
        weights.append(tuple(sorted((name, value / total) for name, value in row.items() if value > 0)))
    return SkinLODSource(contract.armature, tuple(weights), contract.deform_bones)


def build_skin_lod_candidate(source, reduced, scene, *, max_distance):
    """Create a separate bound candidate; neither input is changed.

    Callers must supply an explicit rest-surface distance limit. This low-level
    builder does not apply a preview, replace source geometry, or certify motion.
    """
    import bpy
    if scene != bpy.context.scene:
        raise ValueError('Skin LOD candidate requires the active scene')
    if any(scene.objects.get(obj.name) != obj for obj in (source, reduced)):
        raise ValueError('Skin LOD inputs must belong to the active scene')
    plan = plan_skin_lod_weights(source, reduced, max_distance=max_distance)
    mesh = reduced.data.copy()
    candidate = None
    try:
        candidate = bpy.data.objects.new(reduced.name + ' Skin Candidate', mesh)
        scene.collection.objects.link(candidate)
        candidate.matrix_world = reduced.matrix_world.copy()
        for index, slot in enumerate(reduced.material_slots):
            mesh.materials[index] = slot.material
        for name in plan.deform_bones:
            candidate.vertex_groups.new(name=name)
        for index, row in enumerate(plan.weights):
            for name, weight in row:
                candidate.vertex_groups[name].add([index], weight, 'REPLACE')
        modifier = candidate.modifiers.new('LOD Skin', 'ARMATURE')
        modifier.object = plan.armature
        modifier.use_deform_preserve_volume = source.modifiers[0].use_deform_preserve_volume
        inspect_skin_lod_source(candidate)
        candidate['asset_assistant_skin_lod_candidate'] = True
        return candidate
    except Exception:
        if candidate is not None:
            bpy.data.objects.remove(candidate, do_unlink=True)
        if mesh.users == 0:
            bpy.data.meshes.remove(mesh)
        raise


def build_reduced_skin_lod_candidates(source, scene, ratios=(.5, .25), *, max_distance):
    """Reduce independent rest copies using the validated static pipeline.

    Temporary rest proxies and static previews are removed on success or failure.
    Returned bound candidates are experimental derivatives, not applied previews.
    """
    import bpy
    from .lod import preview_static_lods
    inspect_skin_lod_source(source)
    if scene != bpy.context.scene or scene.objects.get(source.name) != source:
        raise ValueError('Skinned LOD source must belong to the active scene')
    mesh = source.data.copy()
    proxy = None
    preview = None
    candidates = []
    try:
        proxy = bpy.data.objects.new(source.name + ' Rest Proxy', mesh)
        scene.collection.objects.link(proxy)
        proxy.vertex_groups.clear()
        proxy.matrix_world = source.matrix_world.copy()
        for index, slot in enumerate(source.material_slots):
            mesh.materials[index] = slot.material
        preview = preview_static_lods(proxy, scene, ratios)
        for reduced, level in zip(preview.objects, preview.levels):
            candidate = build_skin_lod_candidate(source, reduced, scene, max_distance=max_distance)
            candidates.append(candidate)
            candidate.name = source.name + '_SkinLOD' + str(level.index)
            candidate['asset_assistant_lod_level'] = level.index
            candidate['asset_assistant_lod_budget'] = level.triangle_budget
        return tuple(candidates)
    except Exception:
        for candidate in candidates:
            data = candidate.data
            bpy.data.objects.remove(candidate, do_unlink=True)
            if data.users == 0:
                bpy.data.meshes.remove(data)
        raise
    finally:
        if preview is not None:
            preview.cancel()
        if proxy is not None:
            bpy.data.objects.remove(proxy, do_unlink=True)
        if mesh.users == 0:
            bpy.data.meshes.remove(mesh)
