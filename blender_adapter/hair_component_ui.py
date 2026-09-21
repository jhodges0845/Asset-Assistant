# SPDX-License-Identifier: GPL-3.0-or-later
"""Generated hair component entry point with explicit performance tiers."""

import uuid

import bpy

from .components import _armature, attach_rigid_component
from .core import (
    AttachmentMode,
    ComponentBehavior,
    ComponentKind,
    ComponentRecord,
    RigBinding,
    fit_parent_skinned_hair,
    get_provider,
    hair_shell_mesh,
)
from .skinned_components import attach_skinned_component


def _target(context):
    scene = context.scene if context else None
    settings = getattr(scene, "humanoid_settings", None) if scene else None
    root = settings.target if settings else None
    if root is None or root.get("generator") != "object_generator":
        return None
    return root


def _attachment_items(self, context):
    items = [("asset_root", "Asset Root", "Move with the complete Asset Assistant asset")]
    root = _target(context)
    if root is None:
        return items
    try:
        armature = _armature(root)
    except ValueError:
        return items
    for bone in armature.data.bones:
        value = "bone:" + bone.name
        items.append((value, bone.name, "Attach rigidly to bone " + bone.name))
    return items


def _supports_parent_skinned(root):
    if root is None or root.get("object_type") != "human":
        return False
    try:
        armature = _armature(root)
    except ValueError:
        return False
    return all(armature.data.bones.get(name) is not None for name in ("head", "neck", "torso"))


def _behavior_items(self, context):
    items = [
        (ComponentBehavior.STATIC.value, "Static", "Cheapest path; no independent motion"),
        (ComponentBehavior.RIGID.value, "Rigid", "Follow the selected root or bone without deforming"),
    ]
    if _supports_parent_skinned(_target(context)):
        items.append((
            ComponentBehavior.PARENT_SKINNED.value,
            "Bone-Driven (Parent Rig)",
            "Low-cost deformation through head, neck, and torso; no physics simulation",
        ))
    return tuple(items)


def _default_attachment(root):
    try:
        armature = _armature(root)
    except ValueError:
        return "asset_root"
    return "bone:head" if armature.data.bones.get("head") is not None else "asset_root"


def _provider_values(root, provider):
    return {field.key: root.get(field.key, field.default) for field in provider.parameters}


class ASSET_ASSISTANT_OT_generate_hair_shell(bpy.types.Operator):
    bl_idname = "asset_assistant.generate_hair_shell"
    bl_label = "Generate Hair Shell"
    bl_description = "Generate a separate hair asset and choose its runtime behavior tier"
    bl_options = {"REGISTER", "UNDO"}

    component_name: bpy.props.StringProperty(name="Name", default="Hair Shell")
    # Blender does not allow a string default when EnumProperty items are supplied
    # by a callback. Set the intended Rigid default in invoke() instead so dynamic
    # availability remains context-aware and registration stays valid.
    behavior: bpy.props.EnumProperty(
        name="Behavior",
        items=_behavior_items,
    )
    attachment_target: bpy.props.EnumProperty(name="Attach To", items=_attachment_items)
    width_cm: bpy.props.FloatProperty(name="Width (cm)", default=18.0, min=4.0, max=60.0)
    depth_cm: bpy.props.FloatProperty(name="Depth (cm)", default=20.0, min=4.0, max=60.0)
    cap_height_cm: bpy.props.FloatProperty(name="Cap Height (cm)", default=12.0, min=2.0, max=40.0)
    back_length_cm: bpy.props.FloatProperty(name="Back Length (cm)", default=18.0, min=0.0, max=120.0)

    @classmethod
    def poll(cls, context):
        return context.scene is not None and context.mode == "OBJECT" and _target(context) is not None

    def invoke(self, context, event):
        self.behavior = ComponentBehavior.RIGID.value
        self.attachment_target = _default_attachment(_target(context))
        return context.window_manager.invoke_props_dialog(self, width=440)

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "component_name")
        layout.prop(self, "behavior")
        if self.behavior != ComponentBehavior.PARENT_SKINNED.value:
            layout.prop(self, "attachment_target")
        layout.prop(self, "width_cm")
        layout.prop(self, "depth_cm")
        layout.prop(self, "cap_height_cm")
        layout.prop(self, "back_length_cm")
        box = layout.box()
        box.label(text="Performance is explicit, not automatic.")
        box.label(text="Static/Rigid: lowest cost, no simulation or extra bones.")
        if _supports_parent_skinned(_target(context)):
            box.label(text="Bone-Driven: low-cost head/neck/torso deformation.")
        box.label(text="Physics remains a later optional tier.")

    def execute(self, context):
        root = _target(context)
        try:
            behavior = ComponentBehavior(self.behavior)
            mesh = hair_shell_mesh(
                self.width_cm,
                self.depth_cm,
                self.cap_height_cm,
                self.back_length_cm,
            )
            if behavior == ComponentBehavior.PARENT_SKINNED:
                if not _supports_parent_skinned(root):
                    raise ValueError("Bone-Driven hair currently requires a rigged Human asset.")
                provider = get_provider(root.get("object_type"))
                skeleton = provider.skeleton(_provider_values(root, provider))
                fitted_mesh, skin_weights = fit_parent_skinned_hair(mesh, skeleton)
                record = ComponentRecord(
                    component_id="generated-hair-" + uuid.uuid4().hex,
                    kind=ComponentKind.HAIR,
                    provider_key="primitive.hair_shell",
                    attachment_target="body",
                    attachment_mode=AttachmentMode.SKINNED,
                    owns_geometry=True,
                    owns_materials=False,
                    owns_rig=False,
                    rig_binding=RigBinding.PARENT,
                    behavior=behavior,
                )
                component_root = attach_skinned_component(
                    root,
                    fitted_mesh,
                    skin_weights,
                    record,
                    name=self.component_name.strip() or "Hair Shell",
                )
            else:
                if behavior not in (ComponentBehavior.STATIC, ComponentBehavior.RIGID):
                    raise ValueError("This generated hair behavior is not implemented yet.")
                record = ComponentRecord(
                    component_id="generated-hair-" + uuid.uuid4().hex,
                    kind=ComponentKind.HAIR,
                    provider_key="primitive.hair_shell",
                    attachment_target=self.attachment_target,
                    attachment_mode=AttachmentMode.RIGID,
                    owns_geometry=True,
                    owns_materials=False,
                    owns_rig=False,
                    rig_binding=RigBinding.NONE,
                    behavior=behavior,
                )
                component_root = attach_rigid_component(
                    root,
                    mesh,
                    record,
                    name=self.component_name.strip() or "Hair Shell",
                )
        except (TypeError, ValueError, RuntimeError, AttributeError) as error:
            self.report({"ERROR"}, str(error))
            return {"CANCELLED"}

        for selected in context.selected_objects:
            selected.select_set(False)
        component_root.select_set(True)
        context.view_layer.objects.active = component_root
        self.report({"INFO"}, "Generated hair component: " + record.component_id)
        return {"FINISHED"}


_CLASSES = (ASSET_ASSISTANT_OT_generate_hair_shell,)


def register():
    for cls in _CLASSES:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(_CLASSES):
        bpy.utils.unregister_class(cls)


__all__ = [
    "ASSET_ASSISTANT_OT_generate_hair_shell",
    "_default_attachment",
    "_supports_parent_skinned",
    "register",
    "unregister",
]
