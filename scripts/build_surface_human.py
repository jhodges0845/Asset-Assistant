# SPDX-License-Identifier: GPL-3.0-or-later
"""Reproducible, background-only mathematical Human builder for Blender 5.2.1."""
import argparse
import importlib.util
import sys
from pathlib import Path
import bpy
sys.path.insert(0,str(Path(__file__).resolve().parent))
from surface_source_snapshot import capture_source
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from object_core.geometry.surface_human_builder import HumanSurfaceBuilder,load_surface_preset


def main():
    if not bpy.app.background:raise RuntimeError('Run in a separate Blender --background process to preserve artist work')
    p=argparse.ArgumentParser();p.add_argument('--preset',default=str(ROOT/'presets/human/maxine.json'));p.add_argument('--output',default=str(ROOT/'outputs/maxine-surface-v1'));p.add_argument('--no-render',action='store_true');p.add_argument('--overwrite',action='store_true')
    args=p.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
    out=Path(args.output).resolve()
    if out.exists() and any(out.iterdir()) and not args.overwrite:raise FileExistsError('Output is not empty; choose a new output folder or explicitly pass --overwrite')
    capture_source(ROOT,out,args.preset)
    mesh,report=HumanSurfaceBuilder().build(load_surface_preset(args.preset))
    # Load only the host presentation module; importing the add-on package itself
    # would register unrelated UI modules during headless study generation.
    spec=importlib.util.spec_from_file_location('surface_human_study',ROOT/'blender_adapter/surface_human_study.py');adapter=importlib.util.module_from_spec(spec);spec.loader.exec_module(adapter)
    result=adapter.save_surface_study(mesh,report,out,not args.no_render)
    print('SURFACE_HUMAN_RESULT',result,report['geometry_sha256'],flush=True)

if __name__=='__main__':main()
