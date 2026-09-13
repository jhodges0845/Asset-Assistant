from types import SimpleNamespace

from blender_adapter import rig_animate_ui


class _Layout:
    def __init__(self):
        self.labels = []
        self.separators = 0

    def label(self, **kwargs):
        self.labels.append(kwargs)

    def separator(self, **_kwargs):
        self.separators += 1


class _Panel:
    def __init__(self):
        self.layout = _Layout()


def test_create_modes_no_longer_include_rig():
    assert [key for key, _label, _icon in rig_animate_ui._CREATE_MODES] == ["GENERATE", "MODIFY"]


def test_install_moves_legacy_rig_create_state_to_modify_and_draws_rig_before_animation(monkeypatch):
    calls = []

    class Workflow:
        @staticmethod
        def _section_header(layout, title, subtitle, icon):
            calls.append(("header", title, subtitle, icon))

        @staticmethod
        def _stage_proxy(panel, stage):
            return SimpleNamespace(layout=panel.layout, stage=stage)

        @staticmethod
        def _draw_create(panel, context, ui, modify_ui, working_asset_ui):
            calls.append(("create", context.scene.humanoid_settings.asset_assistant_create_view))

        @staticmethod
        def _draw_animate(panel, context, ui, animation_names_ui, animation_adoption_ui):
            calls.append(("animate",))

    class WorkspaceCreate:
        _CREATE_MODES = (("GENERATE", "Generate", "ADD"), ("MODIFY", "Modify", "MODIFIER"), ("RIG", "Rig", "ARMATURE_DATA"))

    class Normalized:
        @staticmethod
        def _draw_imported_animation_header(_panel, _context, _root):
            return False

    class WorkflowPanel:
        @staticmethod
        def draw(proxy, _context):
            calls.append(("stage", proxy.stage))

    ui = SimpleNamespace(_WorkflowPanel=WorkflowPanel)
    settings = SimpleNamespace(asset_assistant_create_view="RIG")
    context = SimpleNamespace(scene=SimpleNamespace(humanoid_settings=settings))

    monkeypatch.setattr(rig_animate_ui, "asset_rigs", lambda _root: ())
    rig_animate_ui.install(Workflow, WorkspaceCreate, Normalized)

    assert WorkspaceCreate._CREATE_MODES == rig_animate_ui._CREATE_MODES

    Workflow._draw_create(_Panel(), context, ui, None, None)
    assert settings.asset_assistant_create_view == "MODIFY"
    assert ("create", "MODIFY") in calls

    Workflow._draw_animate(_Panel(), context, ui, None, None)
    assert calls.index(("stage", "RIGGING")) < calls.index(("animate",))
    assert any(call[0:2] == ("header", "RIG & POSE") for call in calls)
