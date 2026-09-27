# SPDX-License-Identifier: GPL-3.0-or-later
"""Host-independent quadruped provider."""

from functools import lru_cache
from math import isfinite

from ..models import ImageTextureSpec, MaterialSpec
from .base import Parameter
from .semantic import SemanticTarget
from .quadruped_semantic import apply_quadruped_semantic_operations
from .quadruped_animation import generate_quadruped_idle, generate_quadruped_run, generate_quadruped_walk
from .quadruped_anatomy import CanineRecipe
from .quadruped_geometry import _build_quadruped_mesh
from .quadruped_rigging import _build_quadruped_skeleton, generate_quadruped_skin_weights


QUADRUPED_PARAMETERS = (
    Parameter("body_length_cm", "Body Length (cm)", 70, 25, 140),
    Parameter("shoulder_height_cm", "Shoulder Height (cm)", 55, 15, 100),
    Parameter("body_width_cm", "Body Width (cm)", 24, 8, 55),
    Parameter("head_length_cm", "Head Length (cm)", 24, 8, 45),
    Parameter("tail_length_cm", "Tail Length (cm)", 35, 5, 80),
)

QUADRUPED_SEMANTIC_TARGETS = (
    SemanticTarget("body", "Body", "region", ("shape", "scale", "surface")),
    SemanticTarget("torso", "Torso", "region", ("shape", "scale")),
    SemanticTarget("waist", "Waist", "region", ("shape", "scale")),
    SemanticTarget("chest", "Chest", "region", ("shape", "scale")),
    SemanticTarget("head", "Head", "region", ("shape", "scale", "surface")),
    SemanticTarget("muzzle", "Muzzle", "region", ("shape", "scale", "surface")),
    SemanticTarget("ear.left", "Left Ear", "region", ("shape", "scale")),
    SemanticTarget("ear.right", "Right Ear", "region", ("shape", "scale")),
    SemanticTarget("leg.front.left", "Front Left Leg", "region", ("shape", "scale")),
    SemanticTarget("leg.front.right", "Front Right Leg", "region", ("shape", "scale")),
    SemanticTarget("leg.hind.left", "Hind Left Leg", "region", ("shape", "scale")),
    SemanticTarget("leg.hind.right", "Hind Right Leg", "region", ("shape", "scale")),
    SemanticTarget("tail", "Tail", "region", ("shape", "scale", "surface")),
    SemanticTarget("coat", "Coat", "component", ("surface", "add_detail")),
    SemanticTarget("accessories", "Accessories", "component", ("add_component", "remove_component", "shape", "surface")),
)


QUADRUPED_SEMANTIC_APPLY_CAPABILITIES = tuple(
    (target, operation)
    for target in ("body", "torso", "chest", "waist", "head", "muzzle", "tail",
                   "leg.front.left", "leg.front.right", "leg.hind.left", "leg.hind.right", "ear.left", "ear.right")
    for operation in ("shape", "scale")
)


def _dimensions(parameters, values):
    dimensions = {}
    for field in parameters:
        value = values[field.key]
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise TypeError(field.label + " must be a number")
        if not isfinite(value) or not field.minimum <= value <= field.maximum:
            raise ValueError(field.label + " is outside its supported range")
        dimensions[field.key] = float(value)
    return dimensions


@lru_cache(maxsize=32)
def _quadruped_construction(recipe_id, recipe_version, parameters):
    return _build_quadruped_mesh(CanineRecipe().resolve(dict(parameters)))


def _construction(dimensions):
    return _quadruped_construction(CanineRecipe.recipe_id, CanineRecipe.recipe_version,
                                   tuple(sorted(dimensions.items())))


def _validate_topology(mesh, base):
    from ..models import ObjectMesh
    if not isinstance(mesh, ObjectMesh):
        raise TypeError("Quadruped ownership requires an ObjectMesh")
    if (len(mesh.parts) != 1 or mesh.parts[0].name != base.parts[0].name
            or mesh.parts[0].faces != base.parts[0].faces
            or len(mesh.parts[0].vertices) != len(base.parts[0].vertices)):
        raise ValueError("Quadruped ownership requires the authored surface topology; explicitly regenerate this asset before applying recipe edits")


class QuadrupedProvider:
    """Connected deformable quadruped provider."""

    key, label = "quadruped", "Quadruped"
    supports_rig = supports_idle = supports_locomotion = supports_run = supports_materials = True
    uses_skin_weights = True
    parameters = QUADRUPED_PARAMETERS
    semantic_targets = QUADRUPED_SEMANTIC_TARGETS
    semantic_apply_capabilities = QUADRUPED_SEMANTIC_APPLY_CAPABILITIES

    def dimensions(self, values):
        return _dimensions(self.parameters, values)

    def mesh(self, values):
        return _construction(self.dimensions(values))[0]

    def skeleton(self, values):
        return _build_quadruped_skeleton(_construction(self.dimensions(values))[1])

    def semantic_mesh(self, mesh, values, operations):
        base, anatomy = _construction(self.dimensions(values))
        _validate_topology(mesh, base)
        return apply_quadruped_semantic_operations(mesh, anatomy, operations)

    def skin_weights(self, mesh, values):
        base, anatomy = _construction(self.dimensions(values))
        _validate_topology(mesh, base)
        return generate_quadruped_skin_weights(mesh, _build_quadruped_skeleton(anatomy), anatomy=anatomy)

    def idle(self, duration, strength):
        return generate_quadruped_idle(duration, strength)

    def locomotion(self, duration, strength):
        return generate_quadruped_walk(duration, strength)

    def run(self, duration, strength):
        return generate_quadruped_run(duration, strength)

    def materials(self, values):
        texture = ImageTextureSpec(
            "Quadruped Coat Texture",
            2,
            2,
            (
                0.27, 0.14, 0.07, 1.0,
                0.34, 0.19, 0.10, 1.0,
                0.30, 0.16, 0.08, 1.0,
                0.38, 0.22, 0.12, 1.0,
            ),
        )
        return (
            MaterialSpec(
                "Quadruped Base Coat",
                ("quadruped",),
                (0.32, 0.18, 0.09, 1.0),
                metallic=0.0,
                roughness=0.82,
                base_color_texture=texture,
            ),
        )
