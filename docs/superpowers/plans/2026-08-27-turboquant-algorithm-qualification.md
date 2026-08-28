# TurboQuant Algorithm Qualification Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build and execute the transparent R1 qualification package for TurboQuant Algorithms 1 and 2, producing immutable evidence for determinism, published distortion scale, QJL bias, and agreement with the pinned author QJL implementation.

**Architecture:** A small `hamutay.turboquant` package separates deterministic random-object construction, the spherical Lloyd-Max scalar quantizer, the QJL product estimator, streaming qualification statistics, and append-only evidence artifacts. Unit tests establish each mathematical convention before the one-million-sample registered run. A CUDA-only differential adapter compiles the two unmodified, hash-pinned author kernels outside the package and compares their packed sketches and scores with the transparent reference. Passing R1 is a hard gate: the model cache-path harness, corpus builder, and behavioral assay receive a second implementation plan only after this plan's registered evidence passes.

**Tech Stack:** WSL2 Ubuntu 22.04.5, Python >=3.14, `uv`, NumPy 2.4.x, SciPy 1.17.x, PyTorch 2.10.x built for CUDA 12.8, side-by-side CUDA 12.8 WSL-Ubuntu toolkit, pytest, author QJL CUDA extensions compiled with `torch.utils.cpp_extension.load`, canonical JSON and NPZ evidence artifacts.

**Spec:** `docs/superpowers/specs/2026-08-27-turboquant-cache-path-compositionality-design.md`

**Revision:** Updated after independent review on 2026-08-27. The approved amendment adds analytic scalar-distortion consistency, simultaneous QJL-bias equivalence, process-level determinism, a pinned WSL CUDA compiler environment, and an independent adversarial-test checkpoint.

## Global Constraints

- Run all Python through `uv run`; do not use system Python.
- Compile the author QJL extensions only with `CUDA_HOME=/usr/local/cuda-12.8` and `/usr/local/cuda-12.8/bin` first on `PATH`. Do not change the system CUDA 13.2 default and never install a Linux NVIDIA driver inside WSL.
- Before Task 1, invoke `superpowers:using-git-worktrees` and create an isolated feature worktree. The present checkout contains unrelated user-owned changes, while the registered run requires a clean scientific execution tree.
- This plan implements only replication-ladder stage R1. It does not download Llama weights or WikiText, build a model KV cache, run a language model, or evaluate S, M, A, E, C-seq, or C-task.
- Treat the accessible arXiv v1 equations and Algorithms 1/2 as normative for the transparent reference. Treat author QJL commit `648b3641f96b6e95e091217220b94e4739fd4d82` as a differential oracle, not as a substitute specification.
- Never waive a failed gate. Persist the failure, repair under a new implementation commit, and rerun the entire registered qualification.
- Registered evidence is append-only. Refuse to overwrite an existing run directory or artifact. Development outputs must use `experiments/turboquant/development/`; only the exact registered command may write beneath `experiments/turboquant/qualification/`.
- Every artifact records the Git commit, dirty-worktree state, exact study configuration, package versions, platform/CUDA information, input hashes, and declared numerical conventions.
- This is a shared working tree. Stage only files named by the current task; never use `git add .` or `git add -A`. Preserve unrelated user changes and the untracked external review.
- Use this exact signed commit identity for every commit:

  ```bash
  git -c user.email=hamutay@wamason.com -c user.name="Tony Mason" -c user.signingkey=01193FA2631C8AE8E4DF266E216D3C9B920813A1 commit -S -m "task-specific subject

  Co-Authored-By: Codex <noreply@openai.com>"
  ```

- The post-commit hook creates an OpenTimestamps stamp commit. Do not edit or bypass the hook.
- Use FP64 to construct rotations and codebooks, then freeze FP32 resolved arrays. Reference quantization, reconstruction, and diagnostic reductions use FP32 unless the plan explicitly says FP64.
- The registered dimension is 128. Inputs are arbitrary nonzero vectors: normalize each vector before applying a spherical quantizer and restore its original norm on reconstruction. Zero vectors have norm zero, all-zero codes/sketches, and exact zero reconstruction.
- Vector convention is row-major: rotation is `y = x @ rotation.T`; inverse rotation is `x_hat = y_hat @ rotation`. QJL projections are stored as rows, so sketches are `projection @ residual` for one vector and `residual @ projection.T` for a batch.
- In the transparent reference, every zero sign maps to `+1`. The author kernel maps exact zero to `-1`; Task 7 records and tests this declared convention difference. Bit packing is little-endian within each byte: sketch coordinate `j` occupies bit `j % 8` of byte `j // 8`.
- Do not add entropy coding, mixed precision, outlier selection, recent-token buffers, or model-serving behavior to this package.

---

### Task 1: Package skeleton, study seed, and canonical rotations

**Files:**
- Create: `src/hamutay/turboquant/__init__.py`
- Create: `src/hamutay/turboquant/seeding.py`
- Create: `src/hamutay/turboquant/rotation.py`
- Create: `tests/turboquant/test_seeding_rotation.py`

**Interfaces:**
- `STUDY_SEED_HEX = "0b311d5d4eceaf773efde389305a1b5a"`
- `derive_seed(*fields: str | int, study_seed_hex: str = STUDY_SEED_HEX) -> int`
- `rng_for(*fields: str | int) -> numpy.random.Generator`
- `canonical_qr(matrix: NDArray[np.float64]) -> NDArray[np.float64]`
- `gaussian_rotation(dimension: int, *seed_fields: str | int) -> NDArray[np.float32]`

- [ ] **Step 1: Write the failing tests**

```python
# tests/turboquant/test_seeding_rotation.py
import hashlib

import numpy as np

from hamutay.turboquant.rotation import canonical_qr, gaussian_rotation
from hamutay.turboquant.seeding import STUDY_SEED_HEX, derive_seed


def test_derive_seed_uses_registered_wire_format():
    fields = (
        "0e9e39f249a16976918f6564b8830bc894c89659",
        "tq_prod",
        7,
        "k",
        3,
        "projection",
    )
    wire = "|".join((STUDY_SEED_HEX, *(str(field) for field in fields)))
    expected = int.from_bytes(hashlib.sha256(wire.encode()).digest()[:16], "big")
    assert derive_seed(*fields) == expected


def test_canonical_qr_has_nonnegative_diagonal_and_is_orthogonal():
    matrix = np.array([[1.0, 2.0], [3.0, 4.0]], dtype=np.float64)
    rotation = canonical_qr(matrix)
    signed_r = rotation.T @ matrix
    np.testing.assert_allclose(rotation.T @ rotation, np.eye(2), atol=1e-14)
    assert np.all(np.diag(signed_r) >= 0.0)


def test_gaussian_rotation_is_repeatable_fp32():
    first = gaussian_rotation(128, "algorithm_1", 0, "v", 0, "rotation")
    second = gaussian_rotation(128, "algorithm_1", 0, "v", 0, "rotation")
    assert first.dtype == np.float32
    assert np.array_equal(first, second)
    np.testing.assert_allclose(first @ first.T, np.eye(128), atol=2e-5)
```

- [ ] **Step 2: Run the tests and observe the import failure**

