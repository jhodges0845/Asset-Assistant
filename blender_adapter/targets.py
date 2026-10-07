# SPDX-License-Identifier: GPL-3.0-or-later
"""Blender output adapters; metadata and options are usable without bpy."""

from contextlib import contextmanager
from dataclasses import dataclass, replace
from math import isfinite
from pathlib import Path
from typing import Tuple

from .core import ValidationIssue, get_target, validate_for_target
from .validation import inspect_objects


_GENERATED_TEXTURE_MARKER = 'asset_assistant_generated_texture'


@dataclass(frozen=True)
class ExportResult:
    success: bool
    filepath: str
    issues: Tuple[ValidationIssue, ...] = ()


def asset_objects(root):
    """Return the complete normalized asset boundary used for validation/export."""
    if root is None:
        return ()
    from .asset_structure import asset_members
    return asset_members(root)


def base_asset_rig(root):
    """Return the one normalized base armature without component-owned rigs."""
    if root is None:
        return None
    from .asset_structure import asset_rigs
    rigs = asset_rigs(root)
    if len(rigs) != 1:
        return None
    return rigs[0]


def _is_generated_texture(image):
    """Recognize owned generated images without depending on Blender source state."""
    return image.source == 'GENERATED' or bool(image.get(_GENERATED_TEXTURE_MARKER, False))


@contextmanager
def _stage_generated_animation_tracks(root):
    """Temporarily stash generated clips as one NLA track each for engine export.

    Blender keeps one action active for editing/preview. Engine files need a clip
    library, so generated actions are associated with the rig through temporary
    single-strip NLA tracks only while the exporter runs. Existing artist NLA or
    drivers remain a preservation boundary and are never modified.
    """
    from .animation import clip_export_name, generated_actions

    rig = base_asset_rig(root)
    if rig is None:
        yield False
        return
    actions = generated_actions(root)
    if not actions:
        yield False
        return

    data = rig.animation_data_create()
    if data.nla_tracks or data.drivers:
        raise RuntimeError('Existing NLA tracks or drivers are preserved; prepare them manually before multi-clip export.')

    previous_action = data.action
    previous_slot = getattr(data, 'action_slot', None)
    tracks = []
    try:
        data.action = None
        for action in actions:
            clip_name = clip_export_name(action)
            track = data.nla_tracks.new()
            track.name = clip_name
            track.strips.new(clip_name, int(round(action.frame_range[0])), action)
            tracks.append(track)
        yield True
    finally:
        for track in reversed(tracks):
            data.nla_tracks.remove(track)
        data.action = previous_action
        if previous_action is not None and previous_slot is not None and hasattr(data, 'action_slot'):
            data.action_slot = previous_slot


def _export_gltf(options, root):
    import bpy
    options = dict(options)
    properties = bpy.ops.export_scene.gltf.get_rna_type().properties
    if 'use_active_scene' not in properties:
        options.pop('use_active_scene', None)
    with _stage_generated_animation_tracks(root) as staged:
        if 'export_animation_mode' in properties:
            # Integer-frame NLA baking truncates fractional clip endpoints and
            # discards dense contact keys. Pure keyed generated actions can be
            # exported directly through their temporary single-strip tracks.
            # Constrained/driven assets retain evaluated baking.
            authored = staged and 'export_merge_animation' in properties and not any(
                obj.constraints or (obj.animation_data and obj.animation_data.drivers)
                or (obj.type == 'ARMATURE' and any(b.constraints for b in obj.pose.bones))
                for obj in asset_objects(root))
            options['export_animation_mode'] = 'ACTIONS' if authored or not staged else 'NLA_TRACKS'
            if authored:
                options['export_force_sampling'] = False
                options['export_merge_animation'] = 'NLA_TRACK'
                # Only actions associated with this asset may enter its file.
                if 'export_anim_single_armature' in properties:
                    options['export_anim_single_armature'] = False
        return bpy.ops.export_scene.gltf(**options)


def is_ready(issues):
    """Only completed checks with no unresolved problems can enable Export."""
    return bool(issues) and not any(issue.status in ('ERROR', 'WARN') for issue in issues)


