from blender_adapter import workspace_create_ui


class _Field:
    def __init__(self, name):
        self.name = name


class _Provider:
    label = "Human"
    parameters = tuple(_Field(name) for name in ("height", "weight", "body_type", "waist", "shoulders"))


class _UI:
    @staticmethod
    def get_provider(_key):
        return _Provider()

    @staticmethod
    def _field_name(_provider, field):
        return "field_" + field.name


class _Settings:
    object_type = "human"
    asset_assistant_create_advanced = False
    asset_assistant_workspace = "CREATE"
    asset_assistant_create_view = "GENERATE"
    target = None


class _Scene(dict):
    humanoid_settings = _Settings()


class _Context:
    scene = _Scene()


class _Node:
    def __init__(self):
        self.scale_y = 1.0
        self.scale_x = 1.0
        self.children = []
        self.labels = []
        self.props = []
        self.enums = []
        self.operators = []
        self.enabled = True

    def box(self):
        child = _Node()
        self.children.append(child)
        return child

    def row(self, align=False):
        child = _Node()
        self.children.append(child)
        return child

    def column(self, align=False):
        child = _Node()
        self.children.append(child)
        return child

    def label(self, **kwargs):
        self.labels.append(kwargs)

    def prop(self, _settings, prop, **kwargs):
        self.props.append((prop, kwargs))

    def prop_enum(self, _settings, prop, key, **kwargs):
        self.enums.append((prop, key, kwargs))

    def operator(self, op, **kwargs):
        self.operators.append((op, kwargs))

    def separator(self, **_kwargs):
        pass


class _Panel:
    def __init__(self):
        self.layout = _Node()


def _walk(node):
    yield node
    for child in node.children:
        yield from _walk(child)


def test_create_generate_uses_four_unified_asset_buttons_and_primary_action():
    panel = _Panel()
    workspace_create_ui._draw_generate(panel, _Context(), _UI(), working_asset_ui=object())

    nodes = list(_walk(panel.layout))
    asset_rows = [node for node in nodes if node.scale_y == 2.25 and node.enums]
    assert len(asset_rows) == 1
    assert asset_rows[0].enums == [
        ("object_type", "human", {"text": "Human", "icon": "USER"}),
        ("object_type", "quadruped", {"text": "Human", "icon": "ARMATURE_DATA"}),
        ("object_type", "avian", {"text": "Human", "icon": "OUTLINER_OB_MESH"}),
        ("object_type", "box", {"text": "Human", "icon": "CUBE"}),
    ]

    action_rows = [node for node in nodes if node.scale_y == 2.0 and node.operators]
    assert len(action_rows) == 1

    operators = [call for node in nodes for call in node.operators]
    assert ("asset_assistant.generate_replace_current", {"text": "Generate Human", "icon": "ADD"}) in operators
    assert not any(op == "asset_assistant.open_editable_checkpoint" for op, _kwargs in operators)


def test_start_options_make_asset_file_import_prominent(monkeypatch):
    class _FileUI:
        @staticmethod
        def draw_file_preflight_report(_layout, _scene):
            pass

    class _InspectUI:
        @staticmethod
        def draw_inspection_report(_layout, _scene):
            pass

    monkeypatch.setattr(workspace_create_ui, "_ASSET_FILE_IMPORT_UI", _FileUI)
    monkeypatch.setattr(workspace_create_ui, "_ASSET_INSPECTION_UI", _InspectUI)
    panel = _Panel()
    workspace_create_ui._draw_generate(panel, _Context(), _UI(), working_asset_ui=object())
    operators = [call for node in _walk(panel.layout) for call in node.operators]
    assert ("asset_assistant.preflight_asset_file", {"text": "Import Asset File", "icon": "IMPORT"}) in operators
    assert ("asset_assistant.inspect_selected_asset", {"text": "Inspect Selected", "icon": "VIEWZOOM"}) in operators
    assert not any(op == "asset_assistant.open_editable_checkpoint" for op, _kwargs in operators)


def test_generate_action_becomes_replace_when_a_current_asset_exists():
    marker = object()
    previous = _Context.scene.humanoid_settings.target
    try:
        _Context.scene.humanoid_settings.target = marker
        panel = _Panel()
        workspace_create_ui._draw_generate(panel, _Context(), _UI(), working_asset_ui=object())
        operators = [call for node in _walk(panel.layout) for call in node.operators]
        assert (
            "asset_assistant.generate_replace_current",
            {"text": "Replace Current with Human", "icon": "FILE_REFRESH"},
        ) in operators
    finally:
        _Context.scene.humanoid_settings.target = previous


def test_create_generate_keeps_first_three_parameters_visible_and_collapses_rest():
    panel = _Panel()
    workspace_create_ui._draw_generate(panel, _Context(), _UI(), working_asset_ui=None)

    props = [call[0] for node in _walk(panel.layout) for call in node.props]
    assert props[:3] == ["field_height", "field_weight", "field_body_type"]
    assert "field_waist" not in props
    assert "field_shoulders" not in props
    assert "asset_assistant_create_advanced" in props


def test_create_routes_generate_without_a_current_asset(monkeypatch):
    calls = []
    monkeypatch.setattr(workspace_create_ui, "_draw_generate", lambda *args: calls.append(args))
    context = _Context()
    panel = _Panel()
    assert context.scene.humanoid_settings.target is None
    workspace_create_ui._draw_create(panel, context, _UI(), None, None)
    assert len(calls) == 1
    assert calls[0][0] is panel
    assert calls[0][1] is context
