from types import SimpleNamespace
from contextlib import contextmanager
from pathlib import Path

from blender_adapter import asset_file_import_ui


def test_file_picker_exposes_every_supported_asset_extension():
    assert asset_file_import_ui._FILTER_GLOB == "*.blend;*.glb;*.gltf;*.fbx"
    assert asset_file_import_ui._SUPPORTED_EXTENSIONS == {".blend", ".glb", ".gltf", ".fbx"}


def test_external_exchange_files_are_preflighted_without_import(tmp_path):
    filepath = tmp_path / "maxine.glb"
    filepath.write_bytes(b"placeholder")

    report = asset_file_import_ui.preflight_asset_file(filepath)

    assert report["status"] == "EXTERNAL_ASSET"
    assert report["candidate"] == "maxine"
    assert report["extension"] == ".glb"
    assert any("ownership" in line.lower() for line in report["notes"])


def test_fbx_exchange_files_are_preflighted_without_import(tmp_path):
    filepath = tmp_path / "maxine.fbx"
    filepath.write_bytes(b"placeholder")

    report = asset_file_import_ui.preflight_asset_file(filepath)

    assert report["status"] == "EXTERNAL_ASSET"
    assert report["candidate"] == "maxine"
    assert report["extension"] == ".fbx"


def test_unsupported_file_type_is_rejected(tmp_path):
    filepath = tmp_path / "asset.obj"
    filepath.write_text("placeholder")

    try:
        asset_file_import_ui.preflight_asset_file(filepath)
    except ValueError as error:
        assert ".blend" in str(error)
        assert ".fbx" in str(error)
    else:
        raise AssertionError("unsupported file type should be rejected")


def test_blend_with_one_collection_and_no_scene_signals_is_asset_candidate(monkeypatch, tmp_path):
    filepath = tmp_path / "character.blend"
    filepath.write_bytes(b"placeholder")

    class _DataFrom:
        collections = ["Maxine"]
        scenes = ["Scene"]
        objects = ["Maxine", "Body", "Rig"]
        meshes = ["BodyMesh"]
        armatures = ["RigData"]
        actions = ["Idle", "Walk"]
        cameras = []
        lights = []

    @contextmanager
    def _load(_filepath, link=False):
        assert link is False
        yield _DataFrom(), object()

    monkeypatch.setattr(asset_file_import_ui, "bpy", SimpleNamespace(data=SimpleNamespace(libraries=SimpleNamespace(load=_load))))

    report = asset_file_import_ui.preflight_asset_file(filepath)

    assert report["status"] == "ASSET_CANDIDATE"
    assert report["candidate"] == "Maxine"
    assert report["candidates"] == ("Maxine",)
    assert any("Nothing has been appended" in line for line in report["notes"])


def test_blend_with_multiple_collections_returns_explicit_choices(monkeypatch, tmp_path):
    filepath = tmp_path / "project.blend"
    filepath.write_bytes(b"placeholder")

    class _DataFrom:
        collections = ["Maxine", "Sword", "Environment"]
        scenes = ["Scene"]
        objects = ["Maxine", "Sword", "Ground"]
        meshes = ["Body", "Blade", "GroundMesh"]
        armatures = ["Rig"]
        actions = []
        cameras = ["Camera"]
        lights = ["Key"]

    @contextmanager
    def _load(_filepath, link=False):
        yield _DataFrom(), object()

    monkeypatch.setattr(asset_file_import_ui, "bpy", SimpleNamespace(data=SimpleNamespace(libraries=SimpleNamespace(load=_load))))

    report = asset_file_import_ui.preflight_asset_file(filepath)

    assert report["status"] == "MULTIPLE_CANDIDATES"
    assert report["candidate"] == ""
    assert report["candidates"] == ("Maxine", "Sword", "Environment")
    assert any("choose" in line.lower() for line in report["notes"])
    assert any("project-level" in line.lower() for line in report["notes"])


