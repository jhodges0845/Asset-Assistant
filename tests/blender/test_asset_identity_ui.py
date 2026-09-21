# SPDX-License-Identifier: GPL-3.0-or-later
"""Tests for artist-facing asset identity UI."""

from blender_adapter import asset_identity_ui


class _Target(dict):
    name = "Maxine"


class _Node:
    def __init__(self):
        self.labels = []
        self.props = []
        self.children = []

    def box(self):
        child = _Node()
        self.children.append(child)
        return child

    def column(self, align=False):
        child = _Node()
        self.children.append(child)
        return child

    def label(self, **kwargs):
        self.labels.append(kwargs)

    def prop(self, target, prop, **kwargs):
        self.props.append((target, prop, kwargs))


def test_generated_assets_keep_display_name_separate_from_type_and_source(monkeypatch):
    target = _Target(
        generator="object_generator",
        object_type="human",
        asset_assistant_source="GENERATED",
    )

    monkeypatch.setattr(asset_identity_ui, "_provider_label", lambda _target: "Human")

    layout = _Node()
    identity = asset_identity_ui._draw_identity(layout, target)

    assert identity.props == [(target, "name", {"text": "Name"})]
    details = identity.children[0]
    assert {row["text"] for row in details.labels} == {
        "Type: Human",
        "Source: Generated",
    }


def test_source_label_supports_imported_legacy_and_external_assets():
    assert asset_identity_ui._source_label(_Target(asset_assistant_source="IMPORTED")) == "Imported"
    assert asset_identity_ui._source_label(_Target(asset_assistant_source="ADOPTED")) == "Imported / Adopted"
    assert asset_identity_ui._source_label(_Target(generator="object_generator")) == "Generated"
    assert asset_identity_ui._source_label(_Target()) == "External / Unclassified"


def test_component_label_uses_component_language():
    assert asset_identity_ui._component_label(0) == "0 Components"
    assert asset_identity_ui._component_label(1) == "1 Component"
    assert asset_identity_ui._component_label(2) == "2 Components"
