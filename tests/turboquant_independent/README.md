# Independent black-box validation suite (TurboQuant R1)

Authored under the independence protocol in Task 8 of
`docs/superpowers/plans/2026-08-27-turboquant-algorithm-qualification.md`.

## Materials used before test freeze

- `docs/superpowers/specs/2026-08-27-turboquant-cache-path-compositionality-design.md`
- The qualification plan's "Interfaces" sections (public names only)
- arXiv 2504.19874 v1 (abstract and full HTML)
- The pinned QJL contract in the plan's Task 7

## Access withheld before this commit

`src/`, `scripts/`, `tests/turboquant/`, all review documents, and commits
`b9227ce` / `e8de8bf` were not read, listed, grepped, or diffed. The tests were
never executed against the implementation before being frozen; they were only
`py_compile`d, and their internal oracles were validated against
independently derived mathematics.

## What is tested

| Area | Files |
|---|---|
| Seed wire format, QR sign, rotation orthogonality | `test_conventions.py` |
| Lloyd-Max density, stationarity, analytic vs empirical distortion | `test_codebook_math.py` |
| Algorithm 1: rotation convention, norms, zero vectors | `test_mse_algorithm.py` |
| Algorithm 2: bit packing, zero sign, literal estimator, unbiasedness | `test_product_algorithm.py` |
| Gate logic, bootstrap, config validation | `test_qualification_gates.py` |
| Canonical JSON, overwrite refusal, registered-profile freeze | `test_artifact_contract.py` |
| Pinned upstream contract, declared zero-sign difference | `test_author_contract.py` |

Assertions are checked against oracles written in `conftest.py` from the
paper's own equations, not against a restatement of the plan's prose. The
oracle for bit packing was separately confirmed to agree with
`np.packbits(bitorder="little")` at widths 1, 7, 8, 9, 16, 33, and 128.

## Independently reproduced reference values

FP64 quadrature performed by this validator before freezing reproduces the
spec's registered analytic distortions to within 4e-13 relative error:

| bits | analytic | paper | relative error vs paper |
|---|---|---|---|
| 1 | 0.3608885937 | 0.36 | 0.2% |
| 2 | 0.1160000703 | 0.117 | 0.9% |
| 3 | 0.0339659258 | 0.03 | 13.2% |
| 4 | 0.0093147880 | 0.009 | 3.5% |

## Two deliberate non-assertions

Both were found by simulating the tests against independently written
reference implementations before freezing, and both would otherwise have
produced false findings against a correct implementation.

1. **Four-bit QJL distortion is a diagnostic, not a gate.** Simulation put a
   correct implementation at ~15.4% relative error against the paper's
   `0.047/d`, just outside the registered 15% band. This is the inherited
   rounding the spec explicitly designates non-gating (the paper's 3-bit
   scalar value is rounded to `0.03` against a true `0.033966`). Gating on it
   would penalize the implementation for the paper's rounding.

2. **No assertion that the product quantizer beats a plain MSE codebook at
   equal total bits.** Simulation showed the opposite for iid Gaussian keys:
   a 3-bit MSE codebook achieved ~2.6e-4 normalized inner-product error
   against ~1.4e-3 for the 3-bit product quantizer. Algorithm 2 targets
   worst-case inner-product error, not average-case error on isotropic data.
   The intuition was wrong, so the assertion was removed rather than frozen.

## Running

```bash
CUDA_HOME=/usr/local/cuda-12.8 PATH=/usr/local/cuda-12.8/bin:$PATH \
  QJL_AUTHOR_CHECKOUT=/tmp/hamutay-turboquant-author/QJL \
  uv run pytest tests/turboquant_independent -v
```

CUDA-dependent tests in `test_author_contract.py` skip with a precise reason
when the GPU, the 12.8 toolkit, or the author checkout is absent. The pinned
contract tests that need no checkout never skip.
