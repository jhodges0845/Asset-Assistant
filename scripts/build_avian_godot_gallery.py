# SPDX-License-Identifier: GPL-3.0-or-later
"""Build a local gallery from the edited Avian Godot phase fixtures."""
import argparse
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    args = parser.parse_args()
    rows = []
    for shape in ('default', 'contrasting'):
        for amount in ('06', '15'):
            fixture = args.root / f'avian-skin-{shape}-{amount}'
            for clip in ('walk', 'idle', 'flight'):
                directory = fixture / f'render-{clip}-stills'
                report = json.loads((directory / 'render-report.json').read_text())
                if report.get('capture_mode') != 'phase-stills' or report['frames'] != 4:
                    raise ValueError(f'Expected four phase stills: {directory}')
                paths = [directory / f'frame-{i:03d}.png' for i in range(4)]
                if not all(path.is_file() for path in paths):
                    raise ValueError(f'Missing phase images: {directory}')
                rows.append(dict(label=f'{shape} / chest {0.6 if amount == "06" else 1.5} / {clip}',
                    images=[path.relative_to(args.root).as_posix() for path in paths],
                    report=(directory/'render-report.json').relative_to(args.root).as_posix()))
    page = '''<!doctype html><meta charset="utf-8"><title>Edited Avian destination review</title>
<style>body{background:#20262c;color:#edf1f4;font:17px system-ui;margin:30px auto;max-width:1600px;padding:0 24px}img{width:100%}select,input{margin:12px;font:inherit}a{color:#9ed9ff}</style>
<h1>Edited Avian in Godot</h1><p>Four phase stills per clip, with front, three-quarter, side and back views.
Flight display copies are elevated for airborne inspection; this is not exported root motion.
These sheets support visual review; they do not establish continuous-motion or final artistic acceptance.</p>
<label>Fixture <select id="fixture"></select></label><label>Phase <input id="phase" type="range" min="0" max="3" value="0" step="1"><span id="phaseLabel"></span></label>
<p><a id="report">Render metadata</a></p><img id="sheet" alt="Four-view bird phase sheet">
<script>const rows=DATA;
const fixture=document.getElementById('fixture'), phase=document.getElementById('phase');
rows.forEach((row,i)=>{const option=document.createElement('option');option.value=i;option.textContent=row.label;fixture.append(option);});
function update(){const row=rows[Number(fixture.value)];const index=Number(phase.value);document.getElementById('sheet').src=row.images[index];document.getElementById('report').href=row.report;document.getElementById('phaseLabel').textContent=(index*25)+'%';}
fixture.addEventListener('change',update);phase.addEventListener('input',update);update();</script>'''
    output = args.root / 'avian-destination-review.html'
    output.write_text(page.replace('DATA', json.dumps(rows)), encoding='utf-8')
    print(f'Validated {len(rows)} sets / {len(rows)*4} images: {output}')


if __name__ == '__main__':
    main()
