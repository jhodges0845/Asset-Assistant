# SPDX-License-Identifier: GPL-3.0-or-later
"""Cross-provider Model JSON checkpoints verified in separate Blender processes."""
import json
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory

import bpy

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'tests' / 'blender'))


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def vertices(root):
    return [[float(c) for c in vertex.co] for obj in root.children
            if obj.type == 'MESH' for vertex in obj.data.vertices]


def verify(checkpoint):
    import blender_adapter as addon
    from blender_adapter.components import inspect_component
    from blender_adapter.modification import inspect_generated_asset
    addon.register()
    expected = json.loads(Path(str(checkpoint) + '.json').read_text(encoding='utf-8'))
    roots = [obj for obj in bpy.data.objects
             if obj.get('asset_assistant_asset_id') == expected['asset_id']]
    require(len(roots) == 1, 'Asset identity did not persist uniquely')
    root = roots[0]
    snapshot = inspect_generated_asset(root)
    require(root['object_type'] == expected['provider'], 'Provider changed')
    require(snapshot.owns_geometry, 'Generated geometry ownership was lost')
    require(len(snapshot.semantic_operations) == 1, 'Semantic operation was lost')
    require(root[expected['parameter']] == expected['value'], 'Parameter changed')
    require(vertices(root) == expected['vertices'], 'Applied geometry changed')
    component = inspect_component(root, expected['component_id'])
    require(component.owns_geometry, 'Component ownership was lost')
    require(component.attachment_target == 'asset_root', 'Attachment target changed')
    accessories = [obj for obj in root.children
                   if obj.get('asset_assistant_component_id') == expected['component_id']]
    require(len(accessories) == 1, 'Component parent attachment was lost')
    require(vertices(accessories[0]) == expected['accessory_vertices'], 'Component geometry changed')
    rigs = [obj for obj in root.children if obj.type == 'ARMATURE']
    require(len(rigs) == 1, 'Base rig was lost')
    for body in (obj for obj in root.children if obj.type == 'MESH'):
        require(any(mod.type == 'ARMATURE' and mod.object == rigs[0] for mod in body.modifiers),
                'Armature binding was lost')
        require(len(body.vertex_groups) > 0, 'Skin groups were lost')
    require('asset_assistant_model_preview_root' not in bpy.context.scene, 'Preview persisted')
    addon.unregister()
    print('Fresh-process acceptance passed: ' + expected['provider'])


def main():
    args = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
    if args:
        verify(Path(args[0]))
        return
    from test_model_json_acceptance import ModelJSONAcceptanceTests
    with TemporaryDirectory(prefix='asset-assistant-acceptance-') as directory:
        for key, target, profile in [('human', 'shoulders', 'broad'),
                                     ('quadruped', 'chest', 'broad'),
                                     ('avian', 'chest', 'powerful')]:
            checkpoint = Path(directory) / (key + '.blend')
            case = ModelJSONAcceptanceTests()
            case.setUp()
            try:
                case.prove(key, target, profile, combined=True, checkpoint=checkpoint)
            finally:
                case.tearDown()
            subprocess.run([bpy.app.binary_path, '--background', '--factory-startup',
                            str(checkpoint), '--python-exit-code', '1', '--python',
                            str(Path(__file__).resolve()), '--', str(checkpoint)],
                           check=True, timeout=180)
    print('All three cross-provider fresh-process checks passed')


if __name__ == '__main__':
    main()
