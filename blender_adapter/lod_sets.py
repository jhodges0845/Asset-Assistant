# SPDX-License-Identifier: GPL-3.0-or-later
"""Transactional orchestration of existing static LOD previews."""
from dataclasses import dataclass
import bpy
from object_core.lod import plan_lods
from .lod import _validate_source, _triangles, preview_static_lods, recover_static_lod_preview


@dataclass
class StaticLODSet:
    previews: tuple
    state: str = 'PREVIEW'
    record: object = None

    def _check_record(self):
        if self.record is not None:
            if self.record.get('lod_set_state') != 'PREVIEW':
                raise ValueError('Only an active LOD set can be changed')
            if self.record.get('lod_set_count') != len(self.previews):
                raise ValueError('LOD set member count changed; preserve remaining previews')
            if self.record.objects or self.record.children:
                raise ValueError('LOD set record contains artist data; preserve it before rebuilding')
            if tuple(self.record.get('member_' + str(i)) for i in range(len(self.previews))) != tuple(p.collection for p in self.previews):
                raise ValueError('LOD set membership changed; preserve remaining previews')

    def apply(self):
        if self.state != 'PREVIEW':
            raise ValueError('Only an active LOD set can be applied')
        self._check_record()
        # Validate every member before any member changes state.
        for preview in self.previews:
            preview.validate_apply()
        result = tuple(preview.apply() for preview in self.previews)
        self.state = 'APPLIED'
        if self.record is not None:
            self.record['lod_set_state'] = 'APPLIED'
        return result

    def cancel(self):
        if self.state != 'PREVIEW':
            raise ValueError('Only an active LOD set can be cancelled')
        self._check_record()
        for preview in self.previews:
            if preview.state != 'PREVIEW':
                raise ValueError('A member was already resolved; preserve remaining previews')
            preview._check_structure()
        if self.record is not None:
            bpy.data.collections.remove(self.record)
        for preview in self.previews:
            preview.cancel()
        self.state = 'CANCELLED'


def preview_static_lod_set(sources, scene, ratios=(.5, .25)):
    """Build all members or remove all staged copies on failure.

    Budgets apply per mesh. This explicit source list does not infer asset
    ownership or include children. Individual previews retain their saved IDs;
    a separate saved record retains grouping without defining an export hierarchy.
    """
    sources = tuple(sources)
    ratios = tuple(ratios)
    if not sources or len(set(sources)) != len(sources):
        raise ValueError('Choose a nonempty set of distinct static meshes')
    if scene != bpy.context.scene:
        raise ValueError('LOD preview requires the active scene')
    for source in sources:
        _validate_source(source)
        if scene.objects.get(source.name) != source:
            raise ValueError('Every LOD source must belong to the active scene')
        plan_lods(_triangles(source.data), ratios)
    previews = []
    record = None
    try:
        for source in sources:
            previews.append(preview_static_lods(source, scene, ratios))
        record = bpy.data.collections.new('Static LOD Set')
        scene.collection.children.link(record)
        record['lod_set_version'] = 1
        record['lod_set_state'] = 'PREVIEW'
        record['lod_set_count'] = len(previews)
        for index, preview in enumerate(previews):
            record['member_' + str(index)] = preview.collection
    except Exception:
        if record is not None:
            bpy.data.collections.remove(record)
        for preview in reversed(previews):
            preview.cancel()
        raise
    return StaticLODSet(tuple(previews), record=record)


def recover_static_lod_set(record):
    """Recover explicit member IDs without guessing from names or selection."""
    if record.get('lod_set_version') != 1 or record.get('lod_set_state') != 'PREVIEW':
        raise ValueError('Choose a supported active LOD set')
    count = record.get('lod_set_count')
    if not isinstance(count, int) or count < 1:
        raise ValueError('LOD set member count is invalid')
    members = tuple(record.get('member_' + str(index)) for index in range(count))
    if any(not isinstance(member, bpy.types.Collection) for member in members) or len(set(members)) != count:
        raise ValueError('LOD set members are missing or duplicated; preserve remaining previews')
    previews = tuple(recover_static_lod_preview(member) for member in members)
    group = StaticLODSet(previews, record=record)
    group._check_record()
    return group
