# SPDX-License-Identifier: GPL-3.0-or-later
"""Render matched before/after views of actual external Model JSON edits.

Run in a fresh Blender process with -- --output DIRECTORY.
Each provider keeps the same framing, lighting and scale across both states.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace

import bpy

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from blender_adapter.adapter import create_character
from blender_adapter.modification import inspect_generated_asset
from object_core.models import MeshPart
from object_core.objects import get_provider
from scripts import render_human_review as sheets


def source_evidence():
    paths = ['object_core/providers/' + name + '.py' for name in
             ('human_semantic', 'quadruped_semantic', 'semantic_geometry')]
    return dict(source_files_sha256={name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest()
                                     for name in paths},
                source_files_modified=bool(subprocess.check_output(
                    ['git','diff','HEAD','--name-only','--'] + paths, cwd=ROOT, text=True).strip()))


def capture(root):
    bodies = [obj for obj in root.children if obj.type == 'MESH']
    if len(bodies) != 1:
        raise RuntimeError('Review expects one generated body mesh')
    body = bodies[0]
    return MeshPart('body', tuple(tuple(float(c)*100 for c in v.co) for v in body.data.vertices),
                    tuple(tuple(p.vertices) for p in body.data.polygons))


def finished(result):
    if result != {'FINISHED'}:
        raise RuntimeError('Model JSON operator did not finish: ' + str(result))


def review(key, target, profile, output):
    import blender_adapter as addon
    sheets._clear_scene()
    addon.register()
    provider = get_provider(key)
    values = {field.key: field.default for field in provider.parameters}
    mesh = provider.mesh(values)
    root = create_character(mesh, scene=bpy.context.scene, skeleton=provider.skeleton(values),
                            skin_weights=provider.skin_weights(mesh, values))
    root['object_type'] = key
    for name, value in values.items():
        root[name] = value
    bpy.context.scene.humanoid_settings.target = root
    bpy.context.view_layer.objects.active = root
    root.select_set(True)
    before = capture(root)
    inspection = output / (key + '-inspection.json')
    request_file = output / (key + '-request.json')
    finished(bpy.ops.asset_assistant.modify_export_inspection(filepath=str(inspection)))
    document = json.loads(inspection.read_text(encoding='utf-8'))
    operation = dict(operation='shape', target=target, arguments=dict(profile=profile, amount=.6))
    request = dict(schema=document['request_template']['schema'],
                   asset_id=inspect_generated_asset(root).asset_id, provider_key=key,
                   parameter_changes={}, animation_export_names={}, component_operations=[],
                   semantic_operations=[operation])
    request_file.write_text(json.dumps(request, indent=2), encoding='utf-8')
    finished(bpy.ops.asset_assistant.modify_import_request(filepath=str(request_file)))
    finished(bpy.ops.asset_assistant.model_preview_imported())
    preview = capture(bpy.data.objects[bpy.context.scene['asset_assistant_model_preview_root']])
    if capture(root) != before:
        raise RuntimeError('Preview changed source geometry')
    finished(bpy.ops.asset_assistant.model_apply_previewed())
    after = capture(root)
    if after != preview or after == before:
        raise RuntimeError('Applied edit must match preview and differ from source')
    finished(bpy.ops.wm.save_as_mainfile(filepath=str(output / (key + '-applied.blend'))))
    addon.unregister()
    sheets._clear_scene()
    # Union bounds frame both states identically. The temporary union is replaced
    # before any render, retaining the shared camera and view positions.
    union = MeshPart('bounds', before.vertices + after.vertices, before.faces)
    args = SimpleNamespace(resolution_x=1600, resolution_y=600, samples=8,
                           modes=['clay', 'silhouette'])
    material = sheets._configure_scene(args, union)
    bodies = [obj for obj in bpy.context.scene.objects if obj.type == 'MESH']
    for label, part in [('before', before), ('after', after)]:
        for obj in bodies:
            obj.data.clear_geometry()
            obj.data.from_pydata(part.vertices, [], part.faces)
            obj.data.update()
        sheets._render_modes(args, material, output / (key + '-' + label + '.png'))
    report = dict(provider=key, parameters=values, operation=operation,
                  commit=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
                  blender=bpy.app.version_string, before_bounds_cm=sheets._bounds(before.vertices),
                  after_bounds_cm=sheets._bounds(after.vertices), preview_matches_apply=True,
                  max_vertex_displacement_cm=max(sum((a-b)**2 for a,b in zip(v,w))**.5
                                                 for v,w in zip(before.vertices, after.vertices)),
                  scope='Neutral semantic-only comparison; no artistic sign-off or deformation proof.')
    report.update(source_evidence())
    (output / (key + '-review.json')).write_text(json.dumps(report, indent=2), encoding='utf-8')



def write_gallery(output, providers=('human', 'quadruped', 'avian')):
    cards = []
    for key, title in [('human', 'Human shoulders'), ('quadruped', 'Canine chest'),
                       ('avian', 'Avian chest')]:
        if key not in providers:
            continue
        cards.append('<section><h2>' + title + '</h2><p><a href="' + key +
                     '-applied.blend">Applied Blender scene</a> | <a href="' + key +
                     '-review.json">Parameters and evidence</a></p>')
        for label in ['before', 'after']:
            cards.append('<h3>' + label.title() + '</h3><img alt="' + title + ' ' + label +
                         '" src="' + key + '-' + label + '.png" data-base="' + key + '-' + label + '">')
        cards.append('</section>')
    page = '''<!doctype html><meta charset="utf-8"><title>Model JSON visual review</title>
<style>body{margin:32px auto;max-width:1500px;padding:0 24px;background:#20262c;color:#edf1f4;font:17px system-ui}
a{color:#9ed9ff}img{width:100%;display:block}section{margin:40px 0}button{font:inherit;padding:8px 16px;margin-right:10px}
h3{margin-bottom:8px}p{line-height:1.5}</style>
<h1>Model JSON before / after</h1>
<p>Actual exported/imported semantic edits. Each pair shares framing, lighting and scale.
Neutral geometry only; artistic acceptance and deformation review remain open.</p>
<button onclick="mode('')">Clay</button><button onclick="mode('_silhouette')">Silhouette</button>
<script>function mode(s){document.querySelectorAll('img').forEach(i=>i.src=i.dataset.base+s+'.png')}</script>
''' + ''.join(cards)
    (output / 'index.html').write_text(page, encoding='utf-8')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--providers', nargs='+', choices=('human','quadruped','avian'),
                        default=['human','quadruped','avian'])
    args = parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    for case in [('human', 'shoulders', 'broad'), ('quadruped', 'chest', 'broad'),
                 ('avian', 'chest', 'powerful')]:
        if case[0] in args.providers:
            review(*case, output)
    write_gallery(output, args.providers)


if __name__ == '__main__':
    main()
