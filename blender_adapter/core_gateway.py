# SPDX-License-Identifier: GPL-3.0-or-later
"""Resolve host-independent contracts and providers in a ZIP or checkout."""
from importlib import import_module
from importlib.util import find_spec

_bundled_name = __package__ + '.object_core'
_core_name = _bundled_name if find_spec(_bundled_name) is not None else 'object_core'
_core = import_module(_core_name)
ObjectMesh = _core.ObjectMesh
Skeleton = _core.Skeleton
AssetSnapshot = import_module(_core_name + '.models.validation').AssetSnapshot
validate_asset = import_module(_core_name + '.validation').validate_asset
_objects = import_module(_core_name + '.objects')
OBJECT_TYPES = _objects.OBJECT_TYPES
canonical_provider_key = _objects.canonical_provider_key
get_provider = _objects.get_provider

ValidationIssue = import_module(_core_name + '.models.validation').ValidationIssue
_targets = import_module(_core_name + '.targets')
get_target = _targets.get_target
validate_for_target = _targets.validate_for_target

_components = import_module(_core_name + '.components')
AttachmentMode = _components.AttachmentMode
ComponentBehavior = _components.ComponentBehavior
ComponentKind = _components.ComponentKind
ComponentRecord = _components.ComponentRecord
PhysicsIntent = _components.PhysicsIntent
RigBinding = _components.RigBinding
component_document = _components.component_document
component_from_document = _components.component_from_document
effective_behavior = _components.effective_behavior
validate_component = _components.validate_component
_component_primitives = import_module(_core_name + '.component_primitives')
hair_shell_mesh = _component_primitives.hair_shell_mesh
ring_mesh = _component_primitives.ring_mesh
_human_hair = import_module(_core_name + '.providers.human_hair')
fit_parent_skinned_hair = _human_hair.fit_parent_skinned_hair
_human_clothing = import_module(_core_name + '.providers.human_clothing')
basic_shirt_mesh = _human_clothing.basic_shirt_mesh
basic_shirt_weights = _human_clothing.basic_shirt_weights

_animations = import_module(_core_name + '.animations')
AnimationRecord = _animations.AnimationRecord
AnimationSource = _animations.AnimationSource
RootMotionIntent = _animations.RootMotionIntent
animation_document = _animations.animation_document
animation_from_document = _animations.animation_from_document
validate_animation = _animations.validate_animation

_modification = import_module(_core_name + '.modification')
ModifyAssetSnapshot = _modification.AssetSnapshot
AnimationSnapshot = _modification.AnimationSnapshot
SemanticOperation = _modification.SemanticOperation
ComponentOperation = _modification.ComponentOperation
ModificationRequest = _modification.ModificationRequest
ModificationPlan = _modification.ModificationPlan
plan_modification = _modification.plan_modification

_modify_exchange = import_module(_core_name + '.modify_exchange')
INSPECTION_SCHEMA = _modify_exchange.INSPECTION_SCHEMA
REQUEST_SCHEMA = _modify_exchange.REQUEST_SCHEMA
inspection_document = _modify_exchange.inspection_document
inspection_json = _modify_exchange.inspection_json
request_from_document = _modify_exchange.request_from_document
request_from_json = _modify_exchange.request_from_json

_lod = import_module(_core_name + '.lod')
plan_lods = _lod.plan_lods
LODLevel = _lod.LODLevel