Run: `uv run pytest tests/turboquant/test_seeding_rotation.py -v`

Expected: FAIL because `hamutay.turboquant` does not exist.

- [ ] **Step 3: Implement seed derivation and rotations**

`derive_seed` must validate the seed as exactly 32 lowercase hexadecimal characters, reject any field containing `|`, serialize integers as unpadded decimal with `str`, and return the unsigned big-endian interpretation of the first 16 SHA-256 bytes. `rng_for` returns `np.random.Generator(np.random.PCG64(seed))`.

`canonical_qr` calls `np.linalg.qr` in FP64, computes `sign = np.where(np.diag(r) < 0, -1.0, 1.0)`, and multiplies columns of `q` by that sign. `gaussian_rotation` validates a positive dimension, generates a `(d, d)` standard-normal matrix with `rng_for`, applies `canonical_qr`, and returns a C-contiguous FP32 array.

Export the public names from `__init__.py`; do not expose mutable module-global generators.

- [ ] **Step 4: Run the focused tests**

Run: `uv run pytest tests/turboquant/test_seeding_rotation.py -v`

Expected: 3 PASS.

- [ ] **Step 5: Commit**

```bash
git add src/hamutay/turboquant/__init__.py src/hamutay/turboquant/seeding.py src/hamutay/turboquant/rotation.py tests/turboquant/test_seeding_rotation.py
git -c user.email=hamutay@wamason.com -c user.name="Tony Mason" -c user.signingkey=01193FA2631C8AE8E4DF266E216D3C9B920813A1 commit -S -m "implement deterministic TurboQuant rotations

Co-Authored-By: Codex <noreply@openai.com>"
```

---

### Task 2: Dimension-specific spherical Lloyd-Max codebooks

**Files:**
- Create: `src/hamutay/turboquant/codebook.py`
- Create: `tests/turboquant/test_codebook.py`
- Modify: `src/hamutay/turboquant/__init__.py`

**Interfaces:**
- `sphere_coordinate_density(x: float | NDArray, dimension: int) -> float | NDArray`
- `lloyd_max_codebook(dimension: int, bits: int, *, tolerance: float = 1e-12, max_iterations: int = 10_000) -> NDArray[np.float32]`
- `nearest_code_indices(values: NDArray[np.float32], codebook: NDArray[np.float32]) -> NDArray[np.uint8]`

- [ ] **Step 1: Write failing mathematical tests**

```python
# tests/turboquant/test_codebook.py
import numpy as np
from scipy.integrate import quad

from hamutay.turboquant.codebook import (
    lloyd_max_codebook,
    nearest_code_indices,
    sphere_coordinate_density,
)


def test_sphere_coordinate_density_integrates_to_one():
    integral, _ = quad(lambda x: sphere_coordinate_density(x, 128), -1.0, 1.0)
    assert abs(integral - 1.0) < 1e-11


def test_one_bit_centroids_match_closed_form_scale():
    codebook = lloyd_max_codebook(128, 1)
    expected = np.sqrt(2.0 / (np.pi * 128.0))
    np.testing.assert_allclose(codebook, [-expected, expected], rtol=0.025)


def test_codebooks_are_symmetric_ordered_and_repeatable():
    first = lloyd_max_codebook(128, 4)
    second = lloyd_max_codebook(128, 4)
    assert first.dtype == np.float32
    assert np.array_equal(first, second)
    assert np.all(np.diff(first) > 0)
    np.testing.assert_allclose(first, -first[::-1], atol=2e-7)


def test_nearest_index_ties_choose_lower_centroid():
    codebook = np.array([-1.0, 1.0], dtype=np.float32)
    indices = nearest_code_indices(np.array([-0.1, 0.0, 0.1], np.float32), codebook)
    np.testing.assert_array_equal(indices, [0, 0, 1])
```

- [ ] **Step 2: Run the test and observe failure**

Run: `uv run pytest tests/turboquant/test_codebook.py -v`

Expected: FAIL because the codebook module does not exist.

- [ ] **Step 3: Implement deterministic continuous Lloyd-Max**

Use the paper's coordinate density

```text
Gamma(d/2) / (sqrt(pi) Gamma((d-1)/2)) * (1 - x^2)^((d-3)/2), -1 <= x <= 1.
```

Compute the normalization constant with `scipy.special.gammaln`. Return zero outside `[-1, 1]`. Validate `dimension >= 2` and `bits in 0..8`; bits zero returns the single centroid `[0.0]`.

For positive bits, initialize boundaries by equal-probability quantiles of `Beta((d-1)/2, (d-1)/2)` mapped from `[0,1]` to `[-1,1]`. For each Lloyd iteration, integrate probability and first moment over every boundary interval with `scipy.integrate.quad(epsabs=1e-14, epsrel=1e-13, limit=200)`, update nonempty centroids to `moment / mass`, symmetrize with `(c - c[::-1]) / 2`, and set internal boundaries to adjacent-centroid midpoints. Stop when maximum centroid movement is at most `tolerance`; raise `RuntimeError` on non-convergence. Cast only the final centroids to FP32.

`nearest_code_indices` validates a one-dimensional, strictly increasing codebook, applies `np.searchsorted` to the midpoint boundaries with `side="left"`, and returns `uint8`.

- [ ] **Step 4: Run focused tests**

Run: `uv run pytest tests/turboquant/test_codebook.py -v`

Expected: 4 PASS.

- [ ] **Step 5: Commit**

```bash
git add src/hamutay/turboquant/__init__.py src/hamutay/turboquant/codebook.py tests/turboquant/test_codebook.py
git -c user.email=hamutay@wamason.com -c user.name="Tony Mason" -c user.signingkey=01193FA2631C8AE8E4DF266E216D3C9B920813A1 commit -S -m "implement TurboQuant spherical codebooks

Co-Authored-By: Codex <noreply@openai.com>"
```

---

### Task 3: Algorithm 1 MSE quantization and frozen representation

**Files:**
- Create: `src/hamutay/turboquant/mse.py`
- Create: `tests/turboquant/test_mse.py`
- Modify: `src/hamutay/turboquant/__init__.py`

**Interfaces:**

- Frozen slotted dataclass `MSECodes(indices: np.ndarray, norms: np.ndarray)`, where indices are `uint8` with the vectors' full shape and norms are FP32 with the final vector dimension removed.
- `MSEQuantizer(rotation: np.ndarray, codebook: np.ndarray)`
- `MSEQuantizer.quantize(vectors: np.ndarray) -> MSECodes`
- `MSEQuantizer.dequantize(codes: MSECodes) -> np.ndarray`

- [ ] **Step 1: Write failing behavior tests**

