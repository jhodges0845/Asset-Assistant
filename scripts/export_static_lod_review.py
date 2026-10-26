# SPDX-License-Identifier: GPL-3.0-or-later
"""Blender background fixture for review_static_lod_godot.gd; output must be new."""
from pathlib import Path
import sys
import bpy
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from blender_adapter.lod_sets import preview_static_lod_set
from blender_adapter.lod_export import export_static_lod_bundle


def main():
    destination = Path(sys.argv[sys.argv.index('--') + 1]).resolve()
    sources = []
    for index in range(2):
        bpy.ops.mesh.primitive_uv_sphere_add(segments=24, ring_count=12,
                                           location=(index * 3, 0, 1))
        obj = bpy.context.object
        obj.name = 'LOD fixture %d' % index
        obj.data.materials.append(bpy.data.materials.new('Fixture material %d' % index))
        sources.append(obj)
    preview = preview_static_lod_set(sources, bpy.context.scene)
    preview.apply()
    export_static_lod_bundle(preview.record, bpy.context, destination)
    (destination / 'project.godot').write_text('[application]\nconfig/name="LOD exchange review"\n')


if __name__ == '__main__':
    main()
