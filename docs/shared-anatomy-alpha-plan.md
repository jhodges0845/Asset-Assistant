# Shared anatomy and animation: alpha plan

Status: planned; approved product direction, September 21, 2026. This changes the alpha scope, not the implemented feature set.

## Alpha promise

Human, Quadruped and Avian should feel like one coherent character system. Each should produce a recognizable, appealing neutral model, visibly useful anatomy variations, and believable looping motion through the same Generate -> Modify -> Rig -> Animate -> Export workflow. The wow factor comes from silhouette, deformation and motion together, not only increased polygon counts.

This milestone precedes release hardening. Existing production-readiness checklists remain evidence inventories; they do not require every future production feature for alpha.

## Starting point

Human composes a mathematical surface builder and surface-aligned rig. Quadruped and Avian currently have separate geometry, rigging and animation modules behind the same provider interface. Human and Avian have executable semantic geometry operations; Quadruped semantic declarations do not yet provide equivalent execution. Existing animation identity, preview/apply, ownership and export contracts remain the integration boundary.

Read `human-workflow.md`, `object_core/providers/quadruped.py`, `object_core/providers/avian.py` and `animation-architecture.md` before implementation.

## Shared construction with anatomy recipes

Proposed flow:

`provider controls -> validated anatomy recipe -> resolved anatomy -> surface + rig + region metadata -> weights / semantic Modify -> provider motion recipe -> existing Blender workflow`

The resolved anatomy is the common source for surface landmarks, bone placement, semantic regions and skinning membership. Avoid independently guessed rig locations or spatial filters that accidentally include nearby unrelated body parts.

A recipe describes proportions, anatomical regions and connections, local coordinate frames, symmetry, joint chains and bend directions, attachment boundaries, region membership, semantic controls and supported motion roles. Parameter presets select values within a recipe; a preset is not a new construction implementation.

Shared machinery owns parameter validation, deterministic construction orchestration, coordinate transforms, region/landmark reporting, topology audits and reusable skinning constraints. Anatomy-specific surface constructors remain explicit: a wing is not a stretched Human arm and a quadruped hind limb is not a Human leg with renamed bones. Connected-body joins and separate appendage surfaces must declare their topology expectations.

Start with typed Python contracts in a focused host-independent anatomy package; do not invent an external recipe language or plugin registry before two working recipes justify it. Providers remain the public capability and composition layer. Blender continues to consume existing mesh/skeleton/animation contracts. Box and imported assets do not need anatomy recipes.

## Milestones and acceptance gates

### 1. Record the baseline and prove the shared seam

- Capture reproducible neutral clay, silhouette and wireframe views, bend poses, clips, mesh counts and generation timings for all three current providers.
- Establish a small named parameter sample set: default, contrasting proportions and supported boundary cases. Record commit and parameters with each review.
- Extract the minimum recipe/result contracts from Human and prove them with one Quadruped torso/limb construction slice before generalizing further.
- Route Human through that contract without a visible quality regression. Preserve current Human controls, semantic edits, component attachment and plugin behavior.
- Gate: deterministic results; existing workflow tests pass; geometry and rig derive from the same resolved anatomy; visual baseline accepted. No new public Human option.

### 2. Quadruped anatomy recipe

- Deliver one strong canine-like reference body first: ribcage, scapular/shoulder transition, pelvis, neck, muzzle, ears, paws and tail.
- Model front and hind joint chains explicitly, including digitigrade stance and correct hock versus knee behavior.
- Implement useful independent chest, waist, limb, head and tail shaping through the shared semantic contract, rather than merely advertising targets.
- Gate: convincing front/side/three-quarter silhouettes, at least two meaningful proportion variants, connected intended body surfaces, localized weights and readable shoulder/hip/knee/hock poses.
- Broad species coverage and multiple foot-stance families remain later work.

### 3. Avian anatomy recipe