```python
# tests/turboquant/test_mse.py
import numpy as np

from hamutay.turboquant.codebook import lloyd_max_codebook
from hamutay.turboquant.mse import MSEQuantizer


def quantizer(bits: int) -> MSEQuantizer:
    return MSEQuantizer(np.eye(4, dtype=np.float32), lloyd_max_codebook(4, bits))


def test_mse_quantizer_preserves_shape_and_norm_scale():
    vectors = np.array([[3.0, 0.0, 4.0, 0.0], [1.0, -2.0, 3.0, -4.0]], np.float32)
    codes = quantizer(3).quantize(vectors)
    reconstructed = quantizer(3).dequantize(codes)
    assert codes.indices.shape == vectors.shape
    np.testing.assert_allclose(codes.norms, np.linalg.norm(vectors, axis=-1))
    assert reconstructed.shape == vectors.shape
    assert reconstructed.dtype == np.float32


def test_zero_vector_round_trips_exactly():
    q = quantizer(2)
    codes = q.quantize(np.zeros((2, 4), np.float32))
    assert np.all(codes.indices == 0)
    assert np.array_equal(q.dequantize(codes), np.zeros((2, 4), np.float32))


def test_codes_and_reconstruction_are_bit_repeatable():
    q = quantizer(4)
    vectors = np.arange(32, dtype=np.float32).reshape(8, 4) - 15.5
    a = q.quantize(vectors)
    b = q.quantize(vectors.copy())
    assert np.array_equal(a.indices, b.indices)
    assert np.array_equal(a.norms, b.norms)
    assert np.array_equal(q.dequantize(a), q.dequantize(b))


def test_constructor_rejects_nonorthogonal_rotation():
    bad = np.ones((4, 4), np.float32)
    try:
        MSEQuantizer(bad, lloyd_max_codebook(4, 2))
    except ValueError as error:
        assert "orthogonal" in str(error)
    else:
        raise AssertionError("nonorthogonal rotation accepted")
```

- [ ] **Step 2: Run the focused test and see it fail**

Run: `uv run pytest tests/turboquant/test_mse.py -v`

Expected: FAIL because `mse.py` does not exist.

- [ ] **Step 3: Implement Algorithm 1**

The constructor freezes C-contiguous FP32 copies, checks square rotation shape, strictly increasing 1-D codebook, at most 256 centroids, and orthogonality with `atol=2e-5`. It exposes read-only `rotation` and `codebook` properties.

`quantize` accepts FP32-compatible arrays with final dimension `d`. Compute norms in FP32, divide only nonzero rows, rotate with `normalized @ rotation.T`, and obtain scalar indices through `nearest_code_indices`. Force every zero-vector index to zero. `dequantize` validates shapes and index range, gathers centroids, applies `rotated_hat @ rotation`, multiplies by the stored norms, and forces zero-norm rows to exact zeros. Every public output is C-contiguous and owns its memory.

- [ ] **Step 4: Run tests**

Run: `uv run pytest tests/turboquant/test_mse.py tests/turboquant/test_codebook.py -v`

Expected: 8 PASS.

- [ ] **Step 5: Commit**

```bash
git add src/hamutay/turboquant/__init__.py src/hamutay/turboquant/mse.py tests/turboquant/test_mse.py
git -c user.email=hamutay@wamason.com -c user.name="Tony Mason" -c user.signingkey=01193FA2631C8AE8E4DF266E216D3C9B920813A1 commit -S -m "implement TurboQuant MSE reference

Co-Authored-By: Codex <noreply@openai.com>"
```

---

### Task 4: Algorithm 2 product estimator and bit packing

**Files:**
- Create: `src/hamutay/turboquant/product.py`
- Create: `tests/turboquant/test_product.py`
- Modify: `src/hamutay/turboquant/__init__.py`

**Interfaces:**

- Frozen slotted dataclass `ProductCodes(mse: MSECodes, packed_signs: np.ndarray, residual_norms: np.ndarray)`. Packed signs are `uint8` with final length `ceil(sketch_dim / 8)`; residual norms are FP32 with the vector dimension removed.
- `ProductQuantizer(mse_quantizer: MSEQuantizer, projection: np.ndarray)`
- `ProductQuantizer.quantize(vectors: np.ndarray) -> ProductCodes`
- `ProductQuantizer.dequantize(codes: ProductCodes) -> np.ndarray`
- `ProductQuantizer.estimate_inner_products(queries: np.ndarray, codes: ProductCodes) -> np.ndarray`
- `pack_signs(signs: np.ndarray) -> np.ndarray`
- `unpack_signs(packed: np.ndarray, sketch_dim: int) -> np.ndarray`

- [ ] **Step 1: Write failing tests for the literal estimator**

```python
# tests/turboquant/test_product.py
import numpy as np

from hamutay.turboquant.codebook import lloyd_max_codebook
from hamutay.turboquant.mse import MSEQuantizer
from hamutay.turboquant.product import ProductQuantizer, pack_signs, unpack_signs


def product_quantizer() -> ProductQuantizer:
    mse = MSEQuantizer(np.eye(4, dtype=np.float32), lloyd_max_codebook(4, 1))
    projection = np.array(
        [[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]],
        dtype=np.float32,
    )
    return ProductQuantizer(mse, projection)


def test_pack_signs_is_little_endian_and_zero_is_positive():
    raw = np.array([[1.0, -1.0, 0.0, 2.0, -2.0, -3.0, 4.0, 5.0, -1.0]])
    packed = pack_signs(raw >= 0)
    np.testing.assert_array_equal(packed, [[0b11001101, 0]])
    unpacked = unpack_signs(packed, 9)
    np.testing.assert_array_equal(unpacked, np.where(raw >= 0, 1.0, -1.0))


def test_product_quantizer_matches_literal_formula():
    q = product_quantizer()
    keys = np.array([[0.9, -0.2, 0.3, -0.1]], np.float32)
    queries = np.array([[0.2, 0.4, -0.5, 0.7]], np.float32)
    codes = q.quantize(keys)
    mse_hat = q.mse_quantizer.dequantize(codes.mse)
    residual = keys - mse_hat
    signs = np.where(residual @ q.projection.T >= 0, 1.0, -1.0)
    literal = (
        np.sum(queries * mse_hat, axis=-1)
        + np.sqrt(np.pi / 2.0) / q.sketch_dim
        * codes.residual_norms
        * np.sum((queries @ q.projection.T) * signs, axis=-1)
    )
    np.testing.assert_allclose(q.estimate_inner_products(queries, codes), literal, atol=2e-7)


def test_product_round_trip_is_repeatable_and_zero_safe():
    q = product_quantizer()
    vectors = np.array([[0, 0, 0, 0], [1, 2, 3, 4]], np.float32)
    first = q.quantize(vectors)
    second = q.quantize(vectors)
    assert np.array_equal(first.packed_signs, second.packed_signs)
    assert np.array_equal(first.residual_norms, second.residual_norms)
    assert np.array_equal(q.dequantize(first), q.dequantize(second))
    assert np.array_equal(q.dequantize(first)[0], np.zeros(4, np.float32))
```

- [ ] **Step 2: Run the focused test and observe failure**

Run: `uv run pytest tests/turboquant/test_product.py -v`

Expected: FAIL because `product.py` does not exist.

- [ ] **Step 3: Implement Algorithm 2**

The projection is a C-contiguous FP32 array of shape `(sketch_dim, d)` with positive sketch dimension divisible by eight for the registered run. The transparent paper-literal registered projection is iid standard Gaussian; do not orthogonalize or scale it.

`quantize` first runs the embedded Algorithm 1 quantizer, reconstructs the MSE component, computes the original-scale residual and FP32 residual norm, evaluates `residual @ projection.T`, maps nonnegative values to `+1`, and packs them. `dequantize` returns

