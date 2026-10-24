# SPDX-License-Identifier: GPL-3.0-or-later
"""Read-only observations of Blender objects, materials, and image references."""

from collections import Counter
from math import isfinite
from pathlib import Path

from .core import AssetSnapshot


def _image_nodes(tree, seen=None):
    seen = set() if seen is None else seen
    if tree is None or tree.as_pointer() in seen:
        return
    seen.add(tree.as_pointer())
    for node in tree.nodes:
        if node.type == "TEX_IMAGE" and any(socket.is_linked for socket in node.outputs):
            yield node
        elif node.type == "GROUP" and any(socket.is_linked for socket in node.outputs):
            yield from _image_nodes(node.node_tree, seen)


def inspect_character(root):
    """Preserve the UI's direct-child inspection scope."""
    return inspect_objects([root] + list(root.children) if root is not None else [])


def inspect_objects(objects, *, require_manifold_geometry=True):
    """Inspect an explicit scope without modifying scene data.

    Closed surfaces remain the conservative default. Game target profiles can
    accept boundary edges (including imported UV/normal seams); non-finite,
    degenerate, loose-edge and over-shared-edge geometry remains invalid.
    """
    import bpy
    objects = tuple(objects)
    meshes = [obj for obj in objects if obj.type == "MESH"]
    rigs = [obj for obj in objects if obj.type == "ARMATURE"]
    invalid, materials_missing, uv_missing = [], [], []
    missing_images, texture_warnings, transform_warnings, rig_errors = [], [], [], []
    images, materials = {}, {}
    for obj in meshes:
        data = obj.data
        edges = Counter(tuple(sorted(edge)) for face in data.polygons for edge in face.edge_keys)
        bad = (not data.vertices or not data.polygons
               or any(not isfinite(v) for vertex in data.vertices for v in vertex.co)
               or any(not isfinite(face.area) or face.area <= 0 for face in data.polygons)
               or any(count > 2 or (require_manifold_geometry and count != 2) for count in edges.values())
               or len(edges) != len(data.edges))
        if bad:
            invalid.append(obj.name)
        for face in data.polygons:
            index = face.material_index
            material = obj.material_slots[index].material if index < len(obj.material_slots) else None
            if material is None:
                materials_missing.append(obj.name)
            else:
                materials[material.as_pointer()] = material
        if data.uv_layers.active is None or any(not isfinite(value) for uv in data.uv_layers.active.data for value in uv.uv):
            uv_missing.append(obj.name)
        if any(abs(value - 1) > 1e-6 for value in obj.scale):
            transform_warnings.append(obj.name + ": review unapplied scale before export.")
    if len(rigs) > 1:
        rig_errors.append("Multiple armatures found; review which one drives this character.")
    for rig in rigs:
        if not rig.data.bones:
            rig_errors.append(rig.name + ": no bones.")
        for obj in meshes:
            modifiers = [m for m in obj.modifiers if m.type == "ARMATURE" and m.object == rig
                         and m.show_viewport and m.show_render and m.use_vertex_groups]
            if not modifiers:
                rig_errors.append(obj.name + ": enabled armature modifier missing.")
                continue
            groups = {g.index for g in obj.vertex_groups if g.name in rig.data.bones
                      and rig.data.bones[g.name].use_deform}
            if any(not any(g.group in groups and isfinite(g.weight) and g.weight > 0 for g in v.groups)
                   for v in obj.data.vertices):
                rig_errors.append(obj.name + ": vertices lack bone weights.")
    has_animation = False
    animation_errors = []
    for obj in objects:
        animation = obj.animation_data
        if animation:
            from .animation import action_curves
            actions = ([(animation.action, getattr(animation, 'action_slot', None))] if animation.action else [])
            actions += [(strip.action, getattr(strip, 'action_slot', None)) for track in animation.nla_tracks if not track.mute
                        for strip in track.strips if strip.action and not strip.mute]
            for action, slot in actions:
                for curve in action_curves(action, slot):
                    if curve.mute or not curve.keyframe_points:
                        continue
                    try:
                        obj.path_resolve(curve.data_path)
                    except (ValueError, TypeError):
                        animation_errors.append(action.name + ': animation target is missing.')
                        continue
                    values = [key.co.y for key in curve.keyframe_points]
                    if not all(isfinite(value) for value in values):
                        animation_errors.append(action.name + ': non-finite keyframes.')
                    elif max(values) - min(values) > 1e-6:
                        has_animation = True
            if actions and obj.type == 'ARMATURE' and obj.data.pose_position != 'POSE':
                animation_errors.append(obj.name + ': Rest Position hides animation; switch to Pose Position.')
            if animation.action and animation.action_influence <= 0:
                animation_errors.append(obj.name + ': active action influence is zero.')
    for material in materials.values():
        for node in _image_nodes(material.node_tree if material.use_nodes else None):
            if node.image is None:
                missing_images.append(material.name + ": connected image node has no image.")
            else:
                images[node.image.as_pointer()] = node.image
    for image in images.values():
        if image.packed_file or getattr(image, "packed_files", ()):
            continue
        if image.source in ("FILE", "TILED"):
            path = bpy.path.abspath(image.filepath, library=image.library)
            paths = [path.replace("<UDIM>", str(tile.number)) for tile in image.tiles] if image.source == "TILED" else [path]
            if not image.filepath or not paths or any(not Path(item).is_file() for item in paths):
                missing_images.append(image.name + ": external image file not found.")
        elif image.source == "GENERATED":
            texture_warnings.append(image.name + ": pack or save generated image data before export.")
        else:
            texture_warnings.append(image.name + ": movie/sequence image needs manual file verification.")
    return AssetSnapshot(
        mesh_count=len(meshes), invalid_meshes=tuple(invalid),
        missing_materials=tuple(sorted(set(materials_missing))), missing_uvs=tuple(uv_missing),
        missing_images=tuple(sorted(set(missing_images))), texture_warnings=tuple(texture_warnings),
        texture_count=len(images), has_rig=bool(rigs), rig_errors=tuple(rig_errors),
        has_animation=has_animation, animation_errors=tuple(sorted(set(animation_errors))),
        transform_warnings=tuple(transform_warnings),
        is_blockout=len(meshes) > 1 and any(obj.get("stage") == "blockout" for obj in objects),
    )
