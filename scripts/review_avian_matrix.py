# SPDX-License-Identifier: GPL-3.0-or-later
"""Save the complete canonical Avian action/shape/strength review matrix."""
import argparse
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
from scripts.avian_review_samples import AVIAN_REVIEW_SAMPLES,review_values
from scripts.review_avian_gait import review_cycle

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args(sys.argv[sys.argv.index('--')+1:])
    rows=[]
    passed=True
    for name in ('default',)+tuple(AVIAN_REVIEW_SAMPLES):
        for clip in ('idle','walk','flight'):
            for strength in (.1,1.,2.):
                report=review_cycle(review_values(name),clip,127,strength)
                checks=[report['crossing_samples']==0,report['loop_closure_error_cm']<1e-4]
                if clip=='walk':
                    checks.extend(foot['minimum_z_cm']>.018 and
                        foot['scheduled_stance']['maximum_reference_vertex_displacement_cm']<.002
                        for foot in report['summary'].values())
                elif clip=='idle':
                    checks.extend(foot['penetrating_samples']==0 and foot['maximum_fixed_sole_motion_cm']<1e-4
                                  for foot in report['summary'].values())
                row={key:report[key] for key in ('clip','strength','parameters','recipe_version',
                    'crossing_samples','maximum_crossing_pairs','loop_closure_error_cm','summary')}
                row.update(sample=name,passed=all(checks))
                rows.append(row)
                passed=passed and row['passed']
                print(name,clip,strength,row['passed'],flush=True)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(dict(schema_version=1,intervals=127,passed=passed,rows=rows),indent=2))
    if not passed: raise SystemExit(1)

if __name__=='__main__': main()
