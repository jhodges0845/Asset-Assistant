# SPDX-License-Identifier: GPL-3.0-or-later
"""Validated Human geometry construction, independent of Blender and rigging.

HumanProvider uses this builder for its neutral surface and authored arm indices.
Standalone development scripts also use its strict presets and geometry reports.
"""
import hashlib
import json
from collections import Counter, defaultdict
from dataclasses import asdict
from .surface_human import VERSION, SurfaceHumanSpec, generate_surface_human


def load_surface_preset(path):
    with open(path, encoding="utf-8-sig") as f:
        value = json.load(f)
    if not isinstance(value, dict) or set(value) != {
        "schema_version",
        "generator",
        "parameters",
    }:
        raise ValueError(
            "preset must contain only schema_version, generator, parameters"
        )
    if (
        type(value["schema_version"]) is not int
        or value["schema_version"] != 1
        or value["generator"] != VERSION
    ):
        raise ValueError("unsupported preset or generator version")
    if not isinstance(value["parameters"], dict):
        raise ValueError("parameters must be an object")
    return SurfaceHumanSpec(**value["parameters"])


def audit_surface(mesh):
    """Check connectivity, closed edges, winding and nondegenerate faces.

    Self-intersection and visual/deformation quality are separate checks.
    """
    part = mesh.parts[0]
    edges = Counter()
    directions = Counter()
    adj = defaultdict(set)
    degenerate = 0
    for face in part.faces:
        for j, a in enumerate(face):
            c = face[(j + 1) % len(face)]
            edges[tuple(sorted((a, c)))] += 1
            directions[(a, c)] += 1
            adj[a].add(c)
            adj[c].add(a)
        p = part.vertices[face[0]]
        area = 0.0
        for j in range(1, len(face) - 1):
            u = tuple(part.vertices[face[j]][d] - p[d] for d in range(3))
            v = tuple(part.vertices[face[j + 1]][d] - p[d] for d in range(3))
            cross = (
                u[1] * v[2] - u[2] * v[1],
                u[2] * v[0] - u[0] * v[2],
                u[0] * v[1] - u[1] * v[0],
            )
            area += sum(x * x for x in cross) ** 0.5
        degenerate += area < 1e-10
    unseen = set(range(len(part.vertices)))
    components = 0
    while unseen:
        components += 1
        stack = [unseen.pop()]
        while stack:
            for v in adj[stack.pop()]:
                if v in unseen:
                    unseen.remove(v)
                    stack.append(v)
    boundary = sum(v == 1 for v in edges.values())
    nonmanifold = sum(v > 2 for v in edges.values())
    winding = sum(directions[a, b] != 1 or directions[b, a] != 1 for a, b in edges)
    return {
        "vertices": len(part.vertices),
        "faces": len(part.faces),
        "components": components,
        "boundary_edges": boundary,
        "nonmanifold_edges": nonmanifold,
        "inconsistent_edges": winding,
        "degenerate_faces": degenerate,
        "euler_characteristic": len(part.vertices) - len(edges) + len(part.faces),
        "bounds_cm": mesh.bounds_cm,
        "passed": components == 1
        and not (boundary or nonmanifold or winding or degenerate),
        "not_checked": [
            "self_intersections",
            "animation_deformation",
            "reference_likeness",
            "production_UVs",
        ],
    }


class HumanSurfaceBuilder:
    """Build and audit the shared Human surface; not a registered asset provider."""

    def build_values(self, values):
        return self.build(SurfaceHumanSpec(**values))

    def mesh(self, values):
        return self.build(SurfaceHumanSpec(**values))[0]

    def build(self, spec, *, include_arm_indices=False):
        """Generate and audit once; optionally return arm ownership for skinning."""
        generated = generate_surface_human(
            spec, include_arm_indices=include_arm_indices
        )
        mesh, arms = generated if include_arm_indices else (generated, ())
        report = audit_surface(mesh)
        if not report["passed"]:
            raise ValueError("surface validation failed: " + json.dumps(report))
        report.update(
            generator=VERSION,
            parameters=asdict(spec),
            geometry_sha256=hashlib.sha256(
                json.dumps(
                    {"vertices": mesh.parts[0].vertices, "faces": mesh.parts[0].faces},
                    separators=(",", ":"),
                ).encode()
            ).hexdigest(),
            quality_status="experimental_anatomical_study",
        )
        return (mesh, report, arms) if include_arm_indices else (mesh, report)