class BlenderOutputAdapter:
    target_key = None
    extensions = ()
    operator_name = None

    def __init__(self, *, asset_use=None, require_textures=False):
        self.profile = get_target(self.target_key)
        self.profile = replace(self.profile, require_textures=require_textures) if require_textures else self.profile
        if not self.profile.supports_rig:
            asset_use = "STATIC"
        if asset_use is not None:
            if asset_use not in ("STATIC", "RIGGED", "ANIMATED"):
                raise ValueError("asset_use must be STATIC, RIGGED, or ANIMATED")
            self.profile = replace(self.profile, asset_use=asset_use,
                                   require_rig=asset_use != "STATIC",
                                   require_animation=asset_use == "ANIMATED")

    def prepare(self, root, context):
        """Read-only checks; scene edits use explicit undoable UI operators."""
        return self.validate(root, context)

    def output_path(self, filepath):
        path = Path(filepath)
        if not path.suffix:
            path = path.with_suffix(self.default_extension)
        if path.suffix.lower() not in self.extensions:
            raise ValueError(self.profile.display_name + " export requires " + " or ".join(self.extensions))
        return path.with_suffix(path.suffix.lower()).resolve()

    def export_options(self, filepath):
        raise NotImplementedError

    def write(self, options, root, context):
        raise NotImplementedError

    def inspect(self, objects, context):
        return inspect_objects(objects)

    def validate(self, root, context):
        context.view_layer.update()
        objects = asset_objects(root)
        issues = []

        def add(code, status, message):
            issues.append(ValidationIssue(code, status, message))

        if context.mode != "OBJECT":
            add("blender_mode", "ERROR", "Switch to Object Mode before export.")
        for obj in objects:
            if obj.type not in ("EMPTY", "MESH", "ARMATURE"):
                add("export_type", "ERROR", obj.name + ": unsupported export object type " + obj.type)
            if obj.name not in context.view_layer.objects or not obj.visible_get() or obj.hide_select:
                add("export_scope", "ERROR", obj.name + ": must be visible and selectable in the active view layer.")
            matrix = obj.matrix_world
            if any(not isfinite(v) for row in matrix for v in row) or abs(matrix.determinant()) < 1e-12:
                add("export_transform", "ERROR", obj.name + ": non-finite or singular transform; repair before export.")
            elif matrix.determinant() < 0:
                add("export_transform", "WARN", obj.name + ": mirrored transform; review normals and skinning.")
            if self.target_key == "CURA":
                continue
            for modifier in obj.modifiers:
                if modifier.type != 'ARMATURE' and modifier.show_viewport:
                    add('export_modifier', 'ERROR', obj.name + ': apply non-armature modifiers on an export copy before export.')
                if modifier.type == "ARMATURE" and modifier.object and modifier.object not in objects:
                    add("export_scope", "ERROR", obj.name + ": armature is outside the asset hierarchy.")
            animation = obj.animation_data
            if animation:
                for track in animation.nla_tracks:
                    strips = [strip for strip in track.strips if strip.action and not strip.mute]
                    if track.mute or track.is_solo or len(strips) > 1:
                        add("export_nla", "ERROR", obj.name + ": muted, solo, or multi-strip NLA tracks require manual preparation for export.")
            if obj.constraints:
                add("export_constraints", "WARN", obj.name + ": constraints need exported playback review.")
        if self.target_key == "GODOT" and context.scene.unit_settings.scale_length != 1.0:
            add("export_units", "ERROR", "Export currently requires scene unit scale 1.0; review asset dimensions before changing units. No automatic rescaling is performed.")
        try:
            issues[:0] = validate_for_target(self.inspect(objects, context), self.profile)
        except (AttributeError, ValueError, RuntimeError) as exc:
            add("export_inspection", "ERROR", "Could not inspect this Blender asset: " + str(exc))
        if self.target_key != 'CURA':
            from .materials import material_issues
            issues.extend(material_issues(objects))
        if self.operator_name:
            import bpy
            try:
                getattr(bpy.ops.export_scene, self.operator_name).get_rna_type()
            except (AttributeError, RuntimeError):
                add("exporter", "ERROR", "Enable Blender's " + self.operator_name + " exporter add-on.")
        return tuple(issues)

    def export(self, root, context, filepath):
        try:
            options = self.export_options(filepath)
        except (ValueError, TypeError, OSError) as exc:
            return ExportResult(False, str(filepath), (ValidationIssue("export_path", "ERROR", str(exc)),))
        path = Path(options["filepath"])
        issues = self.prepare(root, context)
        if not is_ready(issues):
            return ExportResult(False, str(path), issues)
        if not path.parent.is_dir() or path.exists():
            return ExportResult(False, str(path), issues + (ValidationIssue(
                "export_path", "ERROR", "Choose a new output path in an existing directory."),))
        if path.suffix.lower() == ".gltf" and any(path.parent.iterdir()):
            return ExportResult(False, str(path), issues + (ValidationIssue(
                "export_path", "ERROR", "Use an empty directory for glTF and its texture/binary sidecars."),))
        selected = tuple(context.selected_objects)
        active = context.view_layer.objects.active
        frame, subframe = context.scene.frame_current, context.scene.frame_subframe
        success = False
        try:
            for obj in selected:
                obj.select_set(False)
            for obj in asset_objects(root):
                obj.select_set(True)
            context.view_layer.objects.active = root
            status = self.write(options, root, context)
            success = "FINISHED" in status and path.is_file() and path.stat().st_size > 0
            if not success:
                issues += (ValidationIssue("export_failed", "ERROR", "Export did not produce a completed file."),)
        except Exception as exc:
            issues += (ValidationIssue("export_failed", "ERROR", str(exc) + "; check for partial output files before retrying."),)
        finally:
            for obj in context.selected_objects:
                obj.select_set(False)
            for obj in selected:
                obj.select_set(True)
            context.view_layer.objects.active = active
            context.scene.frame_set(frame, subframe=subframe)
        return ExportResult(success, str(path), issues)


