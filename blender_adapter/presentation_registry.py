# SPDX-License-Identifier: GPL-3.0-or-later
"""Explicit composition for Asset Assistant presentation renderers.

Presentation modules register named renderers or decorators here instead of replacing
callbacks in other modules.  The registry is intentionally Blender-independent so its
composition behavior can be tested without a Blender runtime.
"""


class PresentationRegistry:
    """Compose named presentation slots with visible ownership and ordering."""

    def __init__(self):
        self.clear()

    def clear(self):
        self._renderers = {}
        self._decorators = {}

    @staticmethod
    def _validate_slot(slot):
        if not isinstance(slot, str) or not slot.strip():
            raise ValueError("presentation slot must be a nonempty string")
        return slot.strip()

    @staticmethod
    def _validate_owner(owner):
        if not isinstance(owner, str) or not owner.strip():
            raise ValueError("presentation owner must be a nonempty string")
        return owner.strip()

    @staticmethod
    def _validate_callable(renderer):
        if not callable(renderer):
            raise TypeError("presentation renderer must be callable")
        return renderer

    def register_renderer(self, slot, renderer, *, owner):
        """Register the one base renderer for a slot.

        Duplicate base ownership is rejected so composition conflicts fail loudly
        instead of depending on import/install order.
        """
        slot = self._validate_slot(slot)
        owner = self._validate_owner(owner)
        renderer = self._validate_callable(renderer)
        existing = self._renderers.get(slot)
        if existing is not None:
            existing_owner, existing_renderer = existing
            if existing_owner == owner and existing_renderer is renderer:
                return renderer
            raise ValueError(
                "presentation slot %r already owned by %s" % (slot, existing_owner)
            )
        self._renderers[slot] = (owner, renderer)
        return renderer

    def decorate(self, slot, decorator, *, owner, order=100):
        """Add an explicit wrapper around a slot renderer.

        A decorator receives ``next_renderer`` followed by the renderer arguments.
        Lower order values are applied closer to the base renderer; higher values wrap
        later.  Owner names make the chain inspectable and duplicate registration safe.
        """
        slot = self._validate_slot(slot)
        owner = self._validate_owner(owner)
        decorator = self._validate_callable(decorator)
        if not isinstance(order, int):
            raise TypeError("presentation decorator order must be an integer")
        rows = self._decorators.setdefault(slot, [])
        for existing_order, existing_owner, existing_decorator in rows:
            if existing_owner == owner:
                if existing_order == order and existing_decorator is decorator:
                    return decorator
                raise ValueError(
                    "presentation slot %r already has decorator from %s" % (slot, owner)
                )
        rows.append((order, owner, decorator))
        return decorator

    def resolve(self, slot, fallback=None):
        """Return the composed renderer for ``slot`` or ``fallback`` when unowned."""
        slot = self._validate_slot(slot)
        base = self._renderers.get(slot)
        renderer = base[1] if base is not None else fallback
        if renderer is None:
            raise KeyError("no renderer registered for presentation slot %r" % slot)
        self._validate_callable(renderer)
        for _order, _owner, decorator in sorted(
            self._decorators.get(slot, ()), key=lambda row: (row[0], row[1])
        ):
            next_renderer = renderer

            def wrapped(*args, _decorator=decorator, _next=next_renderer, **kwargs):
                return _decorator(_next, *args, **kwargs)

            renderer = wrapped
        return renderer

    def owners(self, slot):
        """Return base/decorator owners for diagnostics and tests."""
        slot = self._validate_slot(slot)
        owners = []
        base = self._renderers.get(slot)
        if base is not None:
            owners.append(base[0])
        owners.extend(
            owner
            for _order, owner, _decorator in sorted(
                self._decorators.get(slot, ()), key=lambda row: (row[0], row[1])
            )
        )
        return tuple(owners)


registry = PresentationRegistry()


__all__ = ["PresentationRegistry", "registry"]
