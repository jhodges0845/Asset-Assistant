# SPDX-License-Identifier: GPL-3.0-or-later
"""Self-document the portable LLM animation contract exported by Asset Assistant."""

_REPOSITORY = "https://github.com/jhodges0845/blender-object-generator"
_DOC_PATH = "docs/animation-json-roundtrip.md"
_CONTEXT_SCHEMA = "asset_assistant.animation_context.v1"
_ANIMATION_SCHEMA = "asset_assistant.animation.v1"


def _version_text(version):
    return ".".join(str(part) for part in version)


def enhance_context_payload(payload, addon_version=(0, 9, 0)):
    """Add enough contract guidance for a context-free LLM to author valid motion."""
    rig = payload.get("rig") or {}
    bones = rig.get("bones") or []
    allowed_bones = [str(bone.get("name")) for bone in bones if bone.get("name")]
    signature = str(rig.get("signature") or "")
    scene = payload.get("scene") or {}
    fps = float(scene.get("fps") or 24.0)
    example_bone = allowed_bones[0] if allowed_bones else "REPLACE_WITH_EXPORTED_BONE_NAME"

    payload["asset_assistant"] = {
        "product": "Asset Assistant",
        "addon_version": _version_text(addon_version),
        "repository": _REPOSITORY,
        "documentation": _REPOSITORY + "/blob/main/" + _DOC_PATH,
        "context_schema": _CONTEXT_SCHEMA,
        "return_schema": _ANIMATION_SCHEMA,
    }

    payload["coordinate_conventions"] = {
        "world_up_axis": "+Z",
        "character_forward_axis": "-Y",
        "character_right_axis": "+X",
        "pose_transform_space": "Blender pose-bone local transforms relative to each exported rest pose",
        "location_units": "Blender units using scene.scale_length from this file",
        "euler_units": "radians",
        "quaternion_order": ["w", "x", "y", "z"],
        "axis_angle_order": ["angle_radians", "x", "y", "z"],
        "important": "Character forward is -Y. Do not infer forward/backward from the screen, camera, or a bone's raw local axes. Use matrix_local/rest data and the reference poses when deciding how a torso should lean.",
    }

    payload["authoring_contract"] = {
        "goal": "Author a polished NEW animation for exactly this exported rig.",
        "output": "Return one JSON object only, using schema asset_assistant.animation.v1.",
        "allowed_bones": allowed_bones,
        "rig_signature": signature,
        "rules": [
            "Do not rename, add, remove, or invent bones.",
            "Do not change the rig hierarchy or rest pose.",
            "Use only finite numeric transforms and exported bone names.",
            "Prefer sparse meaningful keyed poses; Asset Assistant/Blender interpolates between them.",
            "Create a new clip; do not assume the reference clip will be overwritten.",
            "Default to in-place locomotion unless the user's request explicitly asks for root motion.",
            "For looping motions, make the beginning and end compatible and set clip.looping=true.",
            "Use the reference_animation as motion/style guidance when present, not as permission to rename bones.",
        ],
        "movement_semantics": {
            "forward": "toward character -Y",
            "backward": "toward character +Y",
            "up": "toward +Z",
            "right": "toward character +X",
            "forward_lean": "tilt the torso/hips toward character -Y using the exported rest matrices/reference poses; do not merely translate the character along +Y",
            "in_place_locomotion": "limbs and body animate while net character/root travel remains near the source position",
        },
        "recommended_user_prompt": "Using this Asset Assistant animation context, create a polished animation matching my artistic description. Return only an importable Asset Assistant animation JSON using the exact exported rig and return schema.",
    }

    payload["return_schema_example"] = {
        "schema": _ANIMATION_SCHEMA,
        "target": {"rig_signature": signature},
        "clip": {
            "name": "Polished Animation",
            "fps": fps,
            "looping": False,
        },
        "keyframes": [
            {
                "frame": 1.0,
                "bones": {
                    example_bone: {
                        "rotation_quaternion": [1.0, 0.0, 0.0, 0.0]
                    }
                },
            }
        ],
        "notes": "Describe artistic intent and important choices here.",
    }

    instructions = payload.setdefault("instructions", {})
    instructions["return_schema"] = _ANIMATION_SCHEMA
    instructions["read_first"] = (
        "Before authoring motion, read coordinate_conventions, authoring_contract, rig.bones, "
        "and reference_animation. Return JSON only; do not wrap it in Markdown."
    )
    instructions["root_motion_default"] = "IN_PLACE"
    instructions["looping_default"] = False
    return payload


def install(animation_json_ui, addon_version=(0, 9, 0)):
    """Decorate animation_json_ui.build_context_payload without coupling core JSON code to version metadata."""
    original = animation_json_ui.build_context_payload
    if getattr(original, "_asset_assistant_self_documenting", False):
        return

    def build_self_documenting_context(root, rig, scene):
        return enhance_context_payload(original(root, rig, scene), addon_version=addon_version)

    build_self_documenting_context._asset_assistant_self_documenting = True
    animation_json_ui.build_context_payload = build_self_documenting_context


__all__ = ["enhance_context_payload", "install"]