def test_choose_blend_candidate_only_selects_preflighted_collection():
    scene = {
        asset_file_import_ui._STATUS_KEY: "MULTIPLE_CANDIDATES",
        asset_file_import_ui._CANDIDATE_KEY: "",
        asset_file_import_ui._CANDIDATES_KEY: "Maxine\nSword\nEnvironment",
        asset_file_import_ui._SUMMARY_KEY: "old summary",
    }

    selected = asset_file_import_ui.choose_blend_candidate(scene, "Sword")

    assert selected == "Sword"
    assert scene[asset_file_import_ui._STATUS_KEY] == "ASSET_CANDIDATE"
    assert scene[asset_file_import_ui._CANDIDATE_KEY] == "Sword"
    assert "Selected collection: Sword" in scene[asset_file_import_ui._SUMMARY_KEY]


def test_choose_blend_candidate_rejects_uninspected_collection():
    scene = {
        asset_file_import_ui._STATUS_KEY: "MULTIPLE_CANDIDATES",
        asset_file_import_ui._CANDIDATES_KEY: "Maxine\nSword",
    }

    try:
        asset_file_import_ui.choose_blend_candidate(scene, "Camera")
    except ValueError as error:
        assert "collection candidates" in str(error)
    else:
        raise AssertionError("uninspected collection should be rejected")


def test_completed_import_clears_transaction_only_preflight_state():
    scene = {
        asset_file_import_ui._FILEPATH_KEY: "/tmp/maxine.glb",
        asset_file_import_ui._STATUS_KEY: "EXTERNAL_ASSET",
        asset_file_import_ui._SUMMARY_KEY: "old message",
        asset_file_import_ui._CANDIDATE_KEY: "maxine",
        asset_file_import_ui._CANDIDATES_KEY: "",
    }

    asset_file_import_ui.clear_file_preflight_state(scene)

    assert not any(key in scene for key in asset_file_import_ui._PREFLIGHT_KEYS)


def test_successful_reimport_replaces_previous_group_only_after_finalize():
    scene = {
        asset_file_import_ui._STATUS_KEY: "EXTERNAL_ASSET",
        asset_file_import_ui._SUMMARY_KEY: "pending",
    }

    class _ImportedRoot:
        def get(self, key, default=None):
            if key == asset_file_import_ui._IMPORT_GROUP_KEY:
                return "new-group"
            return default

    removed = []
    result = asset_file_import_ui._finalize_import_replacement(
        scene,
        _ImportedRoot(),
        "old-group",
        remove_group=removed.append,
    )

    assert result == "new-group"
    assert removed == ["old-group"]
    assert scene[asset_file_import_ui._CURRENT_IMPORT_GROUP_KEY] == "new-group"
    assert asset_file_import_ui._STATUS_KEY not in scene
    assert asset_file_import_ui._SUMMARY_KEY not in scene


def test_first_import_does_not_attempt_to_remove_unrelated_scene_content():
    scene = {}

    class _ImportedRoot:
        def get(self, key, default=None):
            return "first-group" if key == asset_file_import_ui._IMPORT_GROUP_KEY else default

    removed = []
    asset_file_import_ui._finalize_import_replacement(
        scene,
        _ImportedRoot(),
        "",
        remove_group=removed.append,
    )

    assert removed == []
    assert scene[asset_file_import_ui._CURRENT_IMPORT_GROUP_KEY] == "first-group"


def test_artist_import_clears_stale_asset_assistant_target():
    stale_target = object()

    class _Settings:
        target = stale_target

    class _Scene:
        humanoid_settings = _Settings()

    class _Context:
        scene = _Scene()

    result = asset_file_import_ui._sync_imported_asset_context(
        _Context(),
        {"status": "REVIEW", "root": object()},
    )

    assert result is None
    assert _Context.scene.humanoid_settings.target is None


def test_recognized_asset_assistant_import_becomes_current_target():
    imported_root = object()

    class _Settings:
        target = None

    class _Scene:
        humanoid_settings = _Settings()

    class _Context:
        scene = _Scene()

    result = asset_file_import_ui._sync_imported_asset_context(
        _Context(),
        {"status": "READY", "root": imported_root},
    )

    assert result is imported_root
    assert _Context.scene.humanoid_settings.target is imported_root
