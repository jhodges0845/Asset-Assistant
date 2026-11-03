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


## Playback measurement optimization (2026-11-03)

A local cProfile run of the default Human GLB playback test passed and recorded
about 210 million calls. Large costs included the per-vertex pose-error,
movement and ground-height loops, plus weighted-contact clip generation.
Instrumented runtime is not a normal timing benchmark.

The shared Human/Canine playback tests now use Blender's bulk vertex reader
and NumPy arrays for world coordinates, distance maxima and ground height.
NumPy is supplied by the Blender runtime; this adds no production dependency.
The helpers live under `tests/blender/playback_metrics.py`. They retain float32
coordinates/displacements and use double accumulation for distance magnitudes.
Invalid/non-finite comparisons fail explicitly.

All 34 samples for each of Walk, Idle, Run and repeated Idle remain. Every
imported vertex is compared, the initial KDTree correspondence stays fixed
throughout motion, and all original error/contact/closure thresholds remain.
Real generation, semantic edits, export, import and action switching still run.
The weighted-contact solver and other production code are unchanged.

Metric regressions compare the bulk calculations with Blender mathutils under
translation, rotation and nonuniform/negative scale, detect a single displaced
vertex around the existing thresholds, reject wrong correspondence and invalid
data, and compare three-axis distance magnitudes with the scalar reference.


Sequential, fresh-process measurements of the default Human owned-clip playback
case on this Windows host were **125.09 seconds before** and **64.12 seconds
after**, about 49% less time. The baseline replays the original method from
`fb8b11a` with the same Human provider and .72-second Run; the optimized run
selects only `test_owned_clip_library` so the other Human test cannot warm its
geometry cache. These are local per-test results, not a promised CI reduction.
Earlier overlapping runs and cProfile timings are excluded from this comparison.
Evidence: `artifacts/playback-bulk-sequential-{before,after}.log`.

All 18 focused checks pass: default and edited Human/Canine actual GLB playback,
Human Idle reset, and 13 metric regressions. No test, frame, vertex, assertion,
CI job or required validation step is removed. Weighted-contact generation is
still a measured cost and remains a separate future optimization candidate.
