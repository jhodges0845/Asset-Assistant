# SPDX-License-Identifier: GPL-3.0-or-later
"""Human provider: surface generation, rigging, skinning, Modify and animation.

Human: validated neutral surface -> body controls -> matching skeleton -> weights.
The Blender adapter consumes these portable results; it owns scene objects and
explicit rig/animation operators. See docs/human-workflow.md for the full flow.
"""

from functools import lru_cache

from ..animation import generate_idle, generate_run, generate_walk
from ..geometry import generate_mesh
from ..geometry.surface_human import SurfaceHumanSpec
from ..geometry.deformable import _generate_face_atlas_uvs
from ..geometry.surface_human_builder import HumanSurfaceBuilder
from ..models import BodyType, HumanoidSpec, ImageTextureSpec, MaterialSpec
from ..models.mesh import MeshPart, ObjectMesh
from ..rigging.surface_human import surface_skeleton
from ..geometry.human_shaping import shape_human_surface
from ..proportions import generate_proportions
from ..rigging import generate_skin_weights, generate_skeleton
from .base import Parameter
from .semantic import SemanticTarget
from .human_semantic import apply_human_semantic_operations
from .human_anatomy import HumanRecipe
from ..anatomy import AnatomyRegion


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
    SemanticTarget(
        "hair",
        "Hair",
        "component",
        ("add_component", "remove_component", "shape", "surface"),
    ),
    SemanticTarget(
        "clothing",
        "Clothing",
        "component",
        ("add_component", "remove_component", "shape", "surface"),
    ),
    SemanticTarget(
        "accessories",
        "Accessories",
        "component",
        ("add_component", "remove_component", "shape", "surface"),
    ),
)

