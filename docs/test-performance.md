# Test runtime audit (2026-11-02)

## Measured CI baseline

Run [41453690036](https://github.com/jhodges0845/Asset-Assistant/actions/runs/41453690036)
executed 493 core tests. Python 3.12 line coverage took 1,156.675 seconds
(19m17s), versus roughly 3-5 minutes for the uninstrumented Python jobs.
Coverage was 95% (6,561 statements, 300 missing), above the required 90%.
The preceding run 41449117609 also spent about 20 minutes in the coverage job.

Blender integration tests took about 9 minutes, followed by about 94 seconds
of fresh-process, undo and packaged-addon checks. Runtime cache restoration
was 9 seconds; setup/download work was not the main bottleneck. Human visual
review finished in about 96 seconds including setup and uploads.

## Changes

- Use coverage.py 7.17.0 with `COVERAGE_CORE=sysmon` for the Python 3.12
  line-coverage job. This is the same coverage version used by the baseline,
  now pinned for reproducible measurements. All discovered tests, measured
  source files and the 90% gate remain unchanged.
- Report the 20 slowest core tests in the coverage job using unittest's
  Python 3.12 `--durations` option.
- Report the 20 slowest Blender tests on the default full-suite invocation.
  Explicit pytest arguments after Blender's `--` separator remain supported.

The [coverage engine documentation](https://coverage.readthedocs.io/en/7.14.0/howitworks.html)
describes sys.monitoring's lower instrumentation overhead. On Python 3.12,
this mode supports line coverage, not branch coverage. If branch coverage,
dynamic contexts or plugins are introduced, revisit the engine selection.

## Further opportunities

Use the new duration reports before changing test fixtures or splitting jobs.
Geometry corner sweeps, deformation checks and separate-provider playback
cases cover distinct behavior; do not reduce their sample counts for speed.
Blender scene state and fresh-process persistence checks must remain isolated.
A separate Blender test shard may shorten wall time but increases runner and
setup cost, and should follow measured per-test timings.

No test cases, Python compatibility jobs, visual review, package checks or
fresh-process persistence checks are removed by this change. This pass changes
only test instrumentation and reporting, not production generation behavior.
