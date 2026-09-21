# SPDX-License-Identifier: GPL-3.0-or-later
"""Verify generated animation libraries survive engine export."""

import json
from pathlib import Path
import struct
from tempfile import TemporaryDirectory
import unittest

try:
    import bpy
except ModuleNotFoundError:
    bpy = None

from blender_adapter.adapter import create_character
from blender_adapter.animation import (
    action_curves,
    add_idle,
    add_locomotion,
    activate_generated_action,
    clip_export_name,
    generated_action,
    generated_actions,
    set_clip_export_name,
)
from blender_adapter.materials import prepare_materials
from blender_adapter.self_rigged_accessory import create_self_rigged_gauntlet
from blender_adapter.targets import _stage_generated_animation_tracks, asset_objects, get_adapter
from blender_adapter.workflow import add_basic_rig
from object_core.objects import get_provider


def read_glb(path):
    data = Path(path).read_bytes()
    magic, version, length = struct.unpack_from('<4sII', data)
    assert magic == b'glTF' and version == 2 and length == len(data)
    size, kind = struct.unpack_from('<II', data, 12)
    assert kind == 0x4E4F534A
    return json.loads(data[20:20 + size].decode('utf8'))


def animation_duration(document, animation):
    """Return the longest exported animation input time in seconds."""
    accessors = document['accessors']
    maxima = []
    for sampler in animation.get('samplers', []):
        accessor = accessors[sampler['input']]
        values = accessor.get('max', ())
        if values:
            maxima.append(float(values[0]))
    if not maxima:
        raise AssertionError('Exported animation has no time accessor maxima.')
    return max(maxima)


