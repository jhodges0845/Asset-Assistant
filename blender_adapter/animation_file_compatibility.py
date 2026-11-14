# SPDX-License-Identifier: GPL-3.0-or-later
"""Read-only admission checks for transferring clips without retargeting."""
from math import isfinite

from .animation import action_curves
from .animation_records import rig_signature


def validate_clip_compatibility(source, target, action, slot=None):
    """Require matching local rest frames and supported, resolvable bone channels.

    This deliberately rejects object/root motion and procedural dependencies.
    It never assigns an Action or edits either rig. File import and explicit
    registration must remain a separate transaction after this check succeeds.
    """
    if source is None or target is None or source.type != 'ARMATURE' or target.type != 'ARMATURE':
        raise ValueError('Choose source and target armatures')
    if rig_signature(source) != rig_signature(target):
        raise ValueError('Skeleton names or hierarchy differ; retargeting is required')
    for rig in (source, target):
        if rig.constraints or (rig.animation_data and rig.animation_data.drivers):
            raise ValueError('Rig constraints or drivers require manual preparation')
        if any(bone.constraints for bone in rig.pose.bones):
            raise ValueError('Bone constraints require manual preparation')
    for bone in source.data.bones:
        other = target.data.bones[bone.name]
        values = [(a, b) for row, other_row in zip(bone.matrix_local, other.matrix_local)
                  for a, b in zip(row, other_row)]
        values.append((bone.length, other.length))
        if any(not isfinite(a) or not isfinite(b) or abs(a-b) > 1e-5 for a, b in values):
            raise ValueError('Bone rest transforms differ; retargeting is required: ' + bone.name)
        if (bone.inherit_scale != other.inherit_scale or
                bone.use_inherit_rotation != other.use_inherit_rotation or
                bone.use_local_location != other.use_local_location):
            raise ValueError('Bone transform inheritance differs: ' + bone.name)
    if action is None:
        raise ValueError('Choose an animation Action')
    if len(getattr(action, 'slots', ())) > 1:
        raise ValueError('Multi-slot Actions require manual preparation')
    curves = action_curves(action, slot)
    if not curves:
        raise ValueError('Action has no animation curves in the selected slot')
    allowed = {}
    for bone in source.pose.bones:
        for prop, size in (('location', 3), ('rotation_euler', 3),
                           ('rotation_quaternion', 4), ('rotation_axis_angle', 4), ('scale', 3)):
            allowed[bone.path_from_id(prop)] = (bone, prop, size)
    for curve in curves:
        channel = allowed.get(curve.data_path)
        if channel is None or not 0 <= curve.array_index < channel[2]:
            raise ValueError('Only supported bone transform channels can be transferred: ' + curve.data_path)
        bone, prop, _ = channel
        if prop.startswith('rotation_'):
            expected = ('rotation_quaternion' if bone.rotation_mode == 'QUATERNION' else
                        'rotation_axis_angle' if bone.rotation_mode == 'AXIS_ANGLE' else 'rotation_euler')
            if prop != expected or bone.rotation_mode != target.pose.bones[bone.name].rotation_mode:
                raise ValueError('Bone rotation modes differ or channel is inactive: ' + bone.name)
        if curve.modifiers or curve.driver:
            raise ValueError('Procedural animation channels require manual preparation')
        if not curve.keyframe_points or curve.sampled_points:
            raise ValueError('Only keyed animation curves can be transferred')
        if any(not isfinite(value) for key in curve.keyframe_points
               for point in (key.co, key.handle_left, key.handle_right) for value in point):
            raise ValueError('Animation contains non-finite keys')
        target.path_resolve(curve.data_path)
    return tuple(curves)


