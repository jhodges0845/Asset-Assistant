# SPDX-License-Identifier: GPL-3.0-or-later
"""Host-independent triangle budgets for explicit LOD preview workflows."""
from dataclasses import dataclass
from math import isfinite


@dataclass(frozen=True)
class LODLevel:
    index: int
    ratio: float
    triangle_budget: int


def plan_lods(source_triangles, ratios=(.5, .25)):
    if isinstance(source_triangles, bool) or not isinstance(source_triangles, int) or source_triangles < 8:
        raise ValueError("LOD source must contain at least eight triangles")
    ratios = tuple(ratios)
    if not 1 <= len(ratios) <= 4:
        raise ValueError("Choose between one and four LOD levels")
    levels = []
    previous = source_triangles
    for index, ratio in enumerate(ratios, 1):
        if isinstance(ratio, bool) or not isinstance(ratio, (int, float)) or not isfinite(ratio) or not 0 < ratio < 1:
            raise ValueError("LOD ratios must be finite numbers between zero and one")
        budget = max(4, int(source_triangles * ratio))
        if budget >= previous:
            raise ValueError("Each LOD must have a smaller triangle budget")
        levels.append(LODLevel(index, float(ratio), budget))
        previous = budget
    return tuple(levels)
