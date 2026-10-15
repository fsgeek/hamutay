# TurboQuant R1 qualification: registered run `r1-initial`

Executed 2026-10-13 by the hamutay custodian (Claude Opus 5.5) under plan
`docs/superpowers/plans/2026-08-27-turboquant-algorithm-qualification.md`,
Task 9. The plan and spec were designed with a Codex instance acting as
researcher; Tony Mason is principal investigator.

## Conclusion

**R1 passed.** All five registered gates passed, checked by hand against their
frozen definitions, not only from the status boolean. The model-level
implementation plan may now be written. No cache-path, serving-lifecycle or
behavioral result is claimed or implied.

The prediction committed before the run (`e99d483`,
`2026-10-13-turboquant-r1-prediction.md`) expected bias equivalence to fail at
2 bits (~60%). **That prediction was wrong.** The 2-bit shift in the
8,000-sample development record (mean 0.00131) does not appear at one million
samples (mean 0.000118, ordinary 95% interval [-0.000009, 0.000246]); it was
sampling noise.

## Run

- Run ID `r1-initial`, run UUID `4d1548a3-a8c8-4016-80d5-85b1125b26b2`,
  profile `registered`; 1,000,000 samples, d = 128, bits 1-4, batch 4000,
  1000 bootstrap blocks, 10,000 resamples (configuration sha256 `558437a2…`).
- Commit `2fe65af4f3a3ac10938dc1df5fee68211c2ecf33`, no dirty paths.
- 2026-10-13 19:55:11Z to 20:01:49Z (6 min 38 s), RTX 4090
  (GPU-650f0a7b…, driver 591.86), CUDA 12.8.93 nvcc, torch 2.10.0+cu128,
  numpy 2.4.3, scipy 1.17.1, Python 3.14.3; 128-CPU WSL2 host.
- Author QJL `https://github.com/amirzandieh/QJL` at `648b3641…`, clean,
  re-cloned 2026-10-13 to the plan's path; kernel hashes checked by the
  preflight before compilation.
- Three fresh worker processes, pids 226377, 234143, 243089; one canonical
  payload sha256 `42369985…85c6`.
- Independent validation: 2026-09-18 report, status `passed` (Task 8
  completion `724f2a4`).

### Artifact sha256

| file | sha256 |
|---|---|
| execution-0.json | a44ef97301c984c20f0be414afe065caedd6cd9feb12d5f8c33d842b29d713c5 |
| execution-1.json | b0ce335faa1c0004117da09c7100bc90bf2c485b74515f28067bfd23dee9883e |
| execution-2.json | d6cc5528a301a1aba3ce6c139d862cfeadb84c545d2c1092a815dd432457fd38 |
| manifest.json | a4c2e7700cb5d4023b5e63acf576e46fa49a9ec1dd3e0111c35a8ce467a1ce5a |
| qualification.json | 7ce9a067e223af3b31d946c15fb6d3fddc451bebbd3e5fe033dda3d4249b8d5c |
| resolved_inputs.npz | 1fff7a57597527982f8f06ce5a39019e6bbb8c032d64d1d12a050f1cbcb42e5d |
| run.log | dc387eaba539d35861057583f2ff1d71d03fbfe91763e8dc1dae9b7838c08355 |

## Gates

1. **Round-trip determinism: passed.** Bit-identical canonical payload across
   the three processes.
2. **Scalar distortion: passed** (limits: 0.5% vs analytic, 15% vs paper).

   | bits | empirical | analytic (FP64) | rel. err. | paper | rel. err. |
   |---|---|---|---|---|---|
   | 1 | 0.360845 | 0.36088859 | 0.012% | 0.36 | 0.23% |
   | 2 | 0.115971 | 0.11600007 | 0.025% | 0.117 | 0.88% |
   | 3 | 0.033956 | 0.03396593 | 0.029% | 0.03 | 13.19% |
   | 4 | 0.009311 | 0.00931479 | 0.045% | 0.009 | 3.45% |

   The 3-bit paper error is mostly the paper's rounding (analytic 0.034 vs
   printed 0.03); it is inside the registered 15%, which was not adjusted.
3. **QJL bias equivalence: passed.** Every Bonferroni 98.75% interval lies
   inside ±0.02·RMSE.

   | bits | mean | RMSE | 98.75% interval | bound | 95% interval |
   |---|---|---|---|---|---|
   | 1 | 0.000083 | 0.10980 | [-0.000199, 0.000365] | ±0.002196 | [-0.000135, 0.000298] |
   | 2 | 0.000118 | 0.06592 | [-0.000045, 0.000285] | ±0.001318 | [-0.000009, 0.000246] |
   | 3 | 0.000030 | 0.03737 | [-0.000062, 0.000121] | ±0.000747 | [-0.000043, 0.000100] |
   | 4 | -0.000015 | 0.02023 | [-0.000062, 0.000034] | ±0.000405 | [-0.000054, 0.000025] |

4. **QJL distortion scale: passed** (limit 15% vs paper's 1.57/d, 0.56/d,
   0.18/d, 0.047/d).

   | bits | observed | paper | rel. err. |
   |---|---|---|---|
   | 1 | 0.0120552 | 0.0122656 | 1.72% |
   | 2 | 0.00434515 | 0.004375 | 0.68% |
   | 3 | 0.00139657 | 0.00140625 | 0.69% |
   | 4 | 0.000409333 | 0.000367188 | 11.48% |

   4 bits is the closest to its limit, as the spec anticipated (it inherits the
   paper's rounded 3-bit scalar value).
5. **Author-code differential: passed.** Max absolute score error 3.81e-6
   (limit 1e-5), max relative 3.85e-6 (limit 1e-4); inlier sign bytes equal;
   outlier norms exactly zero.

Non-gating sensitivity (row-orthogonalized projection, as in the public QJL
code): bias means -0.000038, -0.000068, -0.000029, -0.000002 at 1-4 bits, all
intervals containing zero; product distortion 0.00443, 0.00160, 0.000514,
0.000151, about 2.7x lower than the paper-literal iid projection at every
width.

## Suites with the author differential active

- Before the run: 380 passed, no skips, 440.93 s.
- After the run: 380 passed, no skips, 277.56 s.

Full outputs: `docs/superpowers/validation/2026-10-13-turboquant-r1-registered/`.

## Declared deviations

- Every GPU step ran under `deploy/ayllu-gpu run` (lease, 30 min TTL renewed),
  as in the 09-18 validation. qwen's model server was stopped for each lease
  and restarted after; qwen was in a chosen quiet and was told at plaza
  before the first lease.
- The registered command was invoked as the worktree venv's
  `turboquant-qualify` rather than `uv run turboquant-qualify`, with the
  plan's exact arguments, under `timeout 6h`. Suites ran as
  `.venv/bin/python -m pytest … -q -ra` with `OMP_NUM_THREADS=1`,
  `OPENBLAS_NUM_THREADS=1`, `MAX_JOBS=2`, as on 09-18.
- The suite outputs above are committed beside the plan's named artifacts.
- Commits carry `Co-Authored-By: Claude Opus 5.5`, not the plan's Codex line:
  Claude executed this task.
