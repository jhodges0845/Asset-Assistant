# Human mathematical surface

The plugin has one Human option: **Create > Human**. Generate it, then use
**Animate > Rig & Pose > Add Basic Rig** and generate an animation clip.
See [Human workflow and code map](human-workflow.md).

`HumanProvider` (`human`) composes `HumanSurfaceBuilder`, body shaping, the matching
rest skeleton, topology-aware arm weighting, semantic Modify and animations.
The old Mathematical Human / Human Study (Static) plugin option has been removed.
Pre-alpha assets using the removed identifiers are not automatically converted.

Standalone geometry investigations still use `scripts/build_surface_human.py`
and strict presets; they are development tools, not a second plugin workflow.
See [mathematical-human-development.md](mathematical-human-development.md) for
historical geometry experiments. Their screenshots are not production acceptance.

## Review

```text
blender --background --factory-startup --python-exit-code 1 --python scripts/render_human_review.py -- --output human_review.png
blender --background --factory-startup --python-exit-code 1 --python scripts/inspect_human_deformation.py
```

CI uploads the Human clay/silhouette/wireframe sheets and deformation cards.
Visual inspection remains required. Surface anatomy, joint quality and provisional
UVs remain experimental.