```text
mse_hat + sqrt(pi / 2) / sketch_dim * residual_norm * (signs @ projection)
```

and makes zero-norm inputs exact zero. `estimate_inner_products` evaluates the same estimator without materializing an extra reconstructed batch. Validate query/code leading shapes exactly; this first package deliberately supports paired queries and keys rather than broadcasting ambiguous shapes.

The total-bit convention is explicit: a `b`-bit product quantizer contains an Algorithm 1 codebook at `b - 1` bits plus its fixed QJL sketch and norm. Bits 1 through 4 therefore use zero- through three-bit MSE codebooks.

- [ ] **Step 4: Run all mathematical unit tests**

Run: `uv run pytest tests/turboquant/test_seeding_rotation.py tests/turboquant/test_codebook.py tests/turboquant/test_mse.py tests/turboquant/test_product.py -v`

Expected: 14 PASS.

- [ ] **Step 5: Commit**

```bash
git add src/hamutay/turboquant/__init__.py src/hamutay/turboquant/product.py tests/turboquant/test_product.py
git -c user.email=hamutay@wamason.com -c user.name="Tony Mason" -c user.signingkey=01193FA2631C8AE8E4DF266E216D3C9B920813A1 commit -S -m "implement TurboQuant product reference

Co-Authored-By: Codex <noreply@openai.com>"
```

---

### Task 5: Streaming R1 statistics, bootstrap, and gate evaluation

**Files:**
- Create: `src/hamutay/turboquant/qualification.py`
- Create: `tests/turboquant/test_qualification.py`
- Modify: `src/hamutay/turboquant/__init__.py`

**Interfaces:**
- `QualificationConfig(dimension=128, sample_count=1_000_000, batch_size=4000, bootstrap_blocks=1000, bootstrap_resamples=10_000, bits=(1,2,3,4))`
- `run_synthetic_qualification(config: QualificationConfig) -> QualificationResult`
- `analytic_codebook_distortion(codebook: NDArray[np.float32], dimension: int) -> float`
- `bootstrap_mean_interval(block_means, *, rng, resamples=10_000, confidence=0.95) -> tuple[float, float]`
- `evaluate_algorithm_gates(result: QualificationResult) -> Sequence[GateResult]`

**Metric definitions:**
- Algorithm 1 per-pair error: `||x_hat - x||^2 / ||x||^2`.
- Algorithm 2 signed error: `estimate(q, x) - dot(q, x)`.
- Algorithm 2 normalized squared error: `signed_error^2 / (||q||^2 ||x||^2)`.
- Normalized signed bias: `signed_error / (||q|| ||x||)`.
- Paper targets for Algorithm 1 bits 1..4: `(0.36, 0.117, 0.03, 0.009)`.
- Paper targets for Algorithm 2 total bits 1..4: `(1.57/d, 0.56/d, 0.18/d, 0.047/d)`.
- The terminal R1 record has exactly five gates named `round_trip_determinism`, `mse_distortion`, `qjl_bias_equivalence`, `published_qjl_distortion`, and `author_code_differential`. Overall R1 status passes only when all five are present and true.

- [ ] **Step 1: Write failing unit tests with small deterministic batches**

```python
# tests/turboquant/test_qualification.py
import numpy as np

from hamutay.turboquant.qualification import (
    GateResult,
    QualificationConfig,
    QualificationMetrics,
    QualificationResult,
    bootstrap_mean_interval,
    evaluate_algorithm_gates,
    partition_block_ids,
)


def test_partition_block_ids_covers_each_sample_once():
    ids = partition_block_ids(sample_count=12, block_count=4)
    assert ids.tolist() == [0, 0, 0, 1, 1, 1, 2, 2, 2, 3, 3, 3]


def test_bootstrap_mean_interval_is_repeatable():
    values = np.arange(20, dtype=np.float64)
    first = bootstrap_mean_interval(values, rng=np.random.default_rng(7), resamples=2000)
    second = bootstrap_mean_interval(values, rng=np.random.default_rng(7), resamples=2000)
    assert first == second
    assert first[0] < values.mean() < first[1]


def test_values_inside_registered_gate_boundaries_pass():
    metrics = tuple(
        QualificationMetrics(
            bits=bits,
            mse_observed=1.0049,
            mse_analytic_target=1.0,
            mse_paper_target=1.0049 / 1.149,
            product_observed=1.149,
            product_paper_target=1.0,
            normalized_bias_mean=0.0,
            normalized_bias_rmse=0.1,
            normalized_bias_ci95=(-0.0001, 0.0001),
            normalized_bias_ci9875=(-0.00199, 0.00199),
        )
        for bits in (1, 2, 3, 4)
    )
    result = QualificationResult(metrics=metrics, determinism_passed=True)
    gates = evaluate_algorithm_gates(result)
    assert all(isinstance(gate, GateResult) for gate in gates)
    assert all(gate.passed for gate in gates)


def test_bias_gate_rejects_interval_outside_equivalence_region():
    metric = QualificationMetrics(
        bits=1,
        mse_observed=0.36,
        mse_analytic_target=0.36,
        mse_paper_target=0.36,
        product_observed=1.57 / 128,
        product_paper_target=1.57 / 128,
        normalized_bias_mean=0.0005,
        normalized_bias_rmse=0.1,
        normalized_bias_ci95=(-0.0005, 0.0015),
        normalized_bias_ci9875=(-0.001, 0.0021),
    )
    result = QualificationResult(metrics=(metric,), determinism_passed=True)
    gate = next(
        g for g in evaluate_algorithm_gates(result)
        if g.name == "qjl_bias_equivalence"
    )
    assert not gate.passed


def test_mse_gate_rejects_analytic_mismatch_even_when_paper_matches():
    metric = QualificationMetrics(
        bits=1,
        mse_observed=0.36,
        mse_analytic_target=0.35,
        mse_paper_target=0.36,
        product_observed=1.57 / 128,
        product_paper_target=1.57 / 128,
        normalized_bias_mean=0.0,
        normalized_bias_rmse=0.1,
        normalized_bias_ci95=(-0.0001, 0.0001),
        normalized_bias_ci9875=(-0.001, 0.001),
    )
    result = QualificationResult(metrics=(metric,), determinism_passed=True)
    gate = next(
        g for g in evaluate_algorithm_gates(result)
        if g.name == "mse_distortion"
    )
    assert not gate.passed
```

- [ ] **Step 2: Run the tests and observe failure**

Run: `uv run pytest tests/turboquant/test_qualification.py -v`

Expected: FAIL because `qualification.py` does not exist.

- [ ] **Step 3: Implement typed results and exact gates**

Use frozen slotted dataclasses whose fields match the test constructors. `GateResult` contains `name`, `passed`, `observed`, `threshold`, and `detail`. `QualificationResult` also retains per-bit block means for artifact serialization but excludes million-row raw vectors. Validate at construction that `sample_count`, `batch_size`, and `bootstrap_blocks` are positive, that `sample_count` is divisible by both `batch_size` and `bootstrap_blocks`, and that every requested bit width is in 1 through 4.

