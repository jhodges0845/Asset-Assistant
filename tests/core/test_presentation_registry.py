import unittest

from blender_adapter.presentation_registry import PresentationRegistry


class PresentationRegistryTests(unittest.TestCase):
    def test_base_renderer_resolves(self):
        registry = PresentationRegistry()

        def renderer(value):
            return "base:" + value

        registry.register_renderer("workspace.create", renderer, owner="create")
        self.assertEqual("base:x", registry.resolve("workspace.create")("x"))
        self.assertEqual(("create",), registry.owners("workspace.create"))

    def test_duplicate_base_owner_fails_loudly(self):
        registry = PresentationRegistry()
        registry.register_renderer("workspace.create", lambda: None, owner="first")

        with self.assertRaisesRegex(ValueError, "already owned by first"):
            registry.register_renderer("workspace.create", lambda: None, owner="second")

    def test_decorators_compose_by_explicit_order(self):
        registry = PresentationRegistry()
        events = []

        def renderer(value):
            events.append("base")
            return value

        def inner(next_renderer, value):
            events.append("inner-before")
            result = next_renderer(value + "-inner")
            events.append("inner-after")
            return result

        def outer(next_renderer, value):
            events.append("outer-before")
            result = next_renderer(value + "-outer")
            events.append("outer-after")
            return result

        registry.register_renderer("workspace.animate", renderer, owner="animate")
        registry.decorate("workspace.animate", outer, owner="outer", order=200)
        registry.decorate("workspace.animate", inner, owner="inner", order=100)

        result = registry.resolve("workspace.animate")("start")

        self.assertEqual("start-outer-inner", result)
        self.assertEqual(
            ["outer-before", "inner-before", "base", "inner-after", "outer-after"],
            events,
        )
        self.assertEqual(("animate", "inner", "outer"), registry.owners("workspace.animate"))

    def test_fallback_can_be_decorated_without_registered_base(self):
        registry = PresentationRegistry()

        def wrapper(next_renderer, value):
            return "wrapped:" + next_renderer(value)

        registry.decorate("workspace.export", wrapper, owner="export.wrapper")
        resolved = registry.resolve("workspace.export", lambda value: "fallback:" + value)
        self.assertEqual("wrapped:fallback:x", resolved("x"))

    def test_clear_removes_renderers_and_decorators(self):
        registry = PresentationRegistry()
        registry.register_renderer("shared.summary", lambda: None, owner="summary")
        registry.decorate("shared.summary", lambda next_renderer: next_renderer(), owner="wrapper")
        registry.clear()

        self.assertEqual((), registry.owners("shared.summary"))
        with self.assertRaises(KeyError):
            registry.resolve("shared.summary")


if __name__ == "__main__":
    unittest.main()
