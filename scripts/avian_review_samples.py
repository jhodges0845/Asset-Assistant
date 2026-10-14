# SPDX-License-Identifier: GPL-3.0-or-later
"""Reproducible Avian review proportions, not an accepted production-shape catalog."""
from object_core.objects import get_provider
from scripts.anatomy_baseline import SAMPLES

AVIAN_REVIEW_SAMPLES = {
    'contrasting': SAMPLES['avian'],
    'compact-wide': dict(body_length_cm=30, body_width_cm=22, body_height_cm=18, wingspan_cm=65, tail_length_cm=14),
    'tall-narrow': dict(body_length_cm=38, body_width_cm=12, body_height_cm=30, wingspan_cm=90, tail_length_cm=20),
    'long-low': dict(body_length_cm=65, body_width_cm=18, body_height_cm=16, wingspan_cm=110, tail_length_cm=28),
    'short-wing': dict(wingspan_cm=45),
    'long-wing': dict(wingspan_cm=160),
    'small': dict(body_length_cm=18, body_width_cm=7, body_height_cm=8, wingspan_cm=35, tail_length_cm=8),
}


def review_values(name):
    values = {p.key:p.default for p in get_provider('avian').parameters}
    if name != 'default':
        values.update(AVIAN_REVIEW_SAMPLES[name])
    return values
