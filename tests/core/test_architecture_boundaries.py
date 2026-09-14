# SPDX-License-Identifier: GPL-3.0-or-later
"""Architecture guardrails that keep the portable core Blender-independent."""

import ast
import unittest
from pathlib import Path


_REPO_ROOT = Path(__file__).resolve().parents[2]
_OBJECT_CORE = _REPO_ROOT / "object_core"
_FORBIDDEN_ROOTS = {"bpy", "blender_adapter", "humanoid_blender"}


def _import_roots(path):
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    roots = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            roots.extend(alias.name.split(".", 1)[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            roots.append(node.module.split(".", 1)[0])
    return roots


def _assigns_attribute(path, object_name, attribute_name):
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in ast.walk(tree):
        if not isinstance(node, (ast.Assign, ast.AnnAssign, ast.AugAssign)):
            continue
        targets = list(node.targets) if isinstance(node, ast.Assign) else [node.target]
        for target in targets:
            if (
                isinstance(target, ast.Attribute)
                and target.attr == attribute_name
                and isinstance(target.value, ast.Name)
                and target.value.id == object_name
            ):
                return True
    return False


class ArchitectureBoundaryTests(unittest.TestCase):
    def test_object_core_never_imports_blender_or_adapter_packages(self):
        violations = []
        for path in sorted(_OBJECT_CORE.rglob("*.py")):
            forbidden = sorted(set(_import_roots(path)) & _FORBIDDEN_ROOTS)
            if forbidden:
                violations.append(
                    "%s imports %s"
                    % (path.relative_to(_REPO_ROOT), ", ".join(forbidden))
                )

        self.assertEqual(
            [],
            violations,
            "object_core must stay host-independent:\n" + "\n".join(violations),
        )

    def test_provider_modules_never_depend_on_blender_adapter(self):
        violations = []
        provider_root = _OBJECT_CORE / "providers"
        for path in sorted(provider_root.rglob("*.py")):
            roots = set(_import_roots(path))
            if "blender_adapter" in roots or "bpy" in roots:
                violations.append(str(path.relative_to(_REPO_ROOT)))

        self.assertEqual(
            [],
            violations,
            "providers must remain portable and adapter-independent:\n"
            + "\n".join(violations),
        )

    def test_migrated_modify_modules_do_not_patch_workflow_renderer(self):
        violations = []
        for relative_path in (
            "blender_adapter/model_json_ui.py",
            "blender_adapter/asset_inspection_ui.py",
        ):
            path = _REPO_ROOT / relative_path
            if _assigns_attribute(path, "workflow_ui", "_draw_artist_modify"):
                violations.append(relative_path)

        self.assertEqual(
            [],
            violations,
            "migrated Modify presentation must compose through PresentationRegistry:\n"
            + "\n".join(violations),
        )

    def test_workspace_ui_does_not_bind_blender_panel_callbacks_directly(self):
        path = _REPO_ROOT / "blender_adapter" / "workflow_ui.py"
        source = path.read_text(encoding="utf-8")
        self.assertNotIn(".draw =", source)
        self.assertNotIn(".poll =", source)

    def test_workspace_panel_host_owns_required_blender_callback_binding(self):
        path = _REPO_ROOT / "blender_adapter" / "workspace_panel_host.py"
        source = path.read_text(encoding="utf-8")
        self.assertIn("panel_type.draw =", source)
        self.assertIn("panel_type.poll =", source)


if __name__ == "__main__":
    unittest.main()
