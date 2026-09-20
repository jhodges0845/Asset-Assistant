# SPDX-License-Identifier: GPL-3.0-or-later
"""Create the mathematical Human through the ordinary plugin asset lifecycle."""
import json
from .adapter import create_character
from .surface_human_study import validate_control_surface


def create_surface_asset(provider, values, scene):
    mesh,report=provider.build_values(values)
    report['base_triangle_self_intersections']=validate_control_surface(mesh.parts[0])
    report['not_checked']=[v for v in report['not_checked'] if v!='self_intersections']+['subdivision_self_intersections']
    root=create_character(mesh,name=provider.label,scene=scene)
    root['surface_generation_report']=json.dumps(report,sort_keys=True)
    root['quality_status']=report['quality_status']
    for obj in root.children:
        if obj.type!='MESH':continue
        for face in obj.data.polygons:face.use_smooth=True
        modifier=obj.modifiers.new('Surface display subdivision','SUBSURF')
        modifier.levels=2;modifier.render_levels=2
    return root
