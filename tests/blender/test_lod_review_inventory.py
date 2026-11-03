# SPDX-License-Identifier: GPL-3.0-or-later
"""Review diagnostics must reject missing or malformed UV export data."""
import json
import struct
import pytest
from scripts.export_avian_lod_review import exported_surface_inventory


def write_fixture(path, *, missing_uv=False, nonfinite=False, wrong_count=False, short_view=False):
    uv = struct.pack('<6f', 0, 0, 1, 0, 0, float('nan') if nonfinite else 1)
    attributes = {'POSITION': 0}
    if not missing_uv:
        attributes['TEXCOORD_0'] = 1
    doc = {'meshes': [{'primitives': [{'attributes': attributes, 'indices': 2, 'material': 0}]}],
           'materials': [{'name': 'Checker'}],
           'accessors': [{'count': 3}, {'count': 2 if wrong_count else 3,
               'type': 'VEC2', 'componentType': 5126, 'bufferView': 0}, {'count': 3}],
           'bufferViews': [{'buffer': 0, 'byteLength': 8 if short_view else len(uv)}]}
    payload = json.dumps(doc).encode()
    payload += b' ' * (-len(payload) % 4)
    path.write_bytes(struct.pack('<4sII', b'glTF', 2, 28 + len(payload) + len(uv)) +
                     struct.pack('<II', len(payload), 0x4E4F534A) + payload +
                     struct.pack('<II', len(uv), 0x004E4942) + uv)


def test_surface_inventory_reports_uv_and_material(tmp_path):
    path = tmp_path / 'surface.glb'
    write_fixture(path)
    assert exported_surface_inventory(path) == [{'material': 'Checker', 'triangles': 1,
        'uv_vertices': 3, 'uv_min': [0, 0], 'uv_max': [1, 1]}]


@pytest.mark.parametrize('fault', ('missing_uv', 'nonfinite', 'wrong_count', 'short_view'))
def test_surface_inventory_rejects_uv_loss(tmp_path, fault):
    path = tmp_path / 'surface.glb'
    write_fixture(path, **{fault: True})
    with pytest.raises((KeyError, ValueError)):
        exported_surface_inventory(path)