class GodotAdapter(BlenderOutputAdapter):
    target_key = "GODOT"
    default_extension = ".glb"
    extensions = (".glb", ".gltf")
    operator_name = "gltf"

    def export_options(self, filepath):
        path = self.output_path(filepath)
        return dict(filepath=str(path), check_existing=False,
                    export_format="GLB" if path.suffix == ".glb" else "GLTF_SEPARATE",
                    use_selection=True, use_active_scene=True, export_yup=True, export_apply=False,
                    export_skins=True, export_animations=True, export_materials="EXPORT",
                    export_frame_range=False, export_force_sampling=True,
                    export_nla_strips=True, export_texcoords=True, export_normals=True)

    def write(self, options, root, context):
        return _export_gltf(options, root)


class FBXAdapter(BlenderOutputAdapter):
    default_extension = ".fbx"
    extensions = (".fbx",)
    operator_name = "fbx"
    axis_forward = '-Z'
    axis_up = 'Y'

    def export_options(self, filepath):
        return dict(filepath=str(self.output_path(filepath)), check_existing=False,
                    use_selection=True, object_types={'EMPTY', 'MESH', 'ARMATURE'},
                    axis_forward=self.axis_forward, axis_up=self.axis_up,
                    apply_unit_scale=True, apply_scale_options='FBX_SCALE_UNITS',
                    use_mesh_modifiers=False, add_leaf_bones=False,
                    bake_anim=True, bake_anim_use_all_actions=False,
                    bake_anim_use_nla_strips=False, bake_anim_use_all_bones=True,
                    bake_anim_simplify_factor=0.0, path_mode='COPY', embed_textures=True)

    def _texture_images(self, root):
        from .validation import _image_nodes
        seen = set()
        for obj in asset_objects(root):
            for slot in obj.material_slots:
                material = slot.material
                if material is None:
                    continue
                for node in _image_nodes(material.node_tree if material.use_nodes else None):
                    image = node.image
                    if image is None or image.as_pointer() in seen:
                        continue
                    seen.add(image.as_pointer())
                    yield image

    def _stage_generated_textures(self, root, directory):
        """Give owned in-memory images temporary PNG paths for Blender's FBX writer."""
        staged = []
        for index, image in enumerate(self._texture_images(root)):
            if not _is_generated_texture(image):
                continue
            original_path = image.filepath_raw
            original_format = image.file_format
            path = Path(directory) / ('asset_assistant_texture_%03d.png' % index)
            try:
                image.filepath_raw = str(path)
                image.file_format = 'PNG'
                image.save_render(str(path))
                if not path.is_file() or path.stat().st_size <= 0:
                    raise RuntimeError('temporary PNG was not written')
            except Exception:
                image.filepath_raw = original_path
                image.file_format = original_format
                for previous, previous_path, previous_format in staged:
                    previous.filepath_raw = previous_path
                    previous.file_format = previous_format
                raise
            staged.append((image, original_path, original_format))
        return staged

    def validate(self, root, context):
        issues = list(super().validate(root, context))
        import bpy
        for obj in asset_objects(root):
            animation = obj.animation_data
            if animation and animation.action:
                start, end = animation.action.frame_range
                if end < context.scene.frame_start or start > context.scene.frame_end:
                    issues.append(ValidationIssue('fbx_animation_range', 'ERROR', obj.name +
                        ': active action is outside the playback range. Set the range to the clip before export.'))
        for image in self._texture_images(root):
            path = (Path(bpy.path.abspath(image.filepath, library=image.library))
                    if image.filepath else None)
            if path is not None and path.is_file():
                continue
            if _is_generated_texture(image):
                issues.append(ValidationIssue('fbx_texture', 'INFO', image.name +
                    ': generated texture will be staged automatically as PNG during FBX export.'))
            else:
                issues.append(ValidationIssue('fbx_texture', 'ERROR', image.name +
                    ': save this texture as a PNG/JPEG file before FBX export.'))
        return tuple(issues)

    def export(self, root, context, filepath):
        from tempfile import TemporaryDirectory
        staged = []
        try:
            with TemporaryDirectory(prefix='asset-assistant-fbx-') as directory:
                staged = self._stage_generated_textures(root, directory)
                try:
                    return super().export(root, context, filepath)
                finally:
                    for image, original_path, original_format in staged:
                        image.filepath_raw = original_path
                        image.file_format = original_format
        except Exception as exc:
            try:
                path = str(self.output_path(filepath))
            except (ValueError, TypeError, OSError):
                path = str(filepath)
            return ExportResult(False, path, (ValidationIssue('fbx_texture', 'ERROR',
                'Could not stage generated texture for FBX export: ' + str(exc)),))

    def write(self, options, root, context):
        import bpy
        with _stage_generated_animation_tracks(root) as staged:
            if staged:
                options = dict(options)
                options['bake_anim_use_nla_strips'] = True
            return bpy.ops.export_scene.fbx(**options)


