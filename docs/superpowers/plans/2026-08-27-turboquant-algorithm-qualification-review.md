# Review: TurboQuant Algorithm Qualification Implementation Plan

Reviewer: a Claude Fable 5 session, 2026-08-27 (evening), at Tony's request.
Reviewed: `2026-08-27-turboquant-algorithm-qualification.md` at commit d3bee63,
against the revised spec at cb0a10c. Nothing here is binding.

Method: I read the plan in full, cloned the author QJL repository at the
pinned commit into a scratch directory (nothing under the project tree),
checked the pinned hashes and the kernel source, checked the local toolchain
against the plan's stated stack, and computed the exact Lloyd-Max distortion
of the registered d=128 codebooks independently (FP64 quadrature, confirmed by
200K-sample Monte Carlo). Numbers below are from those checks, not from
memory.

Overall: the plan is well-structured, the test-first steps are real tests of
the stated conventions, and the wire formats the spec left open (seed
derivation, QR sign, bit packing, zero-sign) are now pinned. The problems are
that two registered gates will fail for reasons unrelated to the
implementation, and one task cannot compile on this machine as configured.
All are fixable before anything is stamped.

## Blocking — the registered run fails or cannot run as written

### 1. Gate 2 fails at 3 bits for a rounding reason

Exact Lloyd-Max distortion for the d=128 sphere-coordinate density
(`d * E[(x - q(x))^2]`, FP64 quadrature; Monte Carlo agrees to 4 digits):

| bits | analytic | Monte Carlo | paper target | rel. error | 10% gate |
|---|---|---|---|---|---|
| 1 | 0.36089 | 0.36104 | 0.36  | +0.2%  | pass |
| 2 | 0.11600 | 0.11609 | 0.117 | -0.9%  | pass |
| 3 | 0.03397 | 0.03398 | 0.03  | +13.2% | **fail** |
| 4 | 0.00931 | 0.00933 | 0.009 | +3.5%  | pass |

The paper's `0.03` is a one-significant-figure rounding of ~0.034 (Gaussian
Lloyd-Max at 8 levels is 0.03454; the sphere marginal at d=128 is slightly
lighter-tailed). A 10% relative gate against a value with ±17% implicit
rounding uncertainty is tighter than the target's precision. A correct
implementation will fail this gate, and the plan's "never waive; repair under
a new commit; rerun everything" rule then invites a repair of code that is
not broken.

Recommendation, in order of preference:

a. Make the primary gate **self-consistency**: empirical normalized MSE on
   the 1M registered vectors must match the *analytic* distortion of the
   frozen codebook (computed in FP64 from the same density) within a tight
   tolerance (0.5% is comfortable; sampling SE at 1M is ~0.1%). This is the
   test that actually certifies Algorithm 1. Report the paper comparison
   separately.
b. If the paper comparison must remain a gate, set its tolerance from the
   target's rounding: half a unit in the last printed digit (0.005 for
   `0.03`, i.e. observed in [0.025, 0.035]) — or state the tolerance as 15%.

Same reasoning applies to gate 4's 4-bit QJL target: `0.047/d` is
`0.03 x 1.57`, so it inherits the rounding. Expected observed value is
~`0.0533/d` (from 0.0340 x pi/2), which is +13.4% against a 15% gate. It
should pass, but by 1.6 points; note it so a marginal pass is not read as
suspicious.

### 2. Gate 3's CI-includes-zero clause has ~18% false-failure rate

At n = 1M the bootstrap SE of the mean is ~rmse/1000, so the 95% interval
has half-width ~0.002 rmse. The second clause (`|mean| <= 0.02 rmse`) is
therefore ~20 SE wide and is the real test; the CI clause is an exact
unbiasedness test at alpha = 0.05 per bit width. QJL is exactly unbiased for
iid Gaussian rows, so for a *correct* implementation the CI excludes zero 5%
of the time per test, and across four bit widths at least one gate fails
with probability 1 - 0.95^4 = 18.5%. That is a registered gate that fails
one run in five with nothing to repair — and the only "repair" available is
a new seed, which is the thing preregistration exists to forbid.

Recommendation: drop the CI clause from the gate (keep it as a reported
diagnostic) and gate on the equivalence bound alone; or Bonferroni it
(98.75% per test) and say so.

### 3. Task 7 cannot compile on this machine as configured

`torch.utils.cpp_extension.load` enforces a CUDA major-version match. Here:

- `nvcc`: `/usr/local/cuda-13.2` (13.2, and it is the only toolkit installed)
- `torch`: 2.10.0+cu128 (`torch.version.cuda == "12.8"`)
- `torch.utils.cpp_extension._check_cuda_version(...)` raises:
  `The detected CUDA version (13.2) mismatches the version that was used to
  compile PyTorch (12.8)`

