# SPDX-License-Identifier: GPL-3.0-or-later
"""Human provider implementations."""

from functools import lru_cache

from ..animation import generate_idle, generate_run, generate_walk
from ..geometry import generate_anatomical_human_mesh, generate_mesh
from ..geometry.deformable import _generate_face_atlas_uvs
from .surface_human import SurfaceHumanProvider
from ..geometry.anatomical_base_contour import refine_human_anatomical_base_contour
from ..geometry.cranium_refinement import refine_human_cranium_cross_sections
from ..geometry.facial_anatomy import refine_human_local_facial_anatomy
from ..geometry.facial_feature_topology import refine_human_facial_feature_loops
from ..geometry.facial_local_topology import refine_human_local_feature_topology
from ..geometry.facial_refinement import refine_human_facial_topology
from ..geometry.limb_refinement import refine_human_limb_cross_sections
from ..geometry.pelvis_refinement import refine_human_pelvis
from ..geometry.shoulder_refinement import refine_human_shoulders
from ..models import BodyType, HumanoidSpec, ImageTextureSpec, MaterialSpec
from ..models.mesh import MeshPart, ObjectMesh
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


@lru_cache(maxsize=16)
def _human_v2_mesh(height_cm):
    """Cache immutable Human V2 geometry for repeated in-process consumers.

    Blender integration tests and UI validation frequently request the same
    default Human several times. ObjectMesh/MeshPart are immutable, so sharing
    the generated core mesh avoids rebuilding and re-auditing ~42k vertices
    without sharing mutable Blender objects.
    """
    surface_values = {
        "height_cm": float(height_cm),
        "shoulder_scale": 1.0,
        "hip_scale": 1.0,
        "waist_scale": 1.0,
        "chest_fullness": 0.55,
        "muscle_definition": 0.45,
    }
    mesh = SurfaceHumanProvider().mesh(surface_values)
    part = mesh.parts[0]
    uvs = part.uvs or _generate_face_atlas_uvs(part.vertices, part.faces)
    return ObjectMesh((MeshPart("human", part.vertices, part.faces, uvs),))


@lru_cache(maxsize=32)
def _human_v2_skeleton(height_cm, weight_kg, body_type):
    proportions = generate_proportions(
        HumanoidSpec(float(height_cm), float(weight_kg), BodyType(body_type))
    )
    return generate_deforming_skeleton(proportions)


@lru_cache(maxsize=32)
def _human_v2_skin_weights(height_cm, weight_kg, body_type):
    """Cache deterministic immutable skin weights for repeated Human V2 requests."""
    mesh = _human_v2_mesh(float(height_cm))
    skeleton = _human_v2_skeleton(float(height_cm), float(weight_kg), body_type)
    return generate_skin_weights(mesh, skeleton)


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
        """Generate Human V2 from the cached immutable Mathematical Human surface."""
        return _human_v2_mesh(float(values["height_cm"]))

    def semantic_mesh(self, mesh, values, operations):
        return apply_human_semantic_operations(mesh, self.proportions(values), operations)

    def skeleton(self, values):
        return _human_v2_skeleton(
            float(values["height_cm"]),
            float(values["weight_kg"]),
            values["body_type"],
        )

    def skin_weights(self, mesh, values):
        cached_mesh = _human_v2_mesh(float(values["height_cm"]))
        if mesh is cached_mesh or mesh == cached_mesh:
            return _human_v2_skin_weights(
                float(values["height_cm"]),
                float(values["weight_kg"]),
                values["body_type"],
            )
        # Semantic edits can change vertex positions while retaining the same
        # Human controls, so only reuse weights for the unmodified base mesh.
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
