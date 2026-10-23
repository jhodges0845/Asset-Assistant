# SPDX-License-Identifier: GPL-3.0-or-later
"""Validate a fresh Human clip-library file opened in Blender background mode.

Usage: blender --background library.blend --python scripts/verify_human_clip_library.py
This switches Actions in memory without saving or modifying the file on disk.
"""
import sys, math
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import bpy
from blender_adapter.animation import generated_actions,activate_generated_action
scene=bpy.context.scene
root=next(o for o in scene.objects if o.get('object_type')=='human')
assert {a.get('asset_assistant_clip') for a in generated_actions(root)}=={'Idle','Walk','Run'}
rig=next(o for o in root.children if o.type=='ARMATURE')
body=next(o for o in root.children if o.type=='MESH')
for label in ('Walk','Idle','Run','Idle'):
 action=activate_generated_action(root,label)
 first=None
 for step in range(34):
  frame=action.frame_range[0]+(action.frame_range[1]-action.frame_range[0])*step/33
  scene.frame_set(math.floor(frame),subframe=frame%1)
  obj=body.evaluated_get(bpy.context.evaluated_depsgraph_get())
  points=[obj.matrix_world@v.co for v in obj.data.vertices]
  assert all(math.isfinite(c) for p in points for c in p)
  if label=='Idle':assert rig.pose.bones['root'].location.length<1e-8
  if first is None:first=points
  if label!='Idle':assert min(p.z for p in points)>0
 assert max((a-b).length for a,b in zip(first,points))<.00001
 print('REOPEN_CLIP_OK',label,flush=True)
print('HUMAN_LIBRARY_REOPEN_OK',flush=True)