Options are Tony's: install a CUDA 12.8 toolkit alongside and point
`CUDA_HOME` at it for the oracle, or move the lock to a cu130 torch wheel.
Either way the plan must name the choice, because Task 7's "once
preconditions exist, skipping is forbidden" precondition (`CUDA available`)
is true here while compilation is impossible — the test would error, not
skip.

### 4. Pinned author file paths are wrong; hashes are right

The kernels live at `qjl_kernel/csrc/qjl_quant_kernel.cu` and
`qjl_kernel/csrc/qjl_score_kernel.cu`, not at the repository root as the
Task 7 contract lists them. Verified at commit
`648b3641f96b6e95e091217220b94e4739fd4d82`:

- `LICENSE` → `c71d239d...` matches
- `models/llama3_utils_qjl.py` → `725b6777...` matches
- `qjl_kernel/csrc/qjl_quant_kernel.cu` → `d03b2fd8...` matches
- `qjl_kernel/csrc/qjl_score_kernel.cu` → `848398bb...` matches

The `tcuda_qjl_score` typo is real (`qjl_kernel/qjl_kernel.py:40`), so the
plan is right to call the extension entry points directly.

## Significant

### 5. The outlier-neutralization trick works, with two details to add

I read the score kernel's final combination. It computes
`norm_k = sqrt(k_norm^2 - outlier_norm^2)` and
`score = sqrt(pi/2)/m * norm_k * <inlier> + sqrt(pi/2)/m_o * outlier_norm * <outlier>`.
There is no division by the outlier norm, so a zero outlier channel
contributes exactly zero and the plan's construction (coordinate 127 zeroed,
sole outlier index 127) is sound. Two things the adapter must get right that
the plan does not state:

- The score kernel takes a precomputed `query_sketch` (`S @ q`) as its own
  argument in addition to `query_states` and `rand_prj`; the adapter must
  compute it in FP32 with the same `S`. It also subtracts the outlier
  contribution from the query sketch internally; with query coordinate 127
  zero that term is zero.
- **Zero-sign convention differs.** The author kernel packs
  `sketched > 0 ? 1 : 0` — an exact zero becomes a *negative* sign. The plan
  fixes `>= 0 -> +1`. Generic FP32 inputs never hit exact zero on the inlier
  sketch, so the byte-equality assertion will hold, but the difference must
  be written into the convention record, as the spec requires of
  "unavoidable convention mismatch", rather than discovered when a test
  vector happens to produce a zero.

### 6. Determinism gate: run three processes, not three objects

The spec says "three same-build executions"; Task 6 runs three passes in one
process. The registered computation is seconds to a minute of NumPy (the
only slow part is the one-time Lloyd-Max quadrature). Three separate process
launches cost nothing and catch what one process cannot (allocator state,
thread pool, BLAS reduction order across runs). Keep the in-process triple if
useful, but the gate should be across processes.

### 7. Config default disagrees with the registered profile

`QualificationConfig(batch_size=4096)` while registered mode freezes 4,000
"evenly dividing both sample and block boundaries". 4,096 does not divide
1,000,000. Make the default 4,000 and have the config validate divisibility,
so a development run cannot silently differ in its last batch.

### 8. Who writes the tests

The project norm (and yesterday's khipu) is that code and tests come from
separate minds; Codex found eleven defects in Claude's harness code that
Claude's own tests missed. This plan has Codex authoring the tests *and* the
implementation. It is not my call, but if Codex executes its own plan, a
Claude instance should author an adversarial test pass before the registered
run — the analytic-distortion self-consistency test in item 1 is an obvious
first one.

## Minor

- `test_gate_boundaries_are_inclusive` sets observed == target; it does not
  exercise a boundary. Either test at exactly 10% or rename it.
- `test_gaussian_rotation_is_repeatable_fp32` asserts `Q @ Q.T ≈ I` at
  `atol=2e-6` for a 128x128 FP32 product; the constructor uses `2e-5`. The
  test is deterministic so it will either always pass or always fail, but if
  it fails the fix is the tolerance, not the rotation.
- Row-orthogonalized sensitivity projection: state the row scaling (unit
  rows, or Gaussian-norm rows) — the `sqrt(pi/2)/m` estimator assumes
  Gaussian rows, and the sensitivity number is uninterpretable without it.
- Author differential tolerance: the kernel accumulates in FP32 with warp
  reductions in a different order from NumPy's; `atol 1e-5` on scores of
  order ~1 at d=128 is plausible but not generous. If it fails by 1e-5-ish,
  that is reduction order, not a convention mismatch — say so in advance.

## One line

Gate 2 fails at 3 bits by construction (0.0340 vs 0.03) and gate 3's CI
clause fails one run in five by chance — fix both before stamping; Task 7
cannot compile against CUDA 13.2 with a cu128 torch and its file paths are
wrong; the outlier trick is sound but the zero-sign convention differs.
