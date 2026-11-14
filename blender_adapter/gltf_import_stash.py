# SPDX-License-Identifier: GPL-3.0-or-later
"""Persist import-time NLA provenance; never infer it from track names alone."""
import json
from uuid import uuid4

_STASH = 'asset_assistant_gltf_import_stash'
_ACTION = 'asset_assistant_gltf_import_action'


def _scalar_state(value):
    # Capture every scalar RNA setting, including timing, blending and slots.
    # Selection/active flags are editor navigation, not animation arrangement.
    return {prop.identifier: getattr(value, prop.identifier)
            for prop in value.bl_rna.properties
            if prop.type in {'BOOLEAN', 'INT', 'FLOAT', 'STRING', 'ENUM'}
            and not getattr(prop, 'is_array', False) and prop.identifier not in {'select', 'active'}
            and isinstance(getattr(value, prop.identifier), (bool, int, float, str))}


def _snapshot(obj):
    data = obj.animation_data
    if data is None or not data.nla_tracks or data.drivers or data.use_tweak_mode:
        return None
    tracks = []
    for track in data.nla_tracks:
        if not track.mute or not track.lock or track.is_solo or len(track.strips) != 1:
            return None
        strip = track.strips[0]
        action = strip.action
        if action is None or strip.mute or not action.get(_ACTION):
            return None
        if strip.modifiers or strip.fcurves:
            return None
        tracks.append({'track': _scalar_state(track), 'strip': _scalar_state(strip),
                       'action': [action.name, action.get(_ACTION)],
                       'range': list(action.frame_range)})
    if data.action is not None and not any(
        strip.action == data.action and strip.action_slot == data.action_slot
        for track in data.nla_tracks for strip in track.strips
    ):
        return None
    settings = {key: getattr(data, key) for key in
                ('use_nla', 'action_blend_type', 'action_extrapolation', 'action_influence')}
    return json.dumps({'version': 1, 'tracks': tracks, 'settings': settings}, sort_keys=True)


def record_import_stashes(objects, new_actions):
    """Called only after successful glTF import, on newly created data."""
    for action in new_actions:
        action[_ACTION] = uuid4().hex
    for obj in objects:
        snapshot = _snapshot(obj)
        if snapshot is not None:
            obj[_STASH] = snapshot


def has_unchanged_import_stash(obj):
    """Fail closed after edits, missing provenance or unsupported arrangements."""
    stored = obj.get(_STASH)
    return isinstance(stored, str) and stored == _snapshot(obj)


def has_import_stash_record(obj):
    return _STASH in obj