`partition_block_ids` forms exactly `block_count` contiguous blocks. Reject non-divisible registered inputs rather than creating a shorter final block. One million pairs become 1,000 blocks of 1,000 pairs. Bootstrap the 1,000 block means, not one million individual rows: for each of 10,000 resamples, sample 1,000 block indices with replacement and take their mean. Use an independently derived PCG64 stream for each metric, confidence level, and bit width; for example, the one-bit 98.75% bias stream's final seed fields are `qualification`, `bootstrap`, `bias`, `0.9875`, and `1`. Adding a diagnostic must not perturb another interval.

`analytic_codebook_distortion` reconstructs midpoint cell boundaries, integrates `(x - centroid)^2 * sphere_coordinate_density(x, dimension)` over every cell with the same FP64 quadrature tolerances as Task 2, sums the cells, and multiplies by `dimension`. This target comes from the frozen codebook rather than a second Lloyd-Max solve.

`run_synthetic_qualification` streams batches. Generate independent standard-Gaussian key and query vectors from distinct purpose-derived PCG64 generators. Build one registered rotation for Algorithm 1, one iid `(128,128)` paper-literal QJL projection, and one independently derived row-orthogonalized sensitivity projection. Scale the orthogonalized matrix by `sqrt(dimension)` so each row has norm `sqrt(dimension)`, matching the expected iid-Gaussian row norm used by the estimator. Accumulate FP64 sums and fixed block sums without retaining all vectors. Record paper-literal metrics as gates and orthogonalized metrics as non-gating sensitivity output.

The composite `mse_distortion` gate requires every bit width to satisfy both `abs(observed-analytic)/analytic <= 0.005` and `abs(observed-paper)/paper <= 0.15`. `published_qjl_distortion` retains `<= 0.15`. Report the ratio between each observed product distortion and the paper table separately; specifically call out the four-bit target's inherited rounding from the paper's three-bit scalar value without changing its gate.

For `qjl_bias_equivalence`, compute both ordinary 95% and Bonferroni-adjusted 98.75% block-bootstrap intervals. Every 98.75% interval must be contained in the closed interval `[-0.02 * rmse, +0.02 * rmse]`; inclusion of zero is not itself a gate. Determinism comes from Task 6's separate-process comparison. The author differential joins in Task 7; overall R1 status cannot become `passed` until all five named gates exist and pass.

- [ ] **Step 4: Add and run a reduced integration test**

Append tests that run `QualificationConfig(dimension=128, sample_count=20_000, batch_size=1000, bootstrap_blocks=100, bootstrap_resamples=200, bits=(1, 2))`, assert finite metrics, exact sample counts, both interval levels, and identical serialized results on two runs. Add a direct quadrature regression asserting the dimension-128 analytic values round to `(0.36089, 0.11600, 0.03397, 0.00931)` for bits 1 through 4. These are development consistency tests; the reduced synthetic run does not assert paper-scale gates.

Run: `uv run pytest tests/turboquant/test_qualification.py -v`

Expected: 7 PASS.

- [ ] **Step 5: Commit**

```bash
git add src/hamutay/turboquant/__init__.py src/hamutay/turboquant/qualification.py tests/turboquant/test_qualification.py
git -c user.email=hamutay@wamason.com -c user.name="Tony Mason" -c user.signingkey=01193FA2631C8AE8E4DF266E216D3C9B920813A1 commit -S -m "implement TurboQuant qualification statistics

Co-Authored-By: Codex <noreply@openai.com>"
```

---

### Task 6: Canonical, append-only evidence artifacts and CLI

**Files:**
- Create: `src/hamutay/turboquant/artifacts.py`
- Create: `src/hamutay/turboquant/qualify.py`
- Create: `src/hamutay/turboquant/qualify_worker.py`
- Create: `tests/turboquant/test_artifacts.py`
- Create: `tests/turboquant/test_qualify_cli.py`
- Modify: `pyproject.toml`
- Modify: `uv.lock` (project-script metadata only; no dependency changes)

**Interfaces:**
- Console command: `turboquant-qualify = "hamutay.turboquant.qualify:main"`
- `canonical_json_bytes(value: object) -> bytes`
- `sha256_file(path: Path) -> str`
- `create_run_directory(root: Path, run_id: str) -> Path`
- `run_registered_workers(run_directory: Path, config_path: Path, resolved_inputs_path: Path) -> tuple[Path, Path, Path]`
- CLI modes `--profile development|registered`, `--output-root`, and `--run-id`.

- [ ] **Step 1: Write failing artifact tests**

```python
# tests/turboquant/test_artifacts.py
import json

import pytest

from hamutay.turboquant.artifacts import canonical_json_bytes, create_run_directory


def test_canonical_json_is_sorted_compact_and_newline_terminated():
    encoded = canonical_json_bytes({"z": 1, "a": [2, 3]})
    assert encoded == b'{"a":[2,3],"z":1}\n'


def test_run_directory_refuses_overwrite(tmp_path):
    created = create_run_directory(tmp_path, "registered-001")
    assert created.is_dir()
    with pytest.raises(FileExistsError):
        create_run_directory(tmp_path, "registered-001")
```

```python
# tests/turboquant/test_qualify_cli.py
from hamutay.turboquant.qualify import build_parser


def test_registered_profile_freezes_all_scientific_counts():
    args = build_parser().parse_args(
        ["--profile", "registered", "--output-root", "out", "--run-id", "r1"]
    )
    assert args.dimension == 128
    assert args.sample_count == 1_000_000
    assert args.bootstrap_resamples == 10_000
    assert args.bits == (1, 2, 3, 4)


def test_registered_profile_rejects_count_overrides():
    parser = build_parser()
    try:
        parser.parse_args(
            ["--profile", "registered", "--output-root", "out", "--run-id", "r1", "--sample-count", "10"]
        )
    except SystemExit as error:
        assert error.code != 0
    else:
        raise AssertionError("registered sample count override accepted")


def test_registered_profile_uses_divisible_batch_size():
    args = build_parser().parse_args(
        ["--profile", "registered", "--output-root", "out", "--run-id", "r1"]
    )
    assert args.batch_size == 4000
    assert args.sample_count % args.batch_size == 0
```

- [ ] **Step 2: Run the focused tests and observe failure**

Run: `uv run pytest tests/turboquant/test_artifacts.py tests/turboquant/test_qualify_cli.py -v`

Expected: FAIL because the modules do not exist.

- [ ] **Step 3: Implement the artifact contract**

Canonical JSON uses `json.dumps(sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)` plus one newline. Array artifacts use uncompressed `np.savez` so their member arrays and whole-file hash can be inspected without codec-version ambiguity.

Each run directory contains:

```text
manifest.json
resolved_inputs.npz
execution-0.json
execution-1.json
execution-2.json
qualification.json
run.log
```

`manifest.json` includes run UUID/name, UTC start/end, profile, status, Git commit and dirty paths, study seed and derivation text, complete configuration, NumPy/SciPy/PyTorch/Python versions, CPU/platform, GPU/driver/CUDA data when available, rotation/codebook/projection hashes, and source-paper targets. `resolved_inputs.npz` contains the FP32 rotation, all codebooks, paper-literal projection, and orthogonalized sensitivity projection. `qualification.json` contains metrics, block-bootstrap intervals, every gate, declared loss/convention strings, artifact hashes, and either `passed`, `failed`, or `error`. `run.log` captures stage transitions and exceptions without becoming the source of record.

