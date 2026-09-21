# Asset Assistant: Blender adapter

## Install and use

Blender 5.2.1 is the supported runtime. Build `dist/asset_assistant.zip` with
`python -m scripts.build_blender_addon`; Blender supplies its own Python runtime.

1. In Edit > Preferences > Add-ons, choose Install from Disk and select the ZIP.
2. Enable Asset Assistant. In the 3D Viewport, press N and open Asset Assistant.
3. In Object Mode, open Create and choose Human, Quadruped, Avian or Box.
4. Generate an asset. If a current asset is selected, the Replace button identifies
   that action explicitly; preserve artist work before replacing it.
5. For Human, open Animate > Rig & Pose > Add Basic Rig, then generate a clip.
6. Use Components for attachments and Export for preparation, validation and export.

Human is one connected mesh with a deforming rig. The provider supplies geometry,
rigging and animation through the shared adapter. There is no separate static
Human model option. Inputs affect explicit generation/Modify actions, not live
procedural changes to artist geometry. See [Human workflow](human-workflow.md).

## Uninstall or temporarily disable

1. Open **Edit > Preferences > Add-ons**.
2. Search for **Asset Assistant**.
3. Uncheck the add-on to disable it immediately.
4. To uninstall its files, expand its entry with the arrow, click **Remove**, and confirm.
5. If Auto-Save Preferences is off, choose **Save Preferences**. Restart Blender to
   finish clearing loaded modules.

Disabling or removing the add-on removes its sidebar and controls. Generated
collections and editable meshes stay in your scene, including their custom
metadata. Saved blend files, this source repository, and downloaded ZIPs are
unaffected. Generated rigs and weights also remain usable after removal.

## Update from an earlier version

Save your scene, remove the old add-on using the steps above, and restart Blender.
Build or download `dist/asset_assistant.zip`, install it, then enable **Asset Assistant**.
The release archive is named `asset_assistant.zip`, but the internal Blender module
ID intentionally remains `humanoid_blender` for compatibility with earlier installs
and saved workflows. Existing `humanoid.*` operator IDs and saved
`scene.humanoid_settings` data are also retained. Existing generated models are
preserved and older generator metadata remains recognized.

The 3D Viewport sidebar has separate Generator, Rigging, Animations, Validation,
and Export tabs. See [file export instructions](targets.md) for Godot, Cura, Unity
and Unreal. Humanoid is joined by Box in Object Type; Box has dimension controls
and uses static validation. The Animations tab can generate a looping idle on a
fresh rig; see [animation instructions](animation.md).

## Build

From the repository root:

```powershell
python -m scripts.build_blender_addon
```

The build creates `dist/asset_assistant.zip` and copies the current independent
core into the add-on ZIP automatically. It also includes the full GPL license and
project notices. There is no manually maintained second copy and no pip install is
needed inside Blender. Rebuild and reinstall after code changes; restart Blender
after updating an already loaded add-on to avoid stale modules.

## Test

GitHub Actions configures Python 3.9 through 3.12 and Blender 2.92.0/5.2.1 jobs on
pull requests, pushes to main, and manual runs. Blender jobs verify the official
archive checksum and run `scripts/test_blender.py` headlessly. Remote CI results
must be checked on the PR.

Ordinary Python tests skip Blender integration tests explicitly:

```powershell
python -m unittest discover -s tests -v
```

Run the full suite with the installed Blender:

```powershell
& 'C:\Program Files\Blender Foundation\Blender 2.92\blender.exe' --background --factory-startup --python-exit-code 1 --python scripts/test_blender.py
```

This uses a separate Blender process and does not alter your open scene or saved
preferences. Integration tests use private temporary scenes and clean up their own
data.

## Boundaries

`object_core` creates proportions and mesh data. `blender_adapter/adapter.py` only
creates Blender data blocks from that mesh. `blender_adapter/core_gateway.py` is
the adapter's bridge to the independent core. `ui.py` handles the sidebar, artist
inputs, cursor placement, and selection. Core code does not import Blender APIs.

The adapter preserves source axes (Z up, positive Y forward). It converts source
centimeters using `0.01 / scene.unit_settings.scale_length`. At default unit scale,
a 180 cm character is 1.8 Blender units tall. It does not change the scene's unit
system or scale.

## Check the release ZIP

After building, run the isolated package check in a separate Blender process:

```powershell
& 'C:\Program Files\Blender Foundation\Blender 2.92\blender.exe' --background --factory-startup --python-exit-code 1 --python scripts/test_blender_package.py
```

This extracts `dist/asset_assistant.zip` into a temporary folder, removes checkout
import access, registers the bundled add-on, verifies its **Asset Assistant**
identity, and generates test assets. It saves `artifacts/blockout-preview.blend`
and `artifacts/blockout-preview.png` for visual review. These generated files are
ignored by Git.
