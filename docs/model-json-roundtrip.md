# Model JSON round trip

Asset Assistant supports an LLM-assisted model modification path alongside direct Blender editing.

## Workflow

1. Open **Create > Modify** for a generated Asset Assistant asset.
2. Choose **Export Model Context JSON**.
3. Give that JSON to an LLM with an artistic request, for example: `Make the shoulders slightly narrower and the silhouette more athletic. Return only an Asset Assistant Model Change JSON.`
4. The LLM returns a request using the exact `asset-assistant.modify-request/v3` schema embedded in the context file.
5. Choose **Import Model Change JSON**. Import validates the request and does not mutate the live model.
6. Choose **Preview Model Changes** to build a temporary visual result while leaving the live asset unchanged.
7. Review the proposed result. Cancel the preview to return to the original, or continue when the preview is acceptable.
8. Choose **Apply Model Changes**. Asset Assistant re-inspects the current asset, re-plans the request, re-checks ownership/capability, and applies only supported changes.

The intended interaction is explicit:

`Export Context -> Import Change -> Preview Change -> Apply Change`

## Contract

The exported context is self-documenting. It includes:

- Asset Assistant product/version/repository identity.
- Exact return schema and example.
- Stable asset id and provider id.
- Current provider values plus valid parameter ranges or serialized enum choices.
- Declared semantic targets and which operations are executable.
- Machine-readable argument contracts for executable Human semantic operations, including supported profile values and numeric ranges where applicable.
- A compact current semantic model state/measurement summary so the LLM can reason from current state toward desired state rather than guessing from labels alone.
- Previously applied semantic operations.
- Current geometry/rig/material/animation ownership flags.
- Attached component state and warnings from the underlying portable inspection document.
- Explicit preservation and authoring rules.

The file tells the LLM to author **relative changes to the current asset**, not to reconstruct a replacement mesh from scratch. Full raw mesh/vertex export is intentionally not the default model-editing contract; semantic/provider controls remain the preferred abstraction.

## Validated checkpoint

The generated-Human round trip has now been exercised end to end with an LLM-authored request. The request produced a visibly different Human silhouette and demonstrated that the semantic/provider pipeline can carry meaningful artistic intent into generated geometry.

A validation regression was also identified during that test: Blender/provider enum choices are represented internally as value/label pairs, while the JSON contract uses the serialized value. Modify validation must compare against the serialized enum token (for example `slim`) rather than the full Blender choice tuple. This preserves strict validation while accepting choices that are valid in the UI and provider contract.

This checkpoint establishes that the **round-trip architecture is viable**. Current visual quality is now limited primarily by the expressive geometry/topology of the Human provider rather than by the JSON transport design.

## Human geometry direction

Do not make the LLM responsible for authoring arbitrary vertex coordinates. Asset Assistant should own known-good Human construction/topology and expose higher-level semantic controls. The LLM describes artistic intent through the published contract; the Human provider translates that intent into predictable geometry.

The next Human quality direction is provisionally **Advanced Human Geometry / Human Provider V2**:

1. **Anatomy/topology** — improve the neck/shoulder transition, clavicle/chest, ribcage, waist, pelvis/hips/glutes, thighs/knees/calves/ankles, upper/lower arms, elbows/wrists/hands, and head/face topology so semantic changes have enough geometry to produce believable results and deform well.
2. **Semantic anatomy profiles** — expand controllable regions such as pelvis, waist, chest/bust, glutes, thighs, knees, calves, neck, hands, jaw, chin, cheekbones, brow, eyes, nose and lips while keeping hair, clothing and accessories as separate components.
3. **Surface/detail** — later improve smoothing/subdivision/normals, facial detail and materials without making those concerns prerequisites for the semantic architecture.

A useful acceptance test is high-fidelity hero-character refinement: generate a recognizable, game-ready-ish neutral Human base and move its anatomy, silhouette and face substantially toward a supplied character direction through semantic Model JSON before attaching hair, clothing and accessories.

Human V1 does not need to be discarded. It can remain a lightweight/blockout path while a higher-fidelity path develops. Whether fidelity becomes dynamically selected later is intentionally left open; no architecture decision is required yet.

## Safety and ownership

The JSON path uses the same preservation-first Modify architecture as manual changes. Import is non-mutating. Preview must not mutate the live asset. Apply re-inspects the asset before mutation and blocks requests that violate ownership or provider capability rules.

Generated provider parameters and executable semantic operations are supported today. Arbitrary raw vertex editing is intentionally not part of this contract.

Imported/artist-authored base assets remain a follow-up for the richer model-context work tracked in issue #236. Their geometry cannot safely be treated as if it had original provider parameters; future support should use derived measurements/landmarks and explicitly scoped artist-safe operations.

## Follow-up cleanup

The current context may expose semantic target definitions in more than one section for convenience. Longer term, keep one canonical target definition and have secondary vocabulary/guidance reference it so the payload stays smaller and duplicate definitions cannot drift.

## Design rule

`Inspect -> Understand -> Propose -> Preview -> Apply`

The LLM JSON path is an additional artist workflow. It does not replace Blender Edit Mode, Sculpt Mode, rigging, material editing, or other direct artist control.
