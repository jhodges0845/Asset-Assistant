# SPDX-License-Identifier: GPL-3.0-or-later
"""Transactional orchestration of existing static LOD previews."""
from dataclasses import dataclass
import bpy
from object_core.lod import plan_lods
from .lod import _validate_source, _triangles, preview_static_lods


@dataclass
class StaticLODSet:
    previews: tuple
    state: str = 'PREVIEW'

    def apply(self):
        if self.state != 'PREVIEW':
            raise ValueError('Only an active LOD set can be applied')
        # Validate every member before any member changes state.
        for preview in self.previews:
            preview.validate_apply()
        result = tuple(preview.apply() for preview in self.previews)
        self.state = 'APPLIED'
        return result

    def cancel(self):
        if self.state != 'PREVIEW':
            raise ValueError('Only an active LOD set can be cancelled')
        for preview in self.previews:
            if preview.state != 'PREVIEW':
                raise ValueError('A member was already resolved; preserve remaining previews')
            preview._check_structure()
        for preview in self.previews:
            preview.cancel()
        self.state = 'CANCELLED'


def preview_static_lod_set(sources, scene, ratios=(.5, .25)):
    """Build all members or remove all staged copies on failure.

    Budgets apply per mesh. This explicit source list does not infer asset
    ownership or include children. Individual previews retain their saved IDs;
    the grouping handle is session-local and is not an export LOD hierarchy.
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
    try:
        for source in sources:
            previews.append(preview_static_lods(source, scene, ratios))
    except Exception:
        for preview in reversed(previews):
            preview.cancel()
        raise
    return StaticLODSet(tuple(previews))
