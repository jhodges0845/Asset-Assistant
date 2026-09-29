# SPDX-License-Identifier: GPL-3.0-or-later
"""Quadruped rig and skin-weight generation."""

from collections import deque
from math import sqrt

from ..models import Bone, BoneWeight, Skeleton, SkinWeights
from .quadruped_anatomy import CanineRecipe


def generate_quadruped_skeleton(dimensions):
    """Build a deterministic quadruped skeleton from validated dimensions."""
    return _build_quadruped_skeleton(CanineRecipe().resolve(dimensions))


def _build_quadruped_skeleton(anatomy):
    """Construct all bones directly from resolved chains and landmarks."""
    landmarks = {landmark.name: landmark.position for landmark in anatomy.landmarks}
    bones = []
    for chain in anatomy.chains:
        parent = chain.parent_bone
        for index, name in enumerate(chain.bones):
            bones.append(Bone(name, landmarks[chain.landmarks[index]],
                              landmarks[chain.landmarks[index + 1]], parent))
            parent = name
    return Skeleton(tuple(bones))


def _distance_to_segment(point, start, end):
    axis = tuple(end[i] - start[i] for i in range(3))
    offset = tuple(point[i] - start[i] for i in range(3))
    length_sq = sum(value * value for value in axis)
    amount = sum(offset[i] * axis[i] for i in range(3)) / length_sq
    amount = max(0.0, min(1.0, amount))
    closest = tuple(start[i] + axis[i] * amount for i in range(3))
    return sqrt(sum((point[i] - closest[i]) ** 2 for i in range(3)))


def _candidate_bones(vertex, bones):
    """Prevent a vertex from being influenced by the opposite-side limb."""
    side = "left" if vertex[0] <= 0 else "right"
    return tuple(
        bone for bone in bones
        if not (bone.name.endswith(".left") or bone.name.endswith(".right"))
        or bone.name.endswith("." + side)
    )


def _weights_for_vertex(vertex, candidates, max_influences=4):
    ranked = sorted(
        ((_distance_to_segment(vertex, bone.head, bone.tail), bone) for bone in candidates),
        key=lambda item: (item[0], item[1].name),
    )
    nearest = ranked[0][1]
    local_names = {nearest.name}
    if nearest.parent:
        local_names.add(nearest.parent)
    local_names.update(bone.name for bone in candidates if bone.parent == nearest.name)
    local = [(distance, bone) for distance, bone in ranked if bone.name in local_names][:max_influences]
    raw = [(bone.name, 1.0 / ((distance + 1e-3) ** 2)) for distance, bone in local]
    total = sum(value for _name, value in raw)
    normalized = [(name, value / total) for name, value in raw]
    correction = 1.0 - sum(value for _name, value in normalized)
    normalized[0] = (normalized[0][0], normalized[0][1] + correction)
    return tuple(BoneWeight(name, value) for name, value in normalized if value > 0)


def _anatomy_bone_candidates(anatomy, bones):
    """Bind limbs to their chains and ears to the head, including after edits.

    Positions can move through Modify, so neither side nor front/hind ownership
    is inferred from coordinates. The bridge and its short topology-owned collar
    blend to the chain parent separately; distal vertices stay within their chain.
    """
    chains = {chain.name: chain for chain in anatomy.chains}
    boundaries = {}
    for connection in anatomy.connections:
        if connection.continuity == "connected":
            for region, boundary in zip(connection.regions, connection.boundaries):
                boundaries.setdefault(region, set()).update(boundary)
    candidates = {}
    for region in anatomy.regions:
        if region.name.startswith("ear."):
            head = tuple(bone for bone in bones if bone.name == "head")
            if not head:
                raise ValueError("Quadruped skeleton is missing its head bone")
            for index in region.vertex_indices:
                candidates[(region.mesh_part, index)] = head
            continue
        if not region.name.startswith("leg."):
            continue
        chain = chains[region.name]
        local = tuple(bone for bone in bones if bone.name in chain.bones)
        if len(local) != len(chain.bones):
            raise ValueError("Quadruped skeleton is missing an authored limb bone")
        attachment = tuple(bone for bone in bones
                           if bone.name in chain.bones or bone.name == chain.parent_bone)
        for index in region.vertex_indices:
            key = (region.mesh_part, index)
            if key in candidates:
                raise ValueError("Quadruped limb ownership must be disjoint")
            candidates[key] = attachment if index in boundaries.get(region.name, ()) else local
    return candidates


def _mesh_graphs(mesh):
    graphs = {}
    for part in mesh.parts:
        graph = [set() for _ in part.vertices]
        for face in part.faces:
            for a, b in zip(face, face[1:] + face[:1]):
                graph[a].add(b)
                graph[b].add(a)
        graphs[part.name] = graph
    return graphs


