# SPDX-License-Identifier: GPL-3.0-or-later
"""Generated lightweight clothing proof using the existing component workflow."""

import uuid
import bpy

from .components import _armature
from .core import (
    AttachmentMode, ComponentBehavior, ComponentKind, ComponentRecord, RigBinding,
    basic_shirt_mesh, basic_shirt_weights, get_provider,
)
from .skinned_components import attach_skinned_component


def _target(context):
    scene = context.scene if context else None
    settings = getattr(scene, "humanoid_settings", None) if scene else None
    root = settings.target if settings else None
    if root is None or root.get("generator") != "object_generator":
        return None
    return root


def _supports_shirt(root):
    if root is None or root.get("object_type") != "human":
        return False
    try:
        armature = _armature(root)
    except ValueError:
        return False
    return all(armature.data.bones.get(name) is not None for name in ("torso", "neck"))


def _provider_values(root, provider):
    return {field.key: root.get(field.key, field.default) for field in provider.parameters}


class ASSET_ASSISTANT_OT_generate_basic_shirt(bpy.types.Operator):
    bl_idname = "asset_assistant.generate_basic_shirt"
    bl_label = "Generate Basic Shirt"
    bl_description = "Generate a separate lightweight shirt skinned to the Human parent rig"
    bl_options = {"REGISTER", "UNDO"}

    component_name: bpy.props.StringProperty(name="Name", default="Basic Shirt")
    ease_cm: bpy.props.FloatProperty(name="Fit Ease (cm)", default=2.0, min=0.0, max=20.0)
    length_cm: bpy.props.FloatProperty(name="Length (cm)", default=42.0, min=15.0, max=90.0)

    @classmethod
    def poll(cls, context):
        return context.scene is not None and context.mode == "OBJECT" and _supports_shirt(_target(context))

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self, width=440)

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "component_name")
        layout.prop(self, "ease_cm")
        layout.prop(self, "length_cm")
        box = layout.box()
        box.label(text="Separate clothing asset; parent-rig skinned.")
        box.label(text="Uses the Human torso/neck rig with no extra simulation.")
        box.label(text="Materials remain independently editable after generation.")

    def execute(self, context):
        root = _target(context)
        try:
            if not _supports_shirt(root):
                raise ValueError("Basic Shirt currently requires a rigged Human asset.")
            provider = get_provider(root.get("object_type"))
            skeleton = provider.skeleton(_provider_values(root, provider))
            mesh = basic_shirt_mesh(skeleton, self.ease_cm, self.length_cm)
            weights = basic_shirt_weights(mesh)
            record = ComponentRecord(
                component_id="generated-shirt-" + uuid.uuid4().hex,
                kind=ComponentKind.CLOTHING,
                provider_key="primitive.basic_shirt",
                attachment_target="body",
                attachment_mode=AttachmentMode.SKINNED,
                owns_geometry=True,
                owns_materials=False,
                owns_rig=False,
                rig_binding=RigBinding.PARENT,
                behavior=ComponentBehavior.PARENT_SKINNED,
            )
            component_root = attach_skinned_component(
                root, mesh, weights, record,
                name=self.component_name.strip() or "Basic Shirt",
            )
        except (TypeError, ValueError, RuntimeError, AttributeError) as error:
            self.report({"ERROR"}, str(error))
            return {"CANCELLED"}

        for selected in context.selected_objects:
            selected.select_set(False)
        component_root.select_set(True)
        context.view_layer.objects.active = component_root
        self.report({"INFO"}, "Generated clothing component: " + record.component_id)
        return {"FINISHED"}


_CLASSES = (ASSET_ASSISTANT_OT_generate_basic_shirt,)


def register():
    for cls in _CLASSES:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(_CLASSES):
        bpy.utils.unregister_class(cls)


__all__ = ["ASSET_ASSISTANT_OT_generate_basic_shirt", "_supports_shirt", "register", "unregister"]
