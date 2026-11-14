# SPDX-License-Identifier: GPL-3.0-or-later
"""Exercise Blender package operators in a disposable user environment.

Run with Blender --background --factory-startup --python-exit-code 1.
This is automated lifecycle coverage, not live Preferences UI acceptance.
"""
from pathlib import Path
import os
import subprocess
import sys
import tempfile

import bpy

ROOT = Path(__file__).resolve().parents[1]


def worker(archive, isolated):
    import addon_utils
    isolated = Path(isolated).resolve()
    scripts = Path(bpy.utils.user_resource('SCRIPTS', create=True)).resolve()
    scripts.relative_to(isolated)  # Fail before any install/remove outside isolation.
    Path(bpy.utils.user_resource('CONFIG', create=True)).resolve().relative_to(isolated)
    sys.path[:] = [entry for entry in sys.path
                   if Path(entry or '.').resolve() not in (ROOT, ROOT / 'scripts')]
    assert 'humanoid_blender' not in sys.modules
    assert 'object_core' not in sys.modules
    installed = scripts / 'addons' / 'humanoid_blender'
    assert not installed.exists()
    assert bpy.ops.preferences.addon_install(filepath=archive, overwrite=True) == {'FINISHED'}
    assert installed.is_dir()
    assert bpy.ops.preferences.addon_enable(module='humanoid_blender') == {'FINISHED'}
    addon = sys.modules['humanoid_blender']
    Path(addon.__file__).resolve().relative_to(installed.resolve())
    assert addon_utils.check('humanoid_blender') == (True, True)
    assert bpy.ops.humanoid.generate_blockout() == {'FINISHED'}
    asset = bpy.context.view_layer.objects.active
    meshes = tuple(obj for obj in asset.children if obj.type == 'MESH')
    assert meshes
    geometry = {obj: tuple(tuple(v.co) for v in obj.data.vertices) for obj in meshes}
    metadata = dict(asset.items())

    def preserved():
        assert bpy.data.objects.get(asset.name) == asset
        assert dict(asset.items()) == metadata
        for obj, vertices in geometry.items():
            assert obj.parent == asset
            assert tuple(tuple(v.co) for v in obj.data.vertices) == vertices

    for _ in range(2):
        assert bpy.ops.preferences.addon_disable(module='humanoid_blender') == {'FINISHED'}
        assert addon_utils.check('humanoid_blender') == (False, False)
        assert not hasattr(bpy.types.Scene, 'humanoid_settings')
        preserved()
        assert bpy.ops.preferences.addon_enable(module='humanoid_blender') == {'FINISHED'}
        assert addon_utils.check('humanoid_blender') == (True, True)
        preserved()

    # Same-build replacement exercises overwrite/registration, not version migration.
    assert bpy.ops.preferences.addon_install(filepath=archive, overwrite=True) == {'FINISHED'}
    assert bpy.ops.preferences.addon_enable(module='humanoid_blender') == {'FINISHED'}
    assert addon_utils.check('humanoid_blender') == (True, True)
    preserved()
    assert hasattr(bpy.types.Scene, 'humanoid_settings')
    installed.resolve().relative_to(isolated)
    # Blender's remove operator redraws its area, even when run headlessly.
    area = next(iter(bpy.context.screen.areas))
    with bpy.context.temp_override(area=area):
        assert bpy.ops.preferences.addon_remove(module='humanoid_blender') == {'FINISHED'}
    assert not installed.exists()
    assert 'humanoid_blender' not in bpy.context.preferences.addons
    assert not hasattr(bpy.types.Scene, 'humanoid_settings')
    preserved()
    print('PACKAGED_INSTALL_LIFECYCLE_OK: install, replacement, disable/re-enable, uninstall and scene preservation')


args = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
if args and args[0] == '--worker':
    worker(args[1], args[2])
else:
    with tempfile.TemporaryDirectory(prefix='asset-assistant-install-') as directory:
        sandbox = Path(directory).resolve()
        env = os.environ.copy()
        for key, folder in (('BLENDER_USER_SCRIPTS', 'scripts'),
                            ('BLENDER_USER_CONFIG', 'config'),
                            ('BLENDER_USER_DATAFILES', 'datafiles'),
                            ('BLENDER_USER_EXTENSIONS', 'extensions')):
            path = sandbox / folder
            path.mkdir()
            env[key] = str(path)
        result = subprocess.run([bpy.app.binary_path, '--background', '--factory-startup',
                                 '--python-exit-code', '1', '--python', str(Path(__file__).resolve()),
                                 '--', '--worker', str(ROOT / 'dist' / 'asset_assistant.zip'), str(sandbox)],
                                env=env, capture_output=True, text=True, timeout=180)
        print(result.stdout)
        print(result.stderr)
        if result.returncode != 0:
            raise RuntimeError('Isolated installer lifecycle failed: ' + str(result.returncode))
        assert 'PACKAGED_INSTALL_LIFECYCLE_OK' in result.stdout