def _attachment_weights(mesh, anatomy, max_influences, graphs=None):
    """Blend across the declared bridge, never through unrelated body surfaces.

    Graph distance uses topology rather than edited positions. The body loop
    stays on the parent; the limb loop retains a quarter parent influence.
    """
    regions = {region.name: region for region in anatomy.regions}
    chains = {chain.name: chain for chain in anatomy.chains}
    graphs = _mesh_graphs(mesh) if graphs is None else graphs
    result = {}
    for connection in anatomy.connections:
        name = connection.regions[1]
        if not name.startswith('leg.') or connection.continuity != 'connected':
            continue
        region, chain = regions[name], chains[name]
        graph = graphs[region.mesh_part]
        root, limb = map(set, connection.boundaries)
        if not root or not limb or root & limb:
            raise ValueError('Canine attachment requires two disjoint boundary loops')
        owned = set(region.vertex_indices)
        body = set(regions[connection.regions[0]].vertex_indices)
        bridge, pending = set(limb), deque(sorted(limb))
        while pending:
            vertex = pending.popleft()
            for neighbor in sorted(graph[vertex]):
                if neighbor in bridge or neighbor in owned:
                    continue
                if neighbor in body and neighbor not in root:
                    raise ValueError('Canine attachment escapes its body boundary')
                bridge.add(neighbor)
                if neighbor not in root:
                    pending.append(neighbor)
        if not root <= bridge:
            raise ValueError('Canine attachment does not reach its body boundary')

        def distances(seeds):
            distance = {i: 0 for i in seeds}
            queue = deque(sorted(seeds))
            while queue:
                vertex = queue.popleft()
                for neighbor in sorted(graph[vertex] & bridge):
                    if neighbor not in distance:
                        distance[neighbor] = distance[vertex] + 1
                        queue.append(neighbor)
            return distance

        body_distance, limb_distance = distances(root), distances(limb)
        for i in sorted(bridge):
            t = body_distance[i] / (body_distance[i] + limb_distance[i])
            amount = .75 * t*t*(3 - 2*t)
            raw = [(chain.parent_bone, 1 - amount), (chain.bones[0], amount)]
            raw = sorted(((name, weight) for name, weight in raw if weight > 0),
                         key=lambda item: (-item[1], item[0]))[:max_influences]
            total = sum(weight for _, weight in raw)
            key = (region.mesh_part, i)
            if key in result:
                raise ValueError('Canine attachment bridges must be disjoint')
            result[key] = tuple(BoneWeight(name, weight / total) for name, weight in raw)
    return result


def _attachment_collar_weights(mesh, anatomy, bones, max_influences, graphs):
    """Fade the boundary's parent weight over one refined cage interval.

    Two subdivision passes produce four edges per cage interval. The three
    interior rows blend into the existing chain weights at the fourth edge.
    Restrict traversal to authored limb ownership so no nearby body or other
    limb can acquire influence, including after large semantic translations.
    """
    regions = {region.name: region for region in anatomy.regions}
    chains = {chain.name: chain for chain in anatomy.chains}
    parts = {part.name: part for part in mesh.parts}
    result = {}
    for connection in anatomy.connections:
        name = connection.regions[1]
        if not name.startswith('leg.') or connection.continuity != 'connected':
            continue
        region, chain = regions[name], chains[name]
        graph = graphs[region.mesh_part]
        owned = set(region.vertex_indices)
        depths = dict.fromkeys(connection.boundaries[1], 0)
        if not set(depths) <= owned:
            raise ValueError('Canine attachment loop must belong to its limb')
        queue = deque(sorted(depths))
        while queue:
            i = queue.popleft()
            if depths[i] == 3:
                continue
            for j in sorted(graph[i] & owned):
                if j not in depths:
                    depths[j] = depths[i] + 1
                    queue.append(j)
        local = tuple(bone for bone in bones if bone.name in chain.bones)
        for i, depth in sorted(depths.items()):
            if depth == 0:
                continue  # The declared bridge owns the boundary itself.
            t = depth / 4
            blend = t*t*(3 - 2*t)
            parent = .25 * (1 - blend)
            raw = {w.bone_name: w.weight * blend for w in _weights_for_vertex(
                parts[region.mesh_part].vertices[i], local, max_influences)}
            raw[chain.bones[0]] = raw.get(chain.bones[0], 0) + 1 - blend
            raw = {name: weight * (1 - parent) for name, weight in raw.items()}
            raw[chain.parent_bone] = parent
            ranked = sorted(raw.items(), key=lambda item: (-item[1], item[0]))[:max_influences]
            total = sum(weight for _, weight in ranked)
            key = (region.mesh_part, i)
            if key in result:
                raise ValueError('Canine attachment collars must be disjoint')
            result[key] = tuple(BoneWeight(name, weight / total) for name, weight in ranked)
    return result


def generate_quadruped_skin_weights(mesh, skeleton, *, max_influences=4, anatomy=None):
    """Return normalized local weights for a connected quadruped surface."""
    if type(max_influences) is not int or max_influences < 1:
        raise ValueError("max_influences must be a positive integer")
    deform_bones = tuple(bone for bone in skeleton.bones if bone.name != "root")
    if not deform_bones:
        raise ValueError("Quadruped skeleton must contain deform bones")
    candidates = {}
    attachment = {}
    axial = tuple(bone for bone in deform_bones if not bone.name.endswith((".left", ".right")))
    if anatomy is not None:
        anatomy.validate_mesh(mesh)
        candidates = _anatomy_bone_candidates(anatomy, deform_bones)
        graphs = _mesh_graphs(mesh)
        attachment = _attachment_weights(mesh, anatomy, max_influences, graphs)
        collar = _attachment_collar_weights(mesh, anatomy, deform_bones, max_influences, graphs)
        if attachment.keys() & collar.keys():
            raise ValueError("Canine attachment collar overlaps the declared bridge")
        attachment.update(collar)

    def weights(part, index, vertex):
        if (part.name, index) in attachment:
            return attachment[(part.name, index)]
        local = candidates.get((part.name, index))
        if local is None:
            local = axial if anatomy is not None else _candidate_bones(vertex, deform_bones)
        return _weights_for_vertex(vertex, local, max_influences)

    return tuple(
        SkinWeights(part.name, tuple(weights(part, index, vertex)
                                    for index, vertex in enumerate(part.vertices)))
        for part in mesh.parts
    )