class UnityAdapter(FBXAdapter):
    target_key = 'UNITY'


class UnrealAdapter(FBXAdapter):
    target_key = 'UNREAL'
    axis_forward = '-Y'
    axis_up = 'Z'

    def export_options(self, filepath):
        """Favor a conventional skeletal FBX hierarchy for Unreal Interchange."""
        options = super().export_options(filepath)
        options['object_types'] = {'MESH', 'ARMATURE'}
        options['use_mesh_modifiers'] = True
        options['use_armature_deform_only'] = True
        options['mesh_smooth_type'] = 'FACE'
        return options

    @staticmethod
    def _clip_path(path, clip_name):
        safe_name = ''.join(character if character.isalnum() or character in ('-', '_') else '_'
                            for character in str(clip_name)).strip('_') or 'Animation'
        return path.with_name(path.stem + '_' + safe_name + path.suffix)

    def write(self, options, root, context):
        import bpy
        mode = getattr(self, '_unreal_export_mode', None)
        if mode == 'model':
            options = dict(options)
            options['bake_anim'] = False
            return bpy.ops.export_scene.fbx(**options)
        if mode == 'clip':
            objects = [obj for obj in asset_objects(root) if obj.type in ('MESH', 'ARMATURE')]
            rig = base_asset_rig(root)
            if rig is None:
                raise RuntimeError('Unreal animation export requires exactly one base asset armature.')
            for obj in tuple(context.selected_objects):
                obj.select_set(False)
            for obj in objects:
                obj.select_set(True)
            context.view_layer.objects.active = rig
            options = dict(options)
            options['object_types'] = {'MESH', 'ARMATURE'}
            options['path_mode'] = 'AUTO'
            options['embed_textures'] = False
            return bpy.ops.export_scene.fbx(**options)
        return super().write(options, root, context)

    def export(self, root, context, filepath):
        """Write an Unreal skeletal mesh FBX plus one FBX per generated clip."""
        from .animation import clip_export_name, generated_actions

        actions = tuple(sorted(generated_actions(root), key=clip_export_name))
        if self.profile.asset_use != 'ANIMATED' or len(actions) <= 1:
            return super().export(root, context, filepath)

        try:
            model_path = self.output_path(filepath)
        except (ValueError, TypeError, OSError) as exc:
            return ExportResult(False, str(filepath), (ValidationIssue('export_path', 'ERROR', str(exc)),))
        clip_paths = tuple((action, self._clip_path(model_path, clip_export_name(action))) for action in actions)
        conflicts = [path for _, path in clip_paths if path.exists()]
        if model_path.exists():
            conflicts.insert(0, model_path)
        if conflicts:
            return ExportResult(False, str(model_path), (ValidationIssue(
                'export_path', 'ERROR', 'Choose a new Unreal output name; model or animation bundle files already exist.'),))

        rig = base_asset_rig(root)
        if rig is None:
            return super().export(root, context, filepath)
        data = rig.animation_data_create()
        previous_action = data.action
        previous_slot = getattr(data, 'action_slot', None)
        previous_start, previous_end = context.scene.frame_start, context.scene.frame_end
        created = []
        issues = ()
        try:
            self._unreal_export_mode = 'model'
            result = super().export(root, context, model_path)
            issues = result.issues
            if not result.success:
                return result
            created.append(model_path)

            for action, clip_path in clip_paths:
                data.action = action
                if hasattr(action, 'slots') and len(action.slots) and hasattr(data, 'action_slot'):
                    data.action_slot = action.slots[0]
                context.scene.frame_start = int(round(action.frame_range[0]))
                context.scene.frame_end = int(round(action.frame_range[1]))
                context.scene.frame_set(context.scene.frame_start)
                self._unreal_export_mode = 'clip'
                result = super().export(root, context, clip_path)
                issues = result.issues
                if not result.success:
                    for created_path in created:
                        if created_path.exists():
                            created_path.unlink()
                    return ExportResult(False, str(model_path), issues + (ValidationIssue(
                        'unreal_animation_bundle', 'ERROR',
                        'Unreal animation bundle was not completed; partial files were removed.'),))
                created.append(clip_path)

            names = ', '.join(path.name for _, path in clip_paths)
            return ExportResult(True, str(model_path), issues + (ValidationIssue(
                'unreal_animation_bundle', 'INFO',
                'Created Unreal model plus Interchange-compatible animation FBX files: ' + names),))
        finally:
            self._unreal_export_mode = None
            data.action = previous_action
            if previous_action is not None and previous_slot is not None and hasattr(data, 'action_slot'):
                data.action_slot = previous_slot
            context.scene.frame_start = previous_start
            context.scene.frame_end = previous_end


