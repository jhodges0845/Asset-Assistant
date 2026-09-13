# SPDX-License-Identifier: GPL-3.0-or-later
"""Regression coverage for imported Animate and summary normalization."""

from types import SimpleNamespace

from blender_adapter import normalized_import_workflow_ui as normalized_ui


class _Obj(dict):
    def __init__(self, name, obj_type="EMPTY", **metadata):
        super().__init__(metadata)
        self.name = name
        self.type = obj_type


class _Node:
    def __init__(self):
        self.enabled = True
        self.scale_y = 1.0
        self.labels = []
        self.operators = []
        self.children = []

    def box(self):
        child = _Node()
        self.children.append(child)
        return child

    def row(self, align=False):
        child = _Node()
        self.children.append(child)
        return child

    def label(self, **kwargs):
        self.labels.append(kwargs)

    def operator(self, operator, **kwargs):
        self.operators.append((operator, kwargs))
        return SimpleNamespace()

    def prop(self, *args, **kwargs):
        return None

    def separator(self, *args, **kwargs):
        return None


def test_component_count_ignores_base_import_meshes_and_deduplicates_component_members():
    base_mesh = _Obj("Body", "MESH")
    hair_root = _Obj("Hair", "EMPTY", asset_assistant_component_id="hair-1")
    hair_mesh = _Obj("HairMesh", "MESH", asset_assistant_component_id="hair-1")
    bracelet = _Obj("Bracelet", "MESH", asset_assistant_component_id="bracelet-1")

    assert normalized_ui._component_count({"objects": (base_mesh, hair_root, hair_mesh, bracelet)}) == 2


def test_animation_adoption_uses_normalized_rig_lookup(monkeypatch):
    target = _Obj("Imported Asset")
    nested_rig = _Obj("Armature", "ARMATURE")
    monkeypatch.setattr(normalized_ui, "asset_rigs", lambda root: (nested_rig,) if root is target else ())

    box = _Node()
    normalized_ui._draw_animation_adoption(box, target)

    action_row = box.children[0]
    assert action_row.enabled is True
    assert action_row.operators[0][0] == "asset_assistant.adopt_animation_action"


def test_imported_animate_bypasses_generated_provider_stage(monkeypatch):
    target = _Obj("Imported Asset", asset_assistant_external_asset=True)
    rig = _Obj("ImportedRig", "ARMATURE")
    monkeypatch.setattr(normalized_ui, "asset_rigs", lambda root: (rig,))
    monkeypatch.setattr(normalized_ui, "is_external_asset", lambda root: root is target)

    original_calls = []
    workflow_ui = SimpleNamespace()
    workflow_ui._draw_animate = lambda *args: original_calls.append(args)
    workflow_ui._section_header = lambda *args, **kwargs: None
    workflow_ui._draw_animation_adoption = None

    identity_ui = SimpleNamespace(_draw_summary=lambda *args: None, _component_label=lambda count: f"{count} Components")
    ui = SimpleNamespace()
    normalized_ui.install(workflow_ui, identity_ui, ui)

    layout = _Node()
    panel = SimpleNamespace(layout=layout)
    context = SimpleNamespace(scene=SimpleNamespace(humanoid_settings=SimpleNamespace(target=target)))

    class _ClipPanel:
        @staticmethod
        def draw(_panel, _context):
            return None

    animation_names = SimpleNamespace(ASSET_ASSISTANT_PT_animation_names=_ClipPanel)
    workflow_ui._draw_animate(panel, context, ui, animation_names, object())

    assert original_calls == []
    flattened_operators = [op for child in layout.children for op in child.operators]
    assert any(op[0] == "asset_assistant.select_base_rig" for op in flattened_operators)
    assert any(op[0] == "asset_assistant.pose_base_rig" for op in flattened_operators)