_HUMAN_GEOMETRY_TARGETS = (
    "body",
    "torso",
    "shoulders",
    "head",
    "face",
    "jaw",
    "cheeks",
    "arm.left",
    "arm.right",
    "leg.left",
    "leg.right",
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


@lru_cache(maxsize=1)
def _neutral_surface_anatomy_data():
    """Build and audit one neutral surface, retaining authored limb ownership."""
    mesh, _report, limbs = HumanSurfaceBuilder().build(
        SurfaceHumanSpec(), include_limb_indices=True
    )
    part = mesh.parts[0]
    return (
        ObjectMesh(
            (
                MeshPart(
                    "human",
                    part.vertices,
                    part.faces,
                    _generate_face_atlas_uvs(part.vertices, part.faces),
                ),
            )
        ),
        limbs,
    )


def _neutral_surface_data():
    """Existing diagnostic seam for the neutral mesh and authored arm indices."""
    mesh, regions = _neutral_surface_anatomy_data()
    return mesh, tuple((name.split(".")[-1], indices) for name, indices in regions
                       if name.startswith("arm."))


def _neutral_surface_mesh():
    return _neutral_surface_anatomy_data()[0]


@lru_cache(maxsize=1)
def _human_regions():
    mesh, limbs = _neutral_surface_anatomy_data()
    return (AnatomyRegion("body", "human", tuple(range(len(mesh.parts[0].vertices)))),) + tuple(
        AnatomyRegion(name, "human", indices) for name, indices in limbs)


def _human_anatomy(height_cm, weight_kg, body_type):
    """Normalize call style and bind every resolution to recipe identity."""
    return _resolved_human_anatomy(HumanRecipe.recipe_id, HumanRecipe.recipe_version,
                                  float(height_cm), float(weight_kg), BodyType(body_type).value)


@lru_cache(maxsize=32)
def _resolved_human_anatomy(recipe_id, recipe_version, height_cm, weight_kg, body_type):
    """Single cached Human resolution used by mesh, rig, weights and Modify."""
    return HumanRecipe(_human_regions()).resolve({
        "height_cm": height_cm, "weight_kg": weight_kg, "body_type": body_type,
    })


def _validate_surface_topology(mesh):
    """Authored ownership is valid only for the unchanged Human topology."""
    if not isinstance(mesh, ObjectMesh):
        raise TypeError("Human ownership expects an ObjectMesh")
    neutral = _neutral_surface_mesh()
    # Semantic edits preserve topology: ownership follows authored indices even
    # when an artist moves a hand beside the pelvis. Never infer arm ownership
    # from proximity to bones in this arms-down rest pose.
    if (
        len(mesh.parts) != 1
        or mesh.parts[0].faces != neutral.parts[0].faces
        or len(mesh.parts[0].vertices) != len(neutral.parts[0].vertices)
    ):
        raise ValueError(
            "Human surface skinning requires the authored surface topology"
        )


def _surface_skin_weights(mesh, skeleton, anatomy):
    """Reuse shared weighting with resolved topology-based arm ownership."""
    _validate_surface_topology(mesh)
    anatomy.validate_mesh(mesh)
    owners = {index: region.name.split(".")[-1]
              for region in anatomy.regions if region.name.startswith("arm.")
              for index in region.vertex_indices}
    groups = {}

    def bone_filter(part_name, index, vertex, bones):
        side = owners.get(index)
        if side not in groups:
            if side is not None:
                names = {
                    "torso",
                    "upper_arm." + side,
                    "forearm." + side,
                    "hand." + side,
                }
                groups[side] = tuple(b for b in bones if b.name in names)
            else:
                groups[side] = tuple(
                    b for b in bones if not b.name.startswith(("forearm.", "hand."))
                )
        return groups[side]

    return generate_skin_weights(mesh, skeleton, bone_filter=bone_filter)


def _human_mesh(height_cm, weight_kg=95.0, body_type="average"):
    return _cached_human_mesh(HumanRecipe.recipe_id, HumanRecipe.recipe_version,
                    float(height_cm), float(weight_kg), BodyType(body_type).value)


@lru_cache(maxsize=16)
def _cached_human_mesh(recipe_id, recipe_version, height_cm, weight_kg, body_type):
    """Cache immutable Human V2 geometry for repeated in-process consumers.

    Blender integration tests and UI validation frequently request the same
    default Human several times. ObjectMesh/MeshPart are immutable, so sharing
    the generated core mesh avoids rebuilding and re-auditing ~42k vertices
    without sharing mutable Blender objects.
    """
    anatomy = _human_anatomy(height_cm, weight_kg, body_type)
    mesh = shape_human_surface(_neutral_surface_mesh(), anatomy)
    anatomy.validate_mesh(mesh)
    return mesh


def _human_skeleton(height_cm, weight_kg, body_type):
    return _cached_human_skeleton(HumanRecipe.recipe_id, HumanRecipe.recipe_version,
                    float(height_cm), float(weight_kg), BodyType(body_type).value)


@lru_cache(maxsize=32)
def _cached_human_skeleton(recipe_id, recipe_version, height_cm, weight_kg, body_type):
    return surface_skeleton(_human_anatomy(height_cm, weight_kg, body_type))


def _human_skin_weights(height_cm, weight_kg, body_type):
    return _cached_human_skin_weights(HumanRecipe.recipe_id, HumanRecipe.recipe_version,
                    float(height_cm), float(weight_kg), BodyType(body_type).value)


@lru_cache(maxsize=32)
def _cached_human_skin_weights(recipe_id, recipe_version, height_cm, weight_kg, body_type):
    """Cache deterministic immutable skin weights for repeated Human V2 requests."""
    mesh = _human_mesh(float(height_cm), float(weight_kg), body_type)
    skeleton = _human_skeleton(float(height_cm), float(weight_kg), body_type)
    return _surface_skin_weights(mesh, skeleton, _human_anatomy(height_cm, weight_kg, body_type))


class HumanProvider:
    """User-facing Human: shape, rig, animate and Modify through one provider.

    Registered as human; this is the plugin's single Human model path.
    """

    key, label = "human", "Human"
    supports_rig = supports_materials = supports_idle = supports_locomotion = (
        supports_run
    ) = True
    uses_skin_weights = True
    parameters = HUMAN_PARAMETERS
    semantic_targets = HUMAN_SEMANTIC_TARGETS
    semantic_apply_capabilities = HUMAN_SEMANTIC_APPLY_CAPABILITIES

    def proportions(self, values):
        return _human_anatomy(float(values["height_cm"]), float(values["weight_kg"]),
                              values["body_type"]).proportions

    def mesh(self, values):
        """Generate Human V2 from the cached immutable Mathematical Human surface."""
        return _human_mesh(
            float(values["height_cm"]), float(values["weight_kg"]), values["body_type"]
        )

    def semantic_mesh(self, mesh, values, operations):
        _validate_surface_topology(mesh)
        anatomy = _human_anatomy(float(values["height_cm"]), float(values["weight_kg"]), values["body_type"])
        return apply_human_semantic_operations(
            mesh, anatomy.proportions, operations, anatomy=anatomy
        )

    def skeleton(self, values):
        return _human_skeleton(
            float(values["height_cm"]),
            float(values["weight_kg"]),
            values["body_type"],
        )

    def skin_weights(self, mesh, values):
        cached_mesh = _human_mesh(
            float(values["height_cm"]), float(values["weight_kg"]), values["body_type"]
        )
        if mesh is cached_mesh:
            return _human_skin_weights(
                float(values["height_cm"]),
                float(values["weight_kg"]),
                values["body_type"],
            )
        # Semantic edits can change vertex positions while retaining the same
        # Human controls, so only reuse weights for the unmodified base mesh.
        return _surface_skin_weights(mesh, self.skeleton(values),
                                     _human_anatomy(float(values["height_cm"]),
                                                    float(values["weight_kg"]), values["body_type"]))

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
                0.50,
                0.31,
                0.24,
                1.0,
                0.58,
                0.38,
                0.29,
                1.0,
                0.60,
                0.40,
                0.31,
                1.0,
                0.53,
                0.34,
                0.26,
                1.0,
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


class HumanoidProvider:
    """Legacy rigid-part blockout; distinct from the surface-based Human."""

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
