# Human: create, rig and animate

**Human** is the single Human option in the plugin. It uses the mathematical
surface and supports rigging, animation, materials and semantic Modify.

## In Blender

1. In Create > Generate, choose Human and adjust height, weight and body type.
2. Generate the asset. If the button says Replace, it targets the current asset;
   preserve artist work before replacing it.
3. Select the generated Human and open Animate > Rig & Pose > Add Basic Rig.
4. Generate an animation clip, then preview it. An existing rig is preserved;
   Add Basic Rig is disabled once the asset already has a rig.
5. Use Components and Export as needed; refresh validation before export.

Rigging requires Object Mode and the generated asset in the active scene.
Animation requires its rig. Model capabilities come from the selected generated
asset, not from changing the Create dropdown.

## Reading the code

| Step | Owner | What it does |
| --- | --- | --- |
| Choose model | `blender_adapter/workspace_create_ui.py` | Shows provider labels, controls and workflow guidance. |
| Generate | `blender_adapter/ui.py` | Resolves the provider and creates the scene asset through the adapter. |
| Build Human | `object_core/providers/human.py` | Composes validated surface, body controls, rig, skinning and animation capabilities. |
| Build neutral surface | `object_core/geometry/surface_human_builder.py` | Calls the geometry generator, audits topology and retains authored arm indices. |
| Construct geometry | `object_core/geometry/surface_human.py` | Builds the mathematical surface; owns vertex ordering and arm membership. |
| Shape mesh and rig | `object_core/rigging/surface_human.py` | Applies the shared body-control mapping and supplies matching rest landmarks. |
| Attach rig | `blender_adapter/workflow.py` | Reads saved asset parameters and attaches the provider skeleton/weights. |
| Calculate weights | `object_core/rigging/deforming.py` | Uses shared weighting with Human's arm candidate restrictions. |
| Animate | `blender_adapter/animation.py` and animation modules | Turns provider motion into editable Blender actions. |
| Modify | `object_core/providers/human_semantic.py` | Changes geometry with explicit preview/apply through the adapter. |

Within `providers/human.py`, read `_neutral_surface_data`, `_human_mesh`,
`_human_skeleton`, `_surface_skin_weights`, then `HumanProvider`.
The caches share immutable core data. Edited meshes recompute weights; arm
ownership follows topology so wrist movement cannot pull nearby hip vertices.

The geometry builder (`HumanSurfaceBuilder`) is an implementation detail, not a
registered asset provider. Standalone investigation scripts can call it directly.

## Identity and pre-alpha cleanup

The registered provider is `HumanProvider`, key `human`. The previous experimental
key and static study entry were removed without aliases or automatic migration.
Regenerate pre-alpha test assets with the current plugin when needed. The low-level
Humanoid blockout remains a separate test fixture, not an alternative Human UI path.

## Validation and limits

Core provider tests protect geometry, controls, cache identity and arm-weight
isolation. Blender tests protect asset lifecycle, rigging, animation and review
projection. The isolated ZIP test exercises the installed plugin workflow.
The surface, joint deformation and provisional UVs remain experimental; a passing
test suite is not anatomical or animation-quality approval.
See [integration evidence](visual-testing-integration.md) for the implementation
checkpoint and [standalone geometry guide](mathematical-human-plugin.md) for study controls.
