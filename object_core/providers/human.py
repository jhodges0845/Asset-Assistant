# SPDX-License-Identifier: GPL-3.0-or-later
"""Human provider implementations."""

from ..animation import generate_idle, generate_run, generate_walk
from ..geometry import generate_deformable_mesh, generate_mesh
from ..geometry.body_refinement import refine_human_torso_cross_sections
from ..geometry.cranium_refinement import refine_human_cranium_cross_sections
from ..geometry.facial_refinement import refine_human_facial_topology
from ..geometry.limb_refinement import refine_human_limb_cross_sections
from ..geometry.pelvis_refinement import refine_human_pelvis
from ..geometry.shoulder_refinement import refine_human_shoulders
from ..models import BodyType, HumanoidSpec, ImageTextureSpec, MaterialSpec
from ..proportions import generate_proportions
from ..rigging import generate_deforming_skeleton, generate_skin_weights, generate_skeleton
from .base import Parameter
from .semantic import SemanticTarget
from .human_semantic import apply_human_semantic_operations


HUMAN_PARAMETERS = (
    Parameter("height_cm", "Height (cm)", 180, 120, 240),
    Parameter("weight_kg", "Weight (kg)", 95, 30, 300),
    Parameter(
        "body_type",
        "Body Type",
        "average",
        0,
        0,
        tuple((value.value, value.value.title()) for value in BodyType),
    ),
)

HUMAN_SEMANTIC_TARGETS = (
    SemanticTarget("body", "Body", "region", ("shape", "scale", "surface")),
    SemanticTarget("torso", "Torso", "region", ("shape", "scale")),
    SemanticTarget("shoulders", "Shoulders", "region", ("shape", "scale")),
    SemanticTarget("head", "Head", "region", ("shape", "scale", "surface")),
    SemanticTarget("face", "Face", "region", ("shape", "surface", "add_detail")),
    SemanticTarget("jaw", "Jaw", "region", ("shape", "scale")),
    SemanticTarget("cheeks", "Cheeks", "region", ("shape", "scale")),
    SemanticTarget("arm.left", "Left Arm", "region", ("shape", "scale")),
    SemanticTarget("arm.right", "Right Arm", "region", ("shape", "scale")),
    SemanticTarget("leg.left", "Left Leg", "region", ("shape", "scale")),
    SemanticTarget("leg.right", "Right Leg", "region", ("shape", "scale")),
    SemanticTarget("hair", "Hair", "component", ("add_component", "remove_component", "shape", "surface")),
    SemanticTarget("clothing", "Clothing", "component", ("add_component", "remove_component", "shape", "surface")),
    SemanticTarget("accessories", "Accessories", "component", ("add_component", "remove_component", "shape", "surface")),
)

_HUMAN_GEOMETRY_TARGETS = (
    "body", "torso", "shoulders", "head", "face", "jaw", "cheeks",
    "arm.left", "arm.right", "leg.left", "leg.right",
)
HUMAN_SEMANTIC_APPLY_CAPABILITIES = tuple(
    (target, operation)
    for target in _HUMAN_GEOMETRY_TARGETS
    for operation in ("shape", "scale")
)


def _proportions(values):
    return generate_proportions(
        HumanoidSpec(
            values["height_cm"],
            values["weight_kg"],
            BodyType(values["body_type"]),
        )
    )


class HumanoidProvider:
    key, label = "humanoid", "Humanoid"
    supports_rig = supports_idle = True
    supports_locomotion = supports_run = False
    uses_skin_weights = supports_materials = False
    parameters = HUMAN_PARAMETERS
    semantic_targets = ()

    def proportions(self, values):
        return _proportions(values)

    def mesh(self, values):
        return generate_mesh(self.proportions(values))

    def skeleton(self, values):
        return generate_skeleton(self.proportions(values))

    def idle(self, duration, strength):
        return generate_idle(duration, strength)


class HumanExperimentalProvider:
    """Deformable Human provider used for new human assets."""

    key, label = "human_experimental", "Human"
    supports_rig = supports_materials = supports_idle = supports_locomotion = supports_run = True
    uses_skin_weights = True
    parameters = HUMAN_PARAMETERS
    semantic_targets = HUMAN_SEMANTIC_TARGETS
    semantic_apply_capabilities = HUMAN_SEMANTIC_APPLY_CAPABILITIES

    def proportions(self, values):
        return _proportions(values)

    def mesh(self, values):
        proportions = self.proportions(values)
        mesh = generate_deformable_mesh(proportions)
        mesh = refine_human_torso_cross_sections(mesh, proportions)
        mesh = refine_human_shoulders(mesh, proportions)
        mesh = refine_human_pelvis(mesh, proportions)
        mesh = refine_human_limb_cross_sections(mesh, proportions)
        mesh = refine_human_facial_topology(mesh, proportions)
        return refine_human_cranium_cross_sections(mesh, proportions)

    def semantic_mesh(self, mesh, values, operations):
        return apply_human_semantic_operations(mesh, self.proportions(values), operations)

    def skeleton(self, values):
        return generate_deforming_skeleton(self.proportions(values))

    def skin_weights(self, mesh, values):
        return generate_skin_weights(mesh, self.skeleton(values))

    def idle(self, duration, strength):
        return generate_idle(duration, strength)

    def locomotion(self, duration, strength):
        return generate_walk(duration, strength)

    def run(self, duration, strength):
        return generate_run(duration, strength)

    def materials(self, values):
        # This tiny warm texture is a portable UV/texturing proof and artist starting
        # point, not an attempt to synthesize finished skin detail.
        texture = ImageTextureSpec(
            "Human Base Texture",
            2,
            2,
            (
                0.50, 0.31, 0.24, 1.0,
                0.58, 0.38, 0.29, 1.0,
                0.60, 0.40, 0.31, 1.0,
                0.53, 0.34, 0.26, 1.0,
            ),
        )
        return (
            MaterialSpec(
                "Human Base Surface",
                ("human",),
                (0.55, 0.36, 0.28, 1.0),
                metallic=0.0,
                roughness=0.68,
                base_color_texture=texture,
            ),
        )
