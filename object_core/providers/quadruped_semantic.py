# SPDX-License-Identifier: GPL-3.0-or-later
"""Quadruped semantic shaping using authored recipe regions."""
from ..models import MeshPart, ObjectMesh
from .semantic_geometry import _number, _transform


PROFILES = {
    ('chest', 'broad'): (0.25, 0.08, 0.12),
    ('waist', 'tucked'): (-0.18, 0.0, -0.12),
    ('head', 'broad'): (0.20, 0.08, 0.10),
    ('tail', 'long'): (0.0, 0.30, 0.0),
}


def apply_quadruped_semantic_operations(mesh, anatomy, operations):
    anatomy.validate_mesh(mesh)
    part = mesh.parts[0]
    vertices = list(part.vertices)
    regions = {region.name: region.vertex_indices for region in anatomy.regions}
    for operation in operations:
        if operation.operation not in ('shape', 'scale'):
            raise ValueError('Quadruped semantic geometry cannot apply ' + operation.operation)
        if operation.target not in regions:
            raise ValueError('Unsupported Quadruped semantic target ' + operation.target)
        indices = regions[operation.target]
        arguments = operation.argument_values()
        vertices = _transform(vertices, indices, arguments)
        profile = arguments.get('profile')
        if operation.operation == 'shape' and profile:
            amount = _number(arguments, 'amount', 0.65)
            if not 0.0 <= amount <= 1.5:
                raise ValueError('profile amount must be between 0.0 and 1.5')
            if operation.target == 'muzzle' and profile == 'long':
                points = {p.name: p.position for p in anatomy.landmarks}
                extension = (points['muzzle.tip'][1] - points['head.center'][1]) * 0.30 * amount
                vertices = _transform(vertices, indices, {'offset_y': extension})
                continue
            changes = PROFILES.get((operation.target, profile))
            if operation.target.startswith('leg.') and profile == 'sturdy':
                changes = (0.20, 0.20, 0.0)
            if changes is None:
                raise ValueError('Unsupported Quadruped semantic profile ' + str(profile))
            vertices = _transform(vertices, indices, dict(zip(('x', 'y', 'z'),
                                  (1.0 + amount * change for change in changes))))
    return ObjectMesh((MeshPart(part.name, tuple(vertices), part.faces, part.uvs),))
