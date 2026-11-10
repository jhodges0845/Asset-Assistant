# SPDX-License-Identifier: GPL-3.0-or-later
"""Undoable, conservative material preparation for generated assets."""

from .targets import asset_objects


_GENERATED_TEXTURE_MARKER = 'asset_assistant_generated_texture'
_GENERATED_MATERIAL_MARKER = 'asset_assistant_generated_material'


def _principled_material(name, base_color, metallic, roughness, base_color_texture=None):
    import bpy

    material = bpy.data.materials.new(name)
    material.use_nodes = True
    shader = material.node_tree.nodes.get('Principled BSDF')
    shader.inputs['Base Color'].default_value = base_color
    shader.inputs['Metallic'].default_value = metallic
    shader.inputs['Roughness'].default_value = roughness
    if base_color_texture is not None:
        image = bpy.data.images.new(
            base_color_texture.name,
            width=base_color_texture.width,
            height=base_color_texture.height,
            alpha=True,
        )
        image.pixels = base_color_texture.pixels
        # Asset Assistant owns generated image data, so keep it self-contained in
        # the .blend immediately. Artist-supplied external textures are never
        # packed here and remain under artist control. Packing can make Blender
        # report the datablock as FILE-backed, so record ownership explicitly;
        # exporters use this marker rather than mutating Image.source.
        image.pack()
        image[_GENERATED_TEXTURE_MARKER] = True
        texture = material.node_tree.nodes.new('ShaderNodeTexImage')
        texture.name = base_color_texture.name
        texture.label = base_color_texture.name
        texture.image = image
        material.node_tree.links.new(texture.outputs['Color'], shader.inputs['Base Color'])
    return material


def apply_generated_materials(root, specs):
    """Translate portable provider material specs into editable Blender materials."""
    by_part = {obj.get('part_name'): obj for obj in asset_objects(root) if obj.type == 'MESH'}
    created = []
    assigned = set()
    for spec in specs:
        if any(part_name not in by_part for part_name in spec.part_names):
            raise ValueError(spec.name + ': material references a missing mesh part')
        overlap = assigned.intersection(spec.part_names)
        if overlap:
            raise ValueError(spec.name + ': mesh part already has a generated material')
        material = _principled_material(
            spec.name,
            spec.base_color,
            spec.metallic,
            spec.roughness,
            spec.base_color_texture,
        )
        material[_GENERATED_MATERIAL_MARKER] = True
        created.append(material)
        for part_name in spec.part_names:
            obj = by_part[part_name]
            obj.data.materials.append(material)
            for face in obj.data.polygons:
                face.material_index = len(obj.data.materials) - 1
            assigned.add(part_name)
    return tuple(created)


def _provider_materials(root):
    from .core import get_provider

    provider = get_provider(root.get('object_type', 'humanoid'))
    if not getattr(provider, 'supports_materials', False):
        return ()
    try:
        values = {field.key: root[field.key] for field in provider.parameters}
    except KeyError:
        return ()
    return provider.materials(values)


def prepare_materials(root):
    """Fill missing face materials while preserving artist assignments."""
    import bpy

    meshes = [obj for obj in asset_objects(root) if obj.type == 'MESH']
    missing_by_object = {}
    for obj in meshes:
        missing = [face.index for face in obj.data.polygons
                   if face.material_index >= len(obj.material_slots)
                   or obj.material_slots[face.material_index].material is None]
        if missing:
            missing_by_object[obj] = missing
    if not missing_by_object:
        return None

    specs = _provider_materials(root)
    if specs and all(len(indices) == len(obj.data.polygons)
                     for obj, indices in missing_by_object.items()):
        created = apply_generated_materials(root, specs)
        return created[0] if len(created) == 1 else created

    default = None
    for obj, missing in missing_by_object.items():
        if default is None:
            default = _principled_material('Generator Material', (0.55, 0.55, 0.55, 1), 0.0, 0.65)
        if obj.data.users > 1:
            obj.data = obj.data.copy()
        index = len(obj.data.materials)
        obj.data.materials.append(default)
        for face_index in missing:
            obj.data.polygons[face_index].material_index = index
    return default


def material_issues(objects, *, allow_vertex_colors=False):
    """Reject shader graphs that these file exporters cannot reliably translate."""
    from .core import ValidationIssue

    seen = set()
    issues = []
    for obj in objects:
        for slot in obj.material_slots:
            material = slot.material
            if material is None or (material.as_pointer() in seen and not allow_vertex_colors) or not material.use_nodes:
                continue
            seen.add(material.as_pointer())
            outputs = [node for node in material.node_tree.nodes
                       if node.type == 'OUTPUT_MATERIAL' and node.is_active_output]
            surface = outputs[0].inputs['Surface'] if outputs else None
            shader = surface.links[0].from_node if surface and surface.is_linked else None
            supported = shader is not None and shader.type == 'BSDF_PRINCIPLED'
            if supported:
                for socket in shader.inputs:
                    for link in socket.links:
                        source = link.from_node
                        if (allow_vertex_colors and source.type == 'VERTEX_COLOR'
                                and socket.name == 'Base Color' and link.from_socket.name == 'Color'
                                and ((source.layer_name and source.layer_name in obj.data.color_attributes)
                                     or (not source.layer_name and
                                         0 <= obj.data.color_attributes.render_color_index < len(obj.data.color_attributes)))):
                            continue
                        if source.type == 'NORMAL_MAP':
                            source = source.inputs['Color'].links[0].from_node if source.inputs['Color'].is_linked else None
                        if source is None or source.type != 'TEX_IMAGE':
                            supported = False
                        elif source.inputs['Vector'].is_linked:
                            supported = False
            if not supported or (outputs and outputs[0].inputs['Displacement'].is_linked):
                issues.append(ValidationIssue('material_shader', 'ERROR', material.name +
                    ': use a Principled BSDF with plain values or direct image textures; bake procedural shaders and mapping before export.'))
    return tuple(issues)