- Deliver one strong bird reference first: breast, back, neck/head, beak, pelvis, legs/feet, wing roots, articulated wings and tail fan.
- Share construction and anatomical metadata machinery while retaining bird-specific surface and joint rules.
- Keep a clear distinction between skeletal wing structure and feather/plumage representation. Use an inexpensive authored surface treatment for alpha; dense individual feathers and simulation are optional later work.
- Gate: recognizable perched silhouette and extended-wing silhouette, at least two useful proportion variants, credible wing folding, and correct leg/ankle bend behavior. Existing Avian semantic operations remain useful.

### 4. Cross-provider anatomy and Modify acceptance

- Refine Human where shared work reveals actual silhouette or deformation weaknesses.
- For each provider, perform one external Model JSON -> preview -> apply proof that produces an intentional visible character variation without arbitrary vertex authoring.
- Exercise a representative attached component, parameter regeneration, manual artist edits, save/reopen and validation.
- Gate: all three providers use the shared construction contract; no duplicate full construction pipeline survives migration; artist ownership remains intact; visual reviews are accepted, not inferred from manifold tests.

### 5. Animation quality pass

Begin final motion tuning after each provider's anatomy and rest rig are accepted. Simple diagnostic poses accompany every earlier milestone.

- Shared motion tools: cycle phase, timing, contact intervals, stance/swing trajectories, loop continuity and review metrics. Recipes supply limb roles, gait phase relationships, bend planes, body response and joint limits.
- Human: Idle / Walk / Run, with foot contact, reduced sliding, weight shift, pelvis/torso counter-motion and natural arm swing.
- Quadruped: Idle / Walk / Run, with deliberate footfall patterns, coordinated fore/hind support, body bounce and restrained head/tail follow-through. Choose and document one run gait for alpha.
- Avian: Idle / Walk / Flight, with planted steps, balance/head response, coordinated wing strokes and folding, and tail response. Takeoff/landing and Avian Run are outside this milestone.
- Match in-place foot motion to a declared reference travel speed for review; do not claim zero world-space foot velocity for an in-place cycle. Root-motion generation is optional and requires a separate explicit contract if added.
- Gate: inspect at least three cycles from front/side/three-quarter views on default and contrasting proportions. No reversed joints, obvious ground penetration, loop pops, detached regions or severe collapse. Record contact drift, loop discontinuity and runtime; set numerical thresholds from the baseline before final acceptance.
- Preserve generated clip identity, artist-owned Actions/NLA, preview/apply, animation tuning and export naming. Verify exported clips in destination, not only Blender playback.

### 6. Alpha candidate and release hardening

- Run full core, Blender, packaged-install and save/reopen checks on the candidate commit.
- Repeat representative destination checks after the anatomy/animation changes: mesh, scale, materials and clips for advertised engine paths; Cura slicing if included in the release promise.
- Test clean install, disable/re-enable and uninstall; record exact ZIP/commit for manual results.
- Reconcile stale release audits, supported Blender version, public docs and known limitations. Publish comparison images and short clips showing the actual candidate.
- Choose consistent version metadata and explicitly configure a GitHub prerelease. Tag/publish only with user approval.

## Delivery discipline

Use reviewable PRs for the shared contract, Human migration, Quadruped anatomy, Avian anatomy, semantic integration, motion tools, each provider's animation tuning, and release hardening. Split further when needed. Each anatomy PR includes reproducible visual evidence and relevant regression checks; avoid one all-provider rewrite.

Keep one active implementation per migrated provider. Pre-alpha cleanup does not require compatibility aliases for retired generated identities, but must never silently regenerate saved artist work. If a topology or rig change invalidates saved managed data, report the limitation and require explicit regeneration.

Track generation, skinning, playback, export and CI timing against the baseline. Cache by full recipe/version/parameter identity. Keep render reviews parallel to functional CI and never bypass validation for speed.

## Explicitly deferred

Photoreal anatomy, facial performance rigs, detailed finger animation, exhaustive species recipes, procedural fur/feather simulation, cloth physics, universal retargeting, new provider families and broad Blender architecture rewrites. Revisit only when a demonstrated alpha workflow blocker requires them.