def _inspect_animation_file(filepath, target, context, consume=None):
    """Inspect compatible clips, removing all temporary imported data on exit.

    This is a preview only: no Action is transferred, assigned or registered.
    """
    from pathlib import Path
    import bpy
    from .asset_file_import_ui import _import_external, _IMPORT_DATA_KINDS
    path = Path(filepath).resolve()
    if not path.is_file() or path.suffix.lower() not in ('.fbx', '.glb', '.gltf'):
        raise ValueError('Choose an existing FBX, GLB or glTF animation file')
    if context.mode != 'OBJECT':
        raise ValueError('Animation file inspection requires Object Mode')
    before = {kind: set(getattr(bpy.data, kind)) for kind in _IMPORT_DATA_KINDS}
    selected = tuple(context.selected_objects)
    active = context.view_layer.objects.active
    scene = context.scene
    timing = (scene.frame_start, scene.frame_end, scene.frame_current, scene.frame_subframe,
              scene.render.fps, scene.render.fps_base)
    retained = set()
    try:
        _import_external(str(path), path.suffix.lower(), context)
        rigs = [obj for obj in set(bpy.data.objects) - before['objects'] if obj.type == 'ARMATURE']
        if len(rigs) != 1:
            raise ValueError('Animation file must contain exactly one source rig')
        source = rigs[0]
        pairs = []
        animation = source.animation_data
        if animation:
            if animation.action:
                pairs.append((animation.action, animation.action_slot))
            for track in animation.nla_tracks:
                for strip in track.strips:
                    if strip.action and (strip.action, strip.action_slot) not in pairs:
                        pairs.append((strip.action, strip.action_slot))
        if not pairs:
            raise ValueError('Animation file contains no rig clips')
        reports = []
        for action, slot in pairs:
            if action in before['actions']:
                raise ValueError('Importer reused an existing Action')
            curves = validate_clip_compatibility(source, target, action, slot)
            reports.append({'name': action.name, 'frames': tuple(action.frame_range),
                            'channels': len(curves)})
        if consume is not None:
            result, keep = consume(pairs, tuple(reports))
            retained.update(keep)
            return result
        return tuple(reports)
    finally:
        created = [item for kind, original in before.items()
                   for item in set(getattr(bpy.data, kind)) - original if item not in retained]
        if created:
            bpy.data.batch_remove(ids=created)
        scene.frame_start, scene.frame_end = timing[:2]
        scene.render.fps, scene.render.fps_base = timing[4:]
        scene.frame_set(timing[2], subframe=timing[3])
        for obj in context.selected_objects:
            obj.select_set(False)
        for obj in selected:
            obj.select_set(True)
        context.view_layer.objects.active = active


def inspect_animation_file(filepath, target, context):
    """Preview compatible file clips without retaining imported data."""
    return _inspect_animation_file(filepath, target, context)


def transfer_animation_file(filepath, root, context, *, expected_sha256, clips, fps=24.0):
    """Explicitly copy selected FBX/GLB clips into a rig's managed library.

    clips maps inspected zero-based clip indexes to user-approved export names.
    No target Action/NLA is assigned. Every copied Action rolls back on failure.
    """
    from hashlib import sha256
    from pathlib import Path
    from .asset_structure import asset_rigs
    from .animation_lifecycle import register_animation_action
    from .core import AnimationSource
    path = Path(filepath).resolve()
    if path.suffix.lower() not in ('.fbx', '.glb'):
        raise ValueError('Clip transfer currently supports self-contained FBX and GLB files')
    payload = path.read_bytes()
    if path.suffix.lower() == '.glb':
        import json
        import struct
        if len(payload) < 20 or payload[:4] != b'glTF' or payload[16:20] != b'JSON':
            raise ValueError('Invalid GLB header')
        size = struct.unpack_from('<I', payload, 12)[0]
        document = json.loads(payload[20:20 + size])
        if any(buffer.get('uri') for buffer in document.get('buffers', ())):
            raise ValueError('External animation buffers require a self-contained GLB export')
    if not expected_sha256 or sha256(payload).hexdigest() != expected_sha256:
        raise ValueError('Animation file changed; inspect it again before applying')
    rigs = asset_rigs(root)
    if len(rigs) != 1:
        raise ValueError('Choose an asset with exactly one target rig')
    if not clips or any(type(index) is not int or index < 0 for index in clips):
        raise ValueError('Select inspected clip indexes and export names')
    names = [str(name).strip() for name in clips.values()]
    if any(not name for name in names) or len(set(names)) != len(names):
        raise ValueError('Selected clips need distinct nonempty export names')

    def consume(pairs, reports):
        if sha256(path.read_bytes()).hexdigest() != expected_sha256:
            raise ValueError('Animation file changed during import; inspect it again')
        if any(index >= len(pairs) for index in clips):
            raise ValueError('Selected clip is no longer available; inspect again')
        copies = []
        for index, name in clips.items():
            action = pairs[index][0].copy()
            # Imported custom properties must not claim generated/managed identity.
            for key in tuple(action.keys()):
                if key.startswith('asset_assistant_'):
                    del action[key]
            action.name = str(name).strip()
            register_animation_action(root, action, source=AnimationSource.IMPORTED,
                                      display_name=action.name, export_name=str(name).strip(),
                                      fps=fps, source_reference=str(path))
            action.use_fake_user = True
            copies.append(action)
        return tuple(copies), copies

    return _inspect_animation_file(path, rigs[0], context, consume=consume)