Create the directory before computation with a provisional manifest. On any exception, atomically write a terminal `qualification.json` with status `error`, then re-raise. Atomic creation means write a sibling temporary file, flush and `os.fsync`, then `os.replace`; replacement is allowed only for the provisional manifest within the same still-running directory. Once terminal status exists, every artifact is immutable.

- [ ] **Step 4: Write the failing separate-process test**

Append to `tests/turboquant/test_qualify_cli.py`:

```python
import subprocess
import sys
from pathlib import Path

from hamutay.turboquant.qualify import run_registered_workers


def test_registered_workers_are_three_fresh_processes(monkeypatch, tmp_path):
    calls: list[list[str]] = []

    def fake_run(command, *, check, env):
        assert check is True
        calls.append(command)
        output = Path(command[command.index("--output") + 1])
        output.write_text("{}\n", encoding="utf-8")

    monkeypatch.setattr(subprocess, "run", fake_run)
    outputs = run_registered_workers(
        tmp_path,
        tmp_path / "worker-config.json",
        tmp_path / "resolved_inputs.npz",
    )
    assert len(calls) == 3
    assert [
        command[command.index("--execution-index") + 1]
        for command in calls
    ] == ["0", "1", "2"]
    assert all(
        command[:3] == [sys.executable, "-m", "hamutay.turboquant.qualify_worker"]
        for command in calls
    )
    assert outputs == tuple(tmp_path / f"execution-{index}.json" for index in range(3))
```

Run: `uv run pytest tests/turboquant/test_qualify_cli.py::test_registered_workers_are_three_fresh_processes -v`

Expected: FAIL because `run_registered_workers` and `qualify_worker.py` do not exist.

- [ ] **Step 5: Implement the CLI and process-level determinism gate**

Development mode permits explicit counts and writes only under a caller-selected development root. Registered mode freezes dimension 128, sample count 1,000,000, batch size 4,000 (evenly dividing both sample and block boundaries), 1,000 bootstrap blocks, 10,000 resamples, and bits 1..4. It requires a clean worktree except for declared `--allow-dirty-path` entries; the registered execution below uses none.

The parent CLI constructs and freezes `resolved_inputs.npz`, then launches `sys.executable -m hamutay.turboquant.qualify_worker` three times sequentially through `subprocess.run(command, check=True, env=worker_env)`. Each child receives the same canonical worker configuration and resolved-input file plus a distinct execution index, reads rather than regenerates the frozen arrays, and writes exactly one immutable `execution-N.json`. Do not use multiprocessing workers that inherit the parent's initialized NumPy, BLAS, Torch, or CUDA state.

Each worker streams the registered inputs from newly constructed purpose-derived generators. Update SHA-256 incrementally with an explicit dtype string, shape encoded as unsigned 64-bit big-endian integers, and C-order bytes for every codes, signs, norms, and reconstruction-checkpoint batch. Hash terminal metric structures as canonical JSON. The determinism gate passes only if all corresponding stream and metric hashes match across the three process artifacts. Persist the three compact execution records, not million-row samples.

Add `turboquant-qualify` to `[project.scripts]` and verify `uv sync` leaves the lockfile unchanged; if `uv.lock` changes only because the project script metadata is regenerated, include it in this task's exact staging list.

- [ ] **Step 6: Run development verification**

```bash
uv run pytest tests/turboquant/test_artifacts.py tests/turboquant/test_qualify_cli.py -v
uv run turboquant-qualify --profile development --output-root experiments/turboquant/development --run-id plan-smoke --sample-count 20000 --batch-size 1000 --bootstrap-blocks 100 --bootstrap-resamples 200
```

Expected: tests PASS; smoke command creates one complete non-overwritable run with finite metrics and status that is explicitly non-certifying.

- [ ] **Step 7: Commit**

```bash
git add pyproject.toml uv.lock src/hamutay/turboquant/artifacts.py src/hamutay/turboquant/qualify.py src/hamutay/turboquant/qualify_worker.py tests/turboquant/test_artifacts.py tests/turboquant/test_qualify_cli.py
git -c user.email=hamutay@wamason.com -c user.name="Tony Mason" -c user.signingkey=01193FA2631C8AE8E4DF266E216D3C9B920813A1 commit -S -m "add append-only TurboQuant qualification artifacts

Co-Authored-By: Codex <noreply@openai.com>"
```

---

### Task 7: Pinned author-QJL CUDA differential

**Files:**
- Create: `scripts/turboquant/author_qjl_oracle.py`
- Create: `tests/turboquant/test_author_qjl.py`
- Modify: `src/hamutay/turboquant/qualify.py`
- Modify: `src/hamutay/turboquant/qualification.py`

**Pinned upstream contract:**
- Repository: `https://github.com/amirzandieh/QJL`
- Commit: `648b3641f96b6e95e091217220b94e4739fd4d82`
- License SHA-256: `c71d239df91726fc519c6eb72d318ec65820627232b2f796219e87dcf35d0ab4`
- `qjl_kernel/csrc/qjl_quant_kernel.cu` SHA-256: `d03b2fd86504554f48da48df2740d73a0cc2d1d8a28c22698da20c9ee801aefd`
- `qjl_kernel/csrc/qjl_score_kernel.cu` SHA-256: `848398bb6b140433aa10f4ccea16eb680ec215cb148956f09e46bbbdabdc030c`
- `models/llama3_utils_qjl.py` SHA-256: `725b6777b752e30b583b6834e258a849c01679c4e3c007f3b4c62212393f34c2`

**Compiler precondition:** This shell is WSL2 Ubuntu 22.04.5. PyTorch is built for CUDA 12.8 while the system toolkit is CUDA 13.2, so `torch.utils.cpp_extension.load` rejects the default compiler before invoking it. Install NVIDIA's WSL-Ubuntu repository metadata and only the versioned toolkit package; never install `cuda`, `cuda-12-8`, `cuda-runtime-12-8`, or `cuda-drivers` inside WSL.

Authoritative installation references: NVIDIA's [CUDA 12.8 Linux guide](https://docs.nvidia.com/cuda/archive/12.8.2/cuda-installation-guide-linux/index.html) and [CUDA 12.8 WSL-Ubuntu archive](https://developer.nvidia.com/cuda-12-8-0-download-archive?Distribution=WSL-Ubuntu&target_arch=x86_64&target_os=Linux&target_type=deb_local&target_version=2.0).

```bash
wget -O /tmp/cuda-keyring_1.1-1_all.deb https://developer.download.nvidia.com/compute/cuda/repos/wsl-ubuntu/x86_64/cuda-keyring_1.1-1_all.deb
sudo dpkg -i /tmp/cuda-keyring_1.1-1_all.deb
sudo apt-get update
sudo apt-get install -y cuda-toolkit-12-8
/usr/local/cuda-12.8/bin/nvcc --version
readlink -f /usr/local/cuda
```

