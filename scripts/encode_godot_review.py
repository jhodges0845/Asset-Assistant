# SPDX-License-Identifier: GPL-3.0-or-later
"""Encode a complete Godot review sequence with Blender's bundled H.264 encoder."""
import argparse
import json
from pathlib import Path
import struct
import sys
import bpy


def encode(directory):
    directory = directory.resolve()
    report = json.loads((directory/'render-report.json').read_text())
    if report.get('capture_mode') != 'three-cycle-sequence' or report.get('cycles') != 3:
        raise ValueError('Expected a complete three-cycle capture')
    count, fps = report['frames'], report['fps']
    if not isinstance(count,int) or count <= 0 or not isinstance(fps,int) or fps <= 0:
        raise ValueError('Invalid frame count or rate')
    frames = [directory/f'frame-{i:03d}.png' for i in range(count)]
    if not all(frame.is_file() for frame in frames):
        raise ValueError('Missing captured frame')
    width,height = struct.unpack('>II',frames[0].read_bytes()[16:24])
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    editor = scene.sequence_editor_create()
    strip = editor.strips.new_image('Godot review',str(frames[0]),channel=1,frame_start=1)
    for frame in frames[1:]:
        strip.elements.append(frame.name)
    scene.frame_start,scene.frame_end = 1,count
    scene.render.fps,scene.render.fps_base = fps,1
    scene.render.resolution_x,scene.render.resolution_y = width,height
    scene.render.resolution_percentage = 100
    scene.render.use_sequencer = True
    scene.view_settings.view_transform = 'Standard'
    scene.view_settings.look = 'None'
    scene.view_settings.exposure = 0
    scene.view_settings.gamma = 1
    if hasattr(scene.render.image_settings,'media_type'):
        scene.render.image_settings.media_type = 'VIDEO'
    scene.render.image_settings.file_format = 'FFMPEG'
    scene.render.ffmpeg.format = 'MPEG4'
    scene.render.ffmpeg.codec = 'H264'
    scene.render.ffmpeg.constant_rate_factor = 'HIGH'
    output = directory/'review.mp4'
    scene.render.filepath = str(output)
    bpy.ops.render.render(animation=True)
    movie = bpy.data.movieclips.load(str(output))
    if movie.frame_duration != count or tuple(movie.size) != (width,height):
        raise RuntimeError('Encoded video dimensions or frame count differ from capture')
    manifest = dict(frames=count,fps=fps,duration_seconds=count/fps,width=width,height=height,
                    source_report='render-report.json',blender=bpy.app.version_string)
    (directory/'video-report.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    print('VIDEO_VERIFIED',output,flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directories',nargs='+',type=Path)
    args = parser.parse_args(sys.argv[sys.argv.index('--')+1:])
    for directory in args.directories:
        encode(directory)


if __name__ == '__main__':
    main()
