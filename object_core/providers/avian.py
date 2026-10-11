# SPDX-License-Identifier: GPL-3.0-or-later
"""Host-independent Avian provider foundation."""

from math import isfinite

from ..models import ImageTextureSpec, MaterialSpec, ObjectMesh
from .base import Parameter
from .semantic import SemanticTarget
from .avian_animation import generate_avian_flight, generate_avian_idle, generate_avian_walk
from .avian_anatomy import AvianRecipe
from .avian_geometry import _build_avian_mesh
from .avian_rigging import _build_avian_skeleton, generate_avian_skin_weights
from .avian_semantic import apply_avian_semantic_operations


AVIAN_PARAMETERS = (
    Parameter("body_length_cm", "Body Length (cm)", 42, 12, 140),
    Parameter("body_width_cm", "Body Width (cm)", 16, 5, 60),
    Parameter("body_height_cm", "Body Height (cm)", 20, 6, 70),
    Parameter("wingspan_cm", "Wingspan (cm)", 90, 20, 320),
    Parameter("tail_length_cm", "Tail Length (cm)", 22, 4, 100),
)

AVIAN_SEMANTIC_TARGETS = (
    SemanticTarget("body", "Body", "region", ("shape", "scale", "surface")),
    SemanticTarget("chest", "Chest", "region", ("shape", "scale")),
    SemanticTarget("head", "Head", "region", ("shape", "scale", "surface")),
    SemanticTarget("beak", "Beak", "region", ("shape", "scale", "surface")),
    SemanticTarget("wing.left", "Left Wing", "region", ("shape", "scale", "surface")),
    SemanticTarget("wing.right", "Right Wing", "region", ("shape", "scale", "surface")),
    SemanticTarget("tail", "Tail", "region", ("shape", "scale", "surface")),
    SemanticTarget("leg.left", "Left Leg", "region", ("shape", "scale", "surface")),
    SemanticTarget("leg.right", "Right Leg", "region", ("shape", "scale", "surface")),
    SemanticTarget("foot.left", "Left Foot", "region", ("shape", "scale")),
    SemanticTarget("foot.right", "Right Foot", "region", ("shape", "scale")),
    SemanticTarget("plumage", "Plumage", "component", ("surface", "add_detail")),
)

_AVIAN_GEOMETRY_TARGETS = (
    "body", "chest", "head", "beak", "wing.left", "wing.right",
    "tail", "leg.left", "leg.right", "foot.left", "foot.right",
)
AVIAN_SEMANTIC_APPLY_CAPABILITIES = tuple(
    (target, operation)
    for target in _AVIAN_GEOMETRY_TARGETS
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
    if dimensions["wingspan_cm"] <= dimensions["body_width_cm"]:
        raise ValueError("Wingspan must be wider than the body")
    return dimensions


class AvianProvider:
    """Connected deformable Avian provider foundation."""

    key, label = "avian", "Avian"
    supports_rig = supports_materials = supports_idle = supports_locomotion = True
    supports_flight = True
    supports_run = False
    locomotion_label = "Walk"
    uses_skin_weights = True
    parameters = AVIAN_PARAMETERS
    semantic_targets = AVIAN_SEMANTIC_TARGETS
    semantic_apply_capabilities = AVIAN_SEMANTIC_APPLY_CAPABILITIES

    def dimensions(self, values):
        return _dimensions(self.parameters, values)

    def mesh(self, values):
        return _build_avian_mesh(AvianRecipe().resolve(self.dimensions(values)))[0]

    def anatomy(self, values):
        """Return resolved anatomy with constructor-authored topology ownership."""
        return _build_avian_mesh(AvianRecipe().resolve(self.dimensions(values)))[1]

    def semantic_mesh(self, mesh, values, operations):
        return apply_avian_semantic_operations(mesh, self.dimensions(values), operations)

    def skeleton(self, values):
        return _build_avian_skeleton(AvianRecipe().resolve(self.dimensions(values)))

    def skin_weights(self, mesh, values):
        base, anatomy = _build_avian_mesh(AvianRecipe().resolve(self.dimensions(values)))
        if not isinstance(mesh, ObjectMesh):
            raise TypeError('Avian ownership requires an ObjectMesh')
        if (len(mesh.parts) != 1 or mesh.parts[0].name != base.parts[0].name
                or mesh.parts[0].faces != base.parts[0].faces
                or len(mesh.parts[0].vertices) != len(base.parts[0].vertices)):
            raise ValueError('Avian ownership requires authored topology; explicitly regenerate this asset')
        return generate_avian_skin_weights(mesh, _build_avian_skeleton(anatomy), anatomy=anatomy)

    def idle(self, duration, strength):
        return generate_avian_idle(duration, strength)

    def locomotion(self, duration, strength):
        return generate_avian_walk(duration, strength)

    def flight(self, duration, strength):
        return generate_avian_flight(duration, strength)

    def materials(self, values):
        self.dimensions(values)
        texture = ImageTextureSpec(
            "Avian Plumage Texture",
            2,
            2,
            (
                0.12, 0.18, 0.28, 1.0,
                0.18, 0.28, 0.42, 1.0,
                0.10, 0.15, 0.24, 1.0,
                0.24, 0.36, 0.50, 1.0,
            ),
        )
        return (
            MaterialSpec(
                "Avian Base Plumage",
                ("avian",),
                (0.16, 0.24, 0.36, 1.0),
                metallic=0.0,
                roughness=0.74,
                base_color_texture=texture,
            ),
        )