Expected: `nvcc` reports release 12.8 and `/usr/local/cuda` still resolves to `/usr/local/cuda-13.2`. If the package changed the alternative, restore the CUDA 13.2 alternative before continuing and continue to select 12.8 only through per-command environment variables.

- [ ] **Step 1: Write the CUDA differential test first**

`tests/turboquant/test_author_qjl.py` must skip with a precise reason unless CUDA is available, `QJL_AUTHOR_CHECKOUT` names a checkout, `/usr/local/cuda-12.8/bin/nvcc` exists, and the selected compiler and `torch.version.cuda` both report 12.8. Once those preconditions exist, skipping is forbidden: verify `git rev-parse HEAD`, clean upstream status, and every hash before compilation.

The test uses 32 FP32 key residuals and one query of dimension 128. Set coordinate 127 of every key and the query exactly to zero. Supply an outlier-index tensor whose sole value is 127 and set `outlier_sketch_dim=8`. The mandatory author outlier channel then has zero norm and zero contribution while avoiding the kernel's division by zero; the inlier estimator is the paper-literal estimator on the active 127 coordinates.

Use a study-derived iid FP32 projection `S` with shape `(128,128)`. Pass `S` to the author quant kernel and `S.T.contiguous()` to the author score kernel, matching their opposite quant/score layouts. Compute the score kernel's required FP32 `query_sketch` argument as `query @ S.T`; the kernel also subtracts the dummy outlier contribution internally, which is exact zero because query coordinate 127 is zero. Give the kernel key shape `(1, 1, 1, 32, 128)`, outlier-index shape `(1, 1, 1, 1)`, query shape `(1, 1, 1, 128)`, and full key norms. Compile only the exact quant and score `.cu` files with separately named `torch.utils.cpp_extension.load` calls; do not import the repository wrapper, whose FP32 score dispatch contains the known `tcuda_qjl_score` typo.

The transparent reference maps exact zero projections to positive signs; the author kernel uses `sketched > 0` and therefore maps exact zero to negative signs. Assert that the registered generic inlier sketches contain no exact FP32 zero before byte comparison, and record both conventions in the differential artifact. Add a separate constructed zero-projection test that expects the known one-bit convention difference rather than treating it as author disagreement.

Assertions:

1. Author packed inlier sign bytes exactly equal `pack_signs(residual @ S.T)`.
2. Author returned dummy-outlier norms are exact zero.
3. Author scores match the transparent literal score within `atol=1e-5`, `rtol=1e-4`.
4. The test input, author outputs, transparent outputs, extension build names, upstream commit, and hashes are serializable for the registered evidence.

- [ ] **Step 2: Run RED without the checkout and confirm the controlled skip**

Run: `uv run pytest tests/turboquant/test_author_qjl.py -v`

Expected: one SKIP naming the missing `QJL_AUTHOR_CHECKOUT`, not an import or collection failure.

- [ ] **Step 3: Implement the oracle adapter without vendoring upstream code**

`scripts/turboquant/author_qjl_oracle.py` accepts `--checkout`, `--output`, and `--device cuda:0`. It verifies the pinned contract, builds the two extensions in PyTorch's content-addressed extension cache, constructs the exact differential batch, calls the FP32 entry points directly, compares outputs, and writes canonical JSON plus an NPZ of inputs/outputs. It exits nonzero on a convention or tolerance mismatch.

Extend the registered qualification CLI with required `--author-qjl-checkout`. Merge the oracle result as the fifth `author_code_differential` gate. Development mode may omit the checkout but must then report the gate as `not_run`, never passed.

- [ ] **Step 4: Clone the oracle outside the repository and run GREEN**

```bash
mkdir -p /tmp/hamutay-turboquant-author
git clone https://github.com/amirzandieh/QJL /tmp/hamutay-turboquant-author/QJL
git -C /tmp/hamutay-turboquant-author/QJL checkout 648b3641f96b6e95e091217220b94e4739fd4d82
CUDA_HOME=/usr/local/cuda-12.8 PATH=/usr/local/cuda-12.8/bin:$PATH QJL_AUTHOR_CHECKOUT=/tmp/hamutay-turboquant-author/QJL uv run pytest tests/turboquant/test_author_qjl.py -v
```

Expected: PASS on the local RTX 4090. If compilation or comparison fails, preserve the build/test output and repair the adapter or reference before proceeding; do not loosen the registered tolerance. A failure just above the absolute tolerance may arise from the kernel's FP32 warp-reduction order, but that explanation is a hypothesis to test, not an automatic waiver. Any tolerance revision requires a reviewed specification amendment before another registered differential.

- [ ] **Step 5: Run the whole development suite**

Run: `CUDA_HOME=/usr/local/cuda-12.8 PATH=/usr/local/cuda-12.8/bin:$PATH QJL_AUTHOR_CHECKOUT=/tmp/hamutay-turboquant-author/QJL uv run pytest tests/turboquant -v`

Expected: all tests PASS with no author-differential skip.

- [ ] **Step 6: Commit**

```bash
git add scripts/turboquant/author_qjl_oracle.py tests/turboquant/test_author_qjl.py src/hamutay/turboquant/qualify.py src/hamutay/turboquant/qualification.py
git -c user.email=hamutay@wamason.com -c user.name="Tony Mason" -c user.signingkey=01193FA2631C8AE8E4DF266E216D3C9B920813A1 commit -S -m "add pinned QJL author differential

Co-Authored-By: Codex <noreply@openai.com>"
```

---

### Task 8: Independent black-box adversarial validation

**Files:**
- Create: `tests/turboquant_independent/` (contents authored by the independent Claude instance, not by the implementer or this plan)
- Create: `docs/superpowers/reports/2026-08-27-turboquant-independent-validation.md`

**Independence protocol:** The principal investigator starts a fresh Claude session after Tasks 1-7 are committed. Before Claude reads any implementation file, provide only the approved specification, this plan's frozen public interfaces, the TurboQuant paper, the pinned author-QJL contract, and permission to create black-box tests beneath `tests/turboquant_independent/`. Claude freezes those tests in a separately signed commit. Only then may it inspect the implementation and explain failures. This task intentionally does not prescribe the test cases: doing so would make the implementer the independent-test author.

- [ ] **Step 1: Freeze the implementation under review**

Run:

```bash
git status --short
git rev-parse HEAD
CUDA_HOME=/usr/local/cuda-12.8 PATH=/usr/local/cuda-12.8/bin:$PATH QJL_AUTHOR_CHECKOUT=/tmp/hamutay-turboquant-author/QJL uv run pytest tests/turboquant -v
```

Expected: clean feature worktree, one recorded implementation commit, and every implementer-authored test passes with the author differential active.

- [ ] **Step 2: Have the independent Claude instance author and commit black-box tests before implementation access**

The test commit message records the implementation commit under review, the materials Claude received before test freeze, the fact that implementation access was withheld, and Claude's model identifier. Use the repository's Tony Mason signing identity and a Claude co-author trailer. Do not squash this commit into an implementation commit.

- [ ] **Step 3: Run the frozen independent suite without editing it**

Run:

