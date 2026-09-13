# Model JSON round trip

Asset Assistant supports an LLM-assisted model modification path alongside direct Blender editing.

## Workflow

1. Open **Create > Modify** for a generated Asset Assistant asset.
2. Choose **Export Model Context JSON**.
3. Give that JSON to an LLM with an artistic request, for example: `Make the shoulders slightly narrower and the silhouette more athletic. Return only an Asset Assistant Model Change JSON.`
4. The LLM returns a request using the exact `asset-assistant.modify-request/v3` schema embedded in the context file.
5. Choose **Import Model Change JSON**. Import validates and previews; it does not mutate the model.
6. Review the change summary and blockers.
7. Choose **Apply Validated Model Changes**. Asset Assistant re-inspects the current asset, re-plans the request, and applies only supported changes.

## Contract

The exported context is self-documenting. It includes:

- Asset Assistant product/version/repository identity.
- Exact return schema and example.
- Stable asset id and provider id.
- Current provider values plus valid parameter ranges or choices.
- Declared semantic targets and which operations are executable.
- Previously applied semantic operations.
- Current geometry/rig/material/animation ownership flags.
- Attached component state and warnings from the underlying portable inspection document.
- Explicit preservation and authoring rules.

The file tells the LLM to author **relative changes to the current asset**, not to reconstruct a replacement mesh from scratch.

## Safety and ownership

The JSON path uses the same preservation-first Modify architecture as manual changes. Import is non-mutating. Apply re-inspects the asset before mutation and blocks requests that violate ownership or provider capability rules.

Generated provider parameters and executable semantic operations are supported today. Arbitrary raw vertex editing is intentionally not part of this contract.

Imported/artist-authored base assets remain a follow-up for the richer model-context work tracked in issue #236. Their geometry cannot safely be treated as if it had original provider parameters; future support should use derived measurements/landmarks and explicitly scoped artist-safe operations.

## Design rule

`Inspect -> Understand -> Propose -> Preview -> Apply`

The LLM JSON path is an additional artist workflow. It does not replace Blender Edit Mode, Sculpt Mode, rigging, material editing, or other direct artist control.
