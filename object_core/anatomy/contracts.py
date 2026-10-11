# SPDX-License-Identifier: GPL-3.0-or-later
"""Body-plan-independent immutable anatomy data. Coordinates are centimeters."""
from __future__ import annotations
from dataclasses import dataclass
from math import isfinite
from typing import Mapping, Protocol, Union

Scalar = Union[str, float, int, bool]
Vector = tuple[float, float, float]


def _name(value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError('anatomy names must be nonempty strings')


def _vector(value):
    result = tuple(value)
    if len(result) != 3:
        raise ValueError('vectors must have three coordinates')
    if any(isinstance(v, bool) or not isinstance(v, (int, float)) for v in result):
        raise TypeError('coordinates must be numbers')
    result = tuple(float(v) for v in result)
    if not all(isfinite(v) for v in result):
        raise ValueError('coordinates must be finite')
    return result


def _indices(values):
    result = tuple(values)
    if any(type(v) is not int or v < 0 for v in result):
        raise ValueError('indices must be nonnegative integers')
    if len(set(result)) != len(result):
        raise ValueError('indices must be unique')
    return result


@dataclass(frozen=True)
class Landmark:
    name: str
    position: Vector

    def __post_init__(self):
        _name(self.name)
        object.__setattr__(self, 'position', _vector(self.position))


@dataclass(frozen=True)
class AnatomyRegion:
    """Authored topology ownership, stable under semantic vertex movement."""
    name: str
    mesh_part: str
    vertex_indices: tuple[int, ...]

    def __post_init__(self):
        _name(self.name)
        _name(self.mesh_part)
        object.__setattr__(self, 'vertex_indices', tuple(sorted(_indices(self.vertex_indices))))


@dataclass(frozen=True)
class JointChain:
    """Landmark path with one bone per segment and model-space bend direction."""
    name: str
    landmarks: tuple[str, ...]
    bones: tuple[str, ...]
    parent_bone: str | None = None
    bend_direction: Vector | None = None
    motion_role: str | None = None

    def __post_init__(self):
        _name(self.name)
        for field in ('landmarks', 'bones'):
            values = tuple(getattr(self, field))
            for value in values:
                _name(value)
            if len(set(values)) != len(values):
                raise ValueError('chain entries must be unique')
            object.__setattr__(self, field, values)
        if not self.bones or len(self.landmarks) != len(self.bones) + 1:
            raise ValueError('a chain needs one more landmark than bones')
        for value in (self.parent_bone, self.motion_role):
            if value is not None:
                _name(value)
        if self.bend_direction is not None:
            direction = _vector(self.bend_direction)
            if not any(direction):
                raise ValueError('bend direction must be nonzero')
            object.__setattr__(self, 'bend_direction', direction)


@dataclass(frozen=True)
class AnatomyConnection:
    """Declared continuity; ordered boundaries use each region mesh-part indices.

    Empty boundaries mean unauthored, never a successful topology audit.
    """
    name: str
    regions: tuple[str, str]
    continuity: str
    boundaries: tuple[tuple[int, ...], tuple[int, ...]] = ((), ())

    def __post_init__(self):
        _name(self.name)
        regions = tuple(self.regions)
        if len(regions) != 2 or regions[0] == regions[1]:
            raise ValueError('connection needs two distinct regions')
        for value in regions:
            _name(value)
        if self.continuity not in ('connected', 'articulated', 'separate'):
            raise ValueError('unknown continuity expectation')
        boundaries = tuple(_indices(b) for b in self.boundaries)
        if len(boundaries) != 2:
            raise ValueError('connection needs two boundary declarations')
        object.__setattr__(self, 'regions', regions)
        object.__setattr__(self, 'boundaries', boundaries)


@dataclass(frozen=True)
class ResolvedAnatomy:
    recipe_id: str
    recipe_version: str
    parameters: tuple[tuple[str, Scalar], ...]
    landmarks: tuple[Landmark, ...] = ()
    regions: tuple[AnatomyRegion, ...] = ()
    chains: tuple[JointChain, ...] = ()
    connections: tuple[AnatomyConnection, ...] = ()
    symmetry: tuple[tuple[str, str], ...] = ()

    def __post_init__(self):
        _name(self.recipe_id)
        _name(self.recipe_version)
        parameters = []
        for key, value in self.parameters:
            _name(key)
            if type(value) not in (str, int, float, bool):
                raise TypeError('parameters must be immutable scalar values')
            if isinstance(value, float) and not isfinite(value):
                raise ValueError('parameters must be finite')
            parameters.append((key, value))
        if len({k for k, _ in parameters}) != len(parameters):
            raise ValueError('duplicate parameter')
        object.__setattr__(self, 'parameters', tuple(sorted(parameters)))
        names = {}
        for field, kind in (('landmarks', Landmark), ('regions', AnatomyRegion),
                            ('chains', JointChain), ('connections', AnatomyConnection)):
            values = tuple(getattr(self, field))
            if any(not isinstance(v, kind) for v in values):
                raise TypeError('invalid anatomy record in ' + field)
            names[field] = {v.name for v in values}
            if len(names[field]) != len(values):
                raise ValueError('duplicate anatomy name in ' + field)
            object.__setattr__(self, field, values)
        parents = {}
        for chain in self.chains:
            if not set(chain.landmarks) <= names['landmarks']:
                raise ValueError('unknown chain landmark')
            for index, bone in enumerate(chain.bones):
                if bone in parents:
                    raise ValueError('bone belongs to multiple chains')
                parents[bone] = chain.bones[index - 1] if index else chain.parent_bone
        for bone in parents:
            visited = set()
            current = bone
            while current is not None:
                if current not in parents:
                    raise ValueError('unknown parent bone')
                if current in visited:
                    raise ValueError('cyclic bone hierarchy')
                visited.add(current)
                current = parents[current]
        for connection in self.connections:
            if not set(connection.regions) <= names['regions']:
                raise ValueError('unknown connection region')
        symmetry = tuple(tuple(pair) for pair in self.symmetry)
        used = set()
        for pair in symmetry:
            if len(pair) != 2 or pair[0] == pair[1] or not set(pair) <= names['regions']:
                raise ValueError('symmetry must pair distinct known regions')
            if used.intersection(pair):
                raise ValueError('region belongs to multiple symmetry pairs')
            used.update(pair)
        object.__setattr__(self, 'symmetry', symmetry)

    def validate_mesh(self, mesh):
        """Validate index bounds, not manifoldness or visual quality."""
        parts = {part.name: part for part in mesh.parts}
        regions = {region.name: region for region in self.regions}
        for region in self.regions:
            if region.mesh_part not in parts:
                raise ValueError('unknown region mesh part')
            size = len(parts[region.mesh_part].vertices)
            if any(i >= size for i in region.vertex_indices):
                raise ValueError('region index outside mesh part')
        for connection in self.connections:
            for name, boundary in zip(connection.regions, connection.boundaries):
                size = len(parts[regions[name].mesh_part].vertices)
                if any(i >= size for i in boundary):
                    raise ValueError('boundary index outside mesh part')


class AnatomyRecipe(Protocol):
    """Structural interface, with provider-owned validation and construction."""
    recipe_id: str
    recipe_version: str

    def resolve(self, values: Mapping[str, Scalar]) -> ResolvedAnatomy:
        ...
