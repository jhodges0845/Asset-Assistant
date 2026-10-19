# SPDX-License-Identifier: GPL-3.0-or-later
"""Save the complete canonical Avian action/shape/strength review matrix."""
import argparse
import json
import hashlib
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
from scripts.avian_review_samples import AVIAN_REVIEW_SAMPLES,review_values
from scripts.review_avian_gait import review_cycle
from object_core.modification import SemanticOperation
import subprocess

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--samples',nargs='+',choices=('default',)+tuple(AVIAN_REVIEW_SAMPLES),
                        default=('default',)+tuple(AVIAN_REVIEW_SAMPLES))
    parser.add_argument('--chest-amounts',nargs='+',type=float)
    args=parser.parse_args(sys.argv[sys.argv.index('--')+1:])
    rows=[]
    passed=True
    for name in args.samples:
        for amount in (args.chest_amounts if args.chest_amounts is not None else (None,)):
            operations=() if amount is None else (SemanticOperation('shape','chest',
                (('profile','powerful'),('amount',amount))),)
            for clip in ('idle','walk','flight'):
                for strength in (.1,1.,2.):
                    report=review_cycle(review_values(name),clip,127,strength,semantic_operations=operations)
                    checks=[not report['neutral_surface_crossings'],report['crossing_samples']==0,report['loop_closure_error_cm']<1e-4]
                    if clip=='walk':
                        checks.extend(foot['minimum_z_cm']>.018 and
                            foot['scheduled_stance']['maximum_reference_vertex_displacement_cm']<.002
                            for foot in report['summary'].values())
                    elif clip=='idle':
                        checks.extend(foot['penetrating_samples']==0 and foot['maximum_fixed_sole_motion_cm']<1e-4
                                      for foot in report['summary'].values())
                    row={key:report[key] for key in ('clip','strength','parameters','recipe_version',
                        'neutral_surface_crossings','crossing_samples','maximum_crossing_pairs','loop_closure_error_cm','summary')}
                    row.update(sample=name,chest_amount=amount,semantic_operations=report['semantic_operations'],passed=all(checks))
                    rows.append(row)
                    passed=passed and row['passed']
                    print(name,amount,clip,strength,row['passed'],flush=True)
    sources = ('scripts/review_avian_gait.py','scripts/review_avian_matrix.py',
               'object_core/providers/avian_semantic.py')
    hashes = {name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in sources}
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(dict(schema_version=2,intervals=127,passed=passed,rows=rows,source_sha256=hashes,
        scope="Sampled crossings, contact and closure; excludes containment, coplanar contact, between-sample extremes and final artistic acceptance.",
        commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        working_tree_changes=subprocess.check_output(['git','status','--porcelain'],cwd=ROOT,text=True).splitlines()),indent=2))
    if not passed: raise SystemExit(1)

if __name__=='__main__': main()