```bash
CUDA_HOME=/usr/local/cuda-12.8 PATH=/usr/local/cuda-12.8/bin:$PATH QJL_AUTHOR_CHECKOUT=/tmp/hamutay-turboquant-author/QJL uv run pytest tests/turboquant_independent -v
```

Expected: all independently authored tests PASS. Preserve complete failing output before diagnosis if any test fails.

- [ ] **Step 4: Resolve findings through evidence rather than reviewer authority**

For each failed test or prose finding, the validation report records its identifier, whether it is accepted or rejected, the technical evidence, the resulting code/test/spec commit when accepted, and the principal investigator's disposition when rejected. Accepted implementation defects return to the relevant earlier task, receive a test-first repair commit, rerun both test suites, and invalidate the prior validation report. An invalid independent test is corrected by its author in a new signed commit; the original remains in history.

- [ ] **Step 5: Commit the terminal validation report**

The report includes the frozen implementation commit, independent-test commit, complete commands and outcomes, every disposition, and terminal status `passed` or `blocked`. Registered execution is permitted only for `passed`.

```bash
git add docs/superpowers/reports/2026-08-27-turboquant-independent-validation.md
git -c user.email=hamutay@wamason.com -c user.name="Tony Mason" -c user.signingkey=01193FA2631C8AE8E4DF266E216D3C9B920813A1 commit -S -m "record independent TurboQuant validation

Co-Authored-By: Codex <noreply@openai.com>"
```

---

### Task 9: Execute, inspect, and timestamp the registered R1 gate

**Files:**
- Create: `experiments/turboquant/qualification/r1-initial/manifest.json`
- Create: `experiments/turboquant/qualification/r1-initial/resolved_inputs.npz`
- Create: `experiments/turboquant/qualification/r1-initial/execution-0.json`
- Create: `experiments/turboquant/qualification/r1-initial/execution-1.json`
- Create: `experiments/turboquant/qualification/r1-initial/execution-2.json`
- Create: `experiments/turboquant/qualification/r1-initial/qualification.json`
- Create: `experiments/turboquant/qualification/r1-initial/run.log`
- Create: `docs/superpowers/reports/2026-08-27-turboquant-r1-qualification.md`

**Precondition:** Tasks 1-8 are committed in the isolated feature worktree; the independent-validation report status is `passed`; and both test suites pass with the pinned author checkout. That feature worktree is clean before beginning the registered run; unrelated changes in the user's original checkout remain untouched.

- [ ] **Step 1: Record the pre-run state**

Run:

```bash
git status --short
git rev-parse HEAD
nvidia-smi --query-gpu=name,uuid,driver_version,memory.total --format=csv,noheader
/usr/local/cuda-12.8/bin/nvcc --version
uv run python -c "import numpy, scipy, torch; print(numpy.__version__, scipy.__version__, torch.__version__, torch.version.cuda, torch.cuda.get_device_name(0))"
CUDA_HOME=/usr/local/cuda-12.8 PATH=/usr/local/cuda-12.8/bin:$PATH QJL_AUTHOR_CHECKOUT=/tmp/hamutay-turboquant-author/QJL uv run pytest tests/turboquant tests/turboquant_independent -v
```

Expected: clean Git status; an RTX 4090 is visible; the environment details match what the manifest will capture. Stop on a dirty tree or hash mismatch.

- [ ] **Step 2: Run the exact registered command**

Use the frozen first-run identifier `r1-initial`. The manifest's UTC start time and Git commit disambiguate the execution. If this run fails and code is repaired, revise this plan with the new explicit run identifier before executing the repair; append-only evidence forbids reusing `r1-initial`.

```bash
CUDA_HOME=/usr/local/cuda-12.8 PATH=/usr/local/cuda-12.8/bin:$PATH uv run turboquant-qualify \
  --profile registered \
  --output-root experiments/turboquant/qualification \
  --run-id r1-initial \
  --author-qjl-checkout /tmp/hamutay-turboquant-author/QJL
```

Expected: one terminal run directory, all five qualification gates present, and process exit zero only if every gate passes. A nonzero exit is retained as valid failed qualification evidence.

- [ ] **Step 3: Independently verify artifacts**

Run:

```bash
uv run python -m json.tool experiments/turboquant/qualification/r1-initial/manifest.json >/dev/null
uv run python -m json.tool experiments/turboquant/qualification/r1-initial/qualification.json >/dev/null
sha256sum experiments/turboquant/qualification/r1-initial/*
CUDA_HOME=/usr/local/cuda-12.8 PATH=/usr/local/cuda-12.8/bin:$PATH QJL_AUTHOR_CHECKOUT=/tmp/hamutay-turboquant-author/QJL uv run pytest tests/turboquant tests/turboquant_independent -v
```

Expected: valid JSON, stable hashes, and full tests PASS with the author differential active. Compare reported scalar/product relative errors and bias conditions manually against the five frozen gate definitions; do not rely solely on the top-level status boolean.

- [ ] **Step 4: Write the qualification report**

The report gives the exact run ID and artifact hashes; a compact empirical-versus-analytic-versus-paper table for all scalar bit widths; observed versus published QJL distortion; normalized bias mean, RMSE, ordinary 95% interval, and simultaneous 98.75% interval; three process-execution hashes; author differential maximum absolute/relative error; independent-validation commit; every gate status; runtime and hardware; declared deviations; and one conclusion from the approved outcome vocabulary. If any gate failed, title the conclusion `No qualified experiment` and state that the model harness remains blocked. If all pass, state only that R1 passed and the model-level implementation plan may now be written; do not claim any cache-path result.

- [ ] **Step 5: Commit evidence and report exactly**

```bash
git add experiments/turboquant/qualification/r1-initial/manifest.json experiments/turboquant/qualification/r1-initial/resolved_inputs.npz experiments/turboquant/qualification/r1-initial/execution-0.json experiments/turboquant/qualification/r1-initial/execution-1.json experiments/turboquant/qualification/r1-initial/execution-2.json experiments/turboquant/qualification/r1-initial/qualification.json experiments/turboquant/qualification/r1-initial/run.log docs/superpowers/reports/2026-08-27-turboquant-r1-qualification.md
git -c user.email=hamutay@wamason.com -c user.name="Tony Mason" -c user.signingkey=01193FA2631C8AE8E4DF266E216D3C9B920813A1 commit -S -m "record TurboQuant R1 qualification

Co-Authored-By: Codex <noreply@openai.com>"
```

- [ ] **Step 6: Verify signed history and OpenTimestamps stamp**

Run:

```bash
git log --show-signature -4 --oneline
git status --short
```

Expected: the evidence commit has a good signature, the hook-created OTS commit follows it, and no task-owned files remain uncommitted. Unrelated pre-existing user files may still appear and must remain untouched.

---

## Completion and Next Gate

This plan is complete only when Tasks 1-8 are implemented and Task 9 has left immutable, signed, timestamped R1 evidence, whether passing or failing. A passing R1 result authorizes writing—not silently executing—the second plan for model baseline qualification, the cache-path harness, fixed-length Q schedules, replay/eviction controls, and the registered numerical/behavioral assay. A failed R1 result blocks that plan until the implementation is repaired and the complete qualification is rerun under a new run ID.