@unittest.skipIf(bpy is None, 'requires Blender; use scripts/test_blender.py')
class AnimationExportTests(unittest.TestCase):
    def setUp(self):
        self.previous_scene = bpy.context.window.scene
        self.before = {name: set(getattr(bpy.data, name)) for name in
                       ('objects', 'meshes', 'armatures', 'collections', 'materials', 'images', 'actions')}
        self.scene = bpy.data.scenes.new('AnimationExportTest')
        bpy.context.window.scene = self.scene
        provider = get_provider('human')
        values = {field.key: field.default for field in provider.parameters}
        self.root = create_character(provider.mesh(values), name='AnimatedHuman', scene=self.scene)
        self.root['object_type'] = provider.key
        for key, value in values.items():
            self.root[key] = value
        self.rig = add_basic_rig(self.root, bpy.context)
        prepare_materials(self.root)
        generated_images = set(bpy.data.images) - self.before['images']
        self.assertTrue(generated_images)
        self.assertTrue(all(image.packed_file or getattr(image, 'packed_files', ())
                            for image in generated_images))
        self.temp = TemporaryDirectory()

    def tearDown(self):
        if bpy.context.mode != 'OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT')
        bpy.context.window.scene = self.previous_scene
        bpy.data.scenes.remove(self.scene)
        for name, original in self.before.items():
            data = getattr(bpy.data, name)
            for item in set(data) - original:
                data.remove(item, do_unlink=True)
        self.temp.cleanup()

    def _generate_library(self):
        add_idle(self.root, self.scene)
        add_locomotion(self.root, self.scene)
        return activate_generated_action(self.root, 'Idle')

    def test_generated_clips_define_every_bone_rotation(self):
        self._generate_library()
        expected = {bone.path_from_id('rotation_quaternion') for bone in self.rig.pose.bones}
        self.assertTrue(expected)

        for clip_name in ('Idle', 'Walk'):
            action = generated_action(self.root, clip_name)
            self.assertIsNotNone(action)
            slot = action.slots[0] if hasattr(action, 'slots') and len(action.slots) else None
            paths = {curve.data_path for curve in action_curves(action, slot)}
            self.assertTrue(expected.issubset(paths),
                            clip_name + ' must explicitly define every bone rotation to prevent cross-clip pose leakage.')

    def test_generated_actions_ignore_stale_action_with_reused_rig_name(self):
        self._generate_library()
        self.assertTrue(self.rig.get('asset_assistant_rig_id'))
        stale = bpy.data.actions.new('Stale.Rig.Idle')
        stale['asset_assistant_generated'] = True
        stale['asset_assistant_rig'] = self.rig.name
        stale['asset_assistant_rig_id'] = 'stale-deleted-rig'
        stale['asset_assistant_clip'] = 'Idle'

        owned = generated_actions(self.root)

        self.assertNotIn(stale, owned)
        self.assertEqual({action.get('asset_assistant_clip') for action in owned}, {'Idle', 'Walk'})

    def test_component_owned_rig_does_not_disable_base_clip_staging(self):
        active = self._generate_library()
        component_root, _record = create_self_rigged_gauntlet(self.root)
        component_rig = next(child for child in component_root.children if child.type == 'ARMATURE')
        component_action = component_rig.animation_data.action
        self.assertIsNotNone(component_action)
        self.assertTrue(component_action.get('asset_assistant_component_animation'))
        self.assertEqual(2, len([obj for obj in asset_objects(self.root) if obj.type == 'ARMATURE']))

        with _stage_generated_animation_tracks(self.root) as staged:
            self.assertTrue(staged)
            self.assertEqual({'Idle', 'Walk'}, {track.name for track in self.rig.animation_data.nla_tracks})
            self.assertIs(component_rig.animation_data.action, component_action)
            self.assertEqual(0, len(component_rig.animation_data.nla_tracks))

        self.assertIs(self.rig.animation_data.action, active)
        self.assertEqual(0, len(self.rig.animation_data.nla_tracks))
        self.assertIs(component_rig.animation_data.action, component_action)

    def test_all_generated_clips_are_exported_to_glb(self):
        active = self._generate_library()
        adapter = get_adapter('GODOT', asset_use='ANIMATED')
        path = Path(self.temp.name) / 'library.glb'

        result = adapter.export(self.root, bpy.context, path)

        self.assertTrue(result.success, result.issues)
        document = read_glb(result.filepath)
        animations = document.get('animations', [])
        self.assertEqual(len(animations), 2)
        self.assertEqual({animation.get('name') for animation in animations}, {'Idle', 'Walk'})
        durations = sorted(animation_duration(document, animation) for animation in animations)
        self.assertAlmostEqual(durations[0], 1.2, delta=0.05)
        self.assertAlmostEqual(durations[1], 4.0, delta=0.05)
        self.assertIs(self.rig.animation_data.action, active)
        self.assertEqual(len(self.rig.animation_data.nla_tracks), 0)

    def test_artist_export_name_is_written_to_glb(self):
        self._generate_library()
        action = set_clip_export_name(self.root, 'Walk', 'Sneak')
        self.assertEqual(clip_export_name(action), 'Sneak')
        adapter = get_adapter('GODOT', asset_use='ANIMATED')
        path = Path(self.temp.name) / 'renamed.glb'

        result = adapter.export(self.root, bpy.context, path)

        self.assertTrue(result.success, result.issues)
        names = {animation.get('name') for animation in read_glb(result.filepath).get('animations', [])}
        self.assertEqual(names, {'Idle', 'Sneak'})

    def test_all_generated_clips_are_named_in_unity_fbx(self):
        active = self._generate_library()
        adapter = get_adapter('UNITY', asset_use='ANIMATED')
        path = Path(self.temp.name) / 'library.fbx'

        result = adapter.export(self.root, bpy.context, path)

        self.assertTrue(result.success, result.issues)
        payload = Path(result.filepath).read_bytes()
        self.assertIn(b'Idle', payload)
        self.assertIn(b'Walk', payload)
        self.assertIs(self.rig.animation_data.action, active)
        self.assertEqual(len(self.rig.animation_data.nla_tracks), 0)

    def test_unreal_writes_model_and_one_fbx_per_generated_clip(self):
        active = self._generate_library()
        adapter = get_adapter('UNREAL', asset_use='ANIMATED')
        path = Path(self.temp.name) / 'Human_Unreal.fbx'
        mesh_names = tuple(obj.name.encode('utf8') for obj in asset_objects(self.root) if obj.type == 'MESH')

        result = adapter.export(self.root, bpy.context, path)

        self.assertTrue(result.success, result.issues)
        model = Path(result.filepath)
        idle = model.with_name(model.stem + '_Idle.fbx')
        walk = model.with_name(model.stem + '_Walk.fbx')
        for exported in (model, idle, walk):
            self.assertTrue(exported.is_file())
            self.assertGreater(exported.stat().st_size, 0)

        model_payload = model.read_bytes()
        self.assertTrue(mesh_names)
        for name in mesh_names:
            self.assertIn(name, model_payload)
        self.assertIn(self.rig.name.encode('utf8'), model_payload)
        self.assertIn(b'Geometry', model_payload)
        self.assertIn(b'Deformer', model_payload)
        self.assertIn(b'Cluster', model_payload)

        idle_payload = idle.read_bytes()
        walk_payload = walk.read_bytes()
        for payload in (idle_payload, walk_payload):
            self.assertIn(self.rig.name.encode('utf8'), payload)
            self.assertIn(b'Geometry', payload)
            self.assertIn(b'Deformer', payload)
            self.assertIn(b'Cluster', payload)
            self.assertIn(b'AnimationStack', payload)
            self.assertIn(b'AnimationCurve', payload)
            for name in mesh_names:
                self.assertIn(name, payload)
        self.assertFalse(idle.with_suffix('.fbm').exists())
        self.assertFalse(walk.with_suffix('.fbm').exists())
        self.assertIs(self.rig.animation_data.action, active)
        self.assertEqual(len(self.rig.animation_data.nla_tracks), 0)


if __name__ == '__main__':
    unittest.main()