class CuraAdapter(BlenderOutputAdapter):
    target_key = 'CURA'
    default_extension = '.stl'
    extensions = ('.stl',)

    def export_options(self, filepath):
        return dict(filepath=str(self.output_path(filepath)))

    def inspect(self, objects, context):
        from .printing import print_geometry
        snapshot, _, _ = print_geometry(objects, context)
        return snapshot

    def validate(self, root, context):
        from .printing import print_geometry
        issues = list(super().validate(root, context))
        _, components, _ = print_geometry(asset_objects(root), context)
        if components > 1:
            issues.append(ValidationIssue('cura_solid', 'INFO',
                'STL contains ' + str(components) + ' separate closed shells. Cura can slice separate printable shells; review placement, clearances, supports, and whether the parts are intended to print together.'))
        else:
            issues.append(ValidationIssue('cura_pose', 'INFO',
                'STL uses the evaluated current pose in millimetres; materials, rigs and animation are not needed. Check printer fit, wall thickness and supports in Cura.'))
        return tuple(issues)

    def write(self, options, root, context):
        from .printing import print_geometry, write_stl
        _, _, triangles = print_geometry(asset_objects(root), context)
        return write_stl(options['filepath'], triangles, context.scene.unit_settings.scale_length)


ADAPTERS = {'GODOT': GodotAdapter, 'UNITY': UnityAdapter, 'UNREAL': UnrealAdapter, 'CURA': CuraAdapter}


def get_adapter(target_key, **options):
    target = get_target(target_key)
    if target.key not in ADAPTERS:
        raise ValueError("Blender adapter not implemented for target: " + target.key)
    return ADAPTERS[target.key](**options)