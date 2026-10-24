from types import SimpleNamespace
from blender_adapter import asset_structure


class _Object:
    def __init__(self, name, type="EMPTY", parent=None, **metadata):
        self.name = name
        self.type = type
        self.parent = parent
        self.children = []
        self.modifiers = []
        self.animation_data = None
        self._metadata = metadata
        if parent is not None:
            parent.children.append(self)

    def get(self, key, default=None):
        return self._metadata.get(key, default)


class _Modifier:
    type = "ARMATURE"

    def __init__(self, obj):
        self.object = obj


class _AnimationData:
    def __init__(self, action=None, tracks=()):
        self.action = action
        self.nla_tracks = tuple(SimpleNamespace(strips=(SimpleNamespace(action=action),)) for action in tracks)


def test_generated_hierarchy_uses_complete_tree_not_only_direct_children():
    root = _Object("Generated")
    wrapper = _Object("Wrapper", parent=root)
    mesh = _Object("Body", type="MESH", parent=wrapper)
    rig = _Object("Rig", type="ARMATURE", parent=root)
    rig.animation_data = _AnimationData(action=object(), tracks=(object(),))

    structure = asset_structure.logical_asset(root, objects=(root, wrapper, mesh, rig))

    assert structure["root"] is root
    assert structure["meshes"] == (mesh,)
    assert structure["rigs"] == (rig,)
    assert structure["animation_count"] == 2


def test_import_group_unifies_sibling_mesh_and_rig_under_marked_root():
    group = "glb-123"
    root = _Object("ImportedRoot", asset_assistant_import_group=group, asset_assistant_import_root=True)
    mesh = _Object("Body", type="MESH", asset_assistant_import_group=group)
    rig = _Object("Rig", type="ARMATURE", asset_assistant_import_group=group)
    rig.animation_data = _AnimationData(action=object(), tracks=(object(), object()))
    mesh.modifiers.append(_Modifier(rig))
    unrelated = _Object("Camera")

    structure = asset_structure.logical_asset(mesh, objects=(root, mesh, rig, unrelated))

    assert structure["root"] is root
    assert structure["objects"] == (root, mesh, rig)
    assert structure["meshes"] == (mesh,)
    assert structure["rigs"] == (rig,)
    assert structure["animation_count"] == 3


def test_modifier_referenced_rig_is_part_of_logical_rig_set_without_double_counting():
    root = _Object("ArtistRoot")
    mesh = _Object("Body", type="MESH", parent=root)
    rig = _Object("ExternalRig", type="ARMATURE")
    rig.animation_data = _AnimationData(action=object())
    mesh.modifiers.append(_Modifier(rig))

    rigs = asset_structure.asset_rigs(root, objects=(root, mesh, rig))
    count = asset_structure.asset_animation_count(root, objects=(root, mesh, rig))

    assert rigs == (rig,)
    assert count == 1


def test_component_owned_rig_does_not_create_false_multi_rig_base_asset():
    root = _Object("Generated")
    body = _Object("Body", type="MESH", parent=root)
    base_rig = _Object("Rig", type="ARMATURE", parent=root)
    base_rig.animation_data = _AnimationData(action=object())

    component_root = _Object(
        "Gauntlet",
        parent=root,
        asset_assistant_component_id="component-gauntlet",
    )
    component_mesh = _Object(
        "GauntletMesh",
        type="MESH",
        parent=component_root,
        asset_assistant_component_id="component-gauntlet",
    )
    component_rig = _Object(
        "GauntletRig",
        type="ARMATURE",
        parent=component_root,
        asset_assistant_component_id="component-gauntlet",
        asset_assistant_component_rig=True,
    )
    component_rig.animation_data = _AnimationData(action=object())
    component_mesh.modifiers.append(_Modifier(component_rig))

    structure = asset_structure.logical_asset(
        root,
        objects=(root, body, base_rig, component_root, component_mesh, component_rig),
    )

    assert structure["objects"] == (root, body, base_rig, component_root, component_mesh, component_rig)
    assert structure["base_objects"] == (root, body, base_rig)
    assert structure["meshes"] == (body,)
    assert structure["rigs"] == (base_rig,)
    assert structure["animation_count"] == 1
