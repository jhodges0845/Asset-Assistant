# SPDX-License-Identifier: GPL-3.0-or-later
"""Fractional gait endpoints and contact survive the real GLB export path."""
import math
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
try:
    import bpy
except ModuleNotFoundError:
    bpy = None

from blender_adapter.adapter import create_character
from blender_adapter.animation import add_idle, add_locomotion, add_run, set_clip_export_name
from blender_adapter.materials import prepare_materials
from blender_adapter.targets import get_adapter
from object_core.objects import get_provider


@unittest.skipIf(bpy is None, 'requires Blender')
class CanineGLBPlaybackTests(unittest.TestCase):
    def setUp(self):
        self.previous = bpy.context.window.scene
        self.before = {name: set(getattr(bpy.data, name)) for name in
                       ('objects', 'meshes', 'armatures', 'collections', 'materials', 'images', 'actions')}
        self.scene = bpy.data.scenes.new('CanineGLBPlayback')
        bpy.context.window.scene = self.scene
        self.scene.render.fps = 24
        self.scene.render.fps_base = 1
        self.scene.frame_start = 1

    def tearDown(self):
        bpy.context.window.scene = self.previous
        bpy.data.scenes.remove(self.scene)
        for name, before in self.before.items():
            data = getattr(bpy.data, name)
            for item in set(data) - before:
                data.remove(item, do_unlink=True)

    def test_owned_clip_library_retains_fractional_duration_contact_and_loop(self):
        provider = get_provider('quadruped')
        values = {p.key: p.default for p in provider.parameters}
        mesh = provider.mesh(values)
        root = create_character(mesh, scene=self.scene, skeleton=provider.skeleton(values),
                                skin_weights=provider.skin_weights(mesh, values))
        root['object_type'] = 'quadruped'
        for key, value in values.items():
            root[key] = value
        prepare_materials(root)
        add_idle(root, self.scene, 4., 1.)
        add_locomotion(root, self.scene, 1.2, 1.)
        add_run(root, self.scene, .64, 1.)
        set_clip_export_name(root, 'Walk', 'CanineStep')
        source_rig = next(o for o in root.children if o.type == 'ARMATURE')
        active_action = source_rig.animation_data.action
        # An unassociated action must not leak into a single-armature export.
        unrelated = active_action.copy()
        unrelated.name = 'UnrelatedCanineRun'
        for key in tuple(unrelated.keys()):
            del unrelated[key]
        before_actions = set(bpy.data.actions)
        before_objects = set(bpy.data.objects)
        with TemporaryDirectory() as directory:
            path = Path(directory) / 'canine.glb'
            result = get_adapter('GODOT', asset_use='ANIMATED').export(root, bpy.context, path)
            self.assertTrue(result.success, result.issues)
            self.assertIs(source_rig.animation_data.action, active_action)
            self.assertEqual(len(source_rig.animation_data.nla_tracks), 0)
            bpy.ops.import_scene.gltf(filepath=str(path))
        imported = set(bpy.data.objects) - before_objects
        rig = next(o for o in imported if o.type == 'ARMATURE')
        # Importers also allocate unlinked bone-display helper meshes.
        bodies = [o for o in imported if o.type == 'MESH' and any(
            m.type == 'ARMATURE' and m.object == rig for m in o.modifiers)]
        self.assertEqual(len(bodies), 1)
        actions = set(bpy.data.actions) - before_actions
        self.assertEqual(len(actions), 3)
        for label, duration in (('CanineStep', 1.2), ('Run', .64)):
            with self.subTest(clip=label):
                action = next(a for a in actions if a.name.startswith(label))
                self.assertAlmostEqual((action.frame_range[1] - action.frame_range[0]) / 24,
                                       duration, places=6)
                rig.animation_data.action = action
                rig.animation_data.action_slot = action.slots[0]
                first = None
                movement = 0.
                minimum = float('inf')
                for step in range(18):
                    frame = action.frame_range[0] + duration * 24 * step / 17
                    self.scene.frame_set(math.floor(frame), subframe=frame % 1)
                    bpy.context.view_layer.update()
                    body = bodies[0].evaluated_get(bpy.context.evaluated_depsgraph_get())
                    points = [body.matrix_world @ v.co for v in body.data.vertices]
                    minimum = min(minimum, min(p.z * 100 for p in points))
                    if first is None:
                        first = points
                    movement = max(movement, max((a-b).length for a,b in zip(first, points)))
                self.assertGreater(movement, .001)
                self.assertGreater(minimum, 0)
                self.assertLess(max((a-b).length for a,b in zip(first, points)) * 100, .001)
