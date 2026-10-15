# TurboQuant R1: public interface contract

Extracted mechanically from the qualification plan by
`scripts/turboquant/build_sanitized_bundle.py`. This contains the
public names, signatures, and declared conventions the independent
validator may rely on.

Every fenced code block in the source plan was dropped, including
inside otherwise-permitted sections: embedded test code is the
contamination vector that invalidated the first validation round
(finding F5). No prescribed test case, implementation-guidance step,
or command from the plan appears here.

## Task 1: Package skeleton, study seed, and canonical rotations

- `STUDY_SEED_HEX = "0b311d5d4eceaf773efde389305a1b5a"`
- `derive_seed(*fields: str | int, study_seed_hex: str = STUDY_SEED_HEX) -> int`
- `rng_for(*fields: str | int) -> numpy.random.Generator`
- `canonical_qr(matrix: NDArray[np.float64]) -> NDArray[np.float64]`
- `gaussian_rotation(dimension: int, *seed_fields: str | int) -> NDArray[np.float32]`


## Task 2: Dimension-specific spherical Lloyd-Max codebooks

- `sphere_coordinate_density(x: float | NDArray, dimension: int) -> float | NDArray`
- `lloyd_max_codebook(dimension: int, bits: int, *, tolerance: float = 1e-12, max_iterations: int = 10_000) -> NDArray[np.float32]`
- `nearest_code_indices(values: NDArray[np.float32], codebook: NDArray[np.float32]) -> NDArray[np.uint8]`


## Task 3: Algorithm 1 MSE quantization and frozen representation


- Frozen slotted dataclass `MSECodes(indices: np.ndarray, norms: np.ndarray)`, where indices are `uint8` with the vectors' full shape and norms are FP32 with the final vector dimension removed.
- `MSEQuantizer(rotation: np.ndarray, codebook: np.ndarray)`
- `MSEQuantizer.quantize(vectors: np.ndarray) -> MSECodes`
- `MSEQuantizer.dequantize(codes: MSECodes) -> np.ndarray`


## Task 4: Algorithm 2 product estimator and bit packing


- Frozen slotted dataclass `ProductCodes(mse: MSECodes, packed_signs: np.ndarray, residual_norms: np.ndarray)`. Packed signs are `uint8` with final length `ceil(sketch_dim / 8)`; residual norms are FP32 with the vector dimension removed.
- `ProductQuantizer(mse_quantizer: MSEQuantizer, projection: np.ndarray)`
- `ProductQuantizer.quantize(vectors: np.ndarray) -> ProductCodes`
- `ProductQuantizer.dequantize(codes: ProductCodes) -> np.ndarray`
- `ProductQuantizer.estimate_inner_products(queries: np.ndarray, codes: ProductCodes) -> np.ndarray`
- `pack_signs(signs: np.ndarray) -> np.ndarray`
- `unpack_signs(packed: np.ndarray, sketch_dim: int) -> np.ndarray`


## Task 5: Streaming R1 statistics, bootstrap, and gate evaluation

- `QualificationConfig(dimension=128, sample_count=1_000_000, batch_size=4000, bootstrap_blocks=1000, bootstrap_resamples=10_000, bits=(1,2,3,4))`
- `run_synthetic_qualification(config: QualificationConfig) -> QualificationResult`
- `analytic_codebook_distortion(codebook: NDArray[np.float32], dimension: int) -> float`
- `bootstrap_mean_interval(block_means, *, rng, resamples=10_000, confidence=0.95) -> tuple[float, float]`
- `evaluate_algorithm_gates(result: QualificationResult) -> Sequence[GateResult]`

- Algorithm 1 per-pair error: `||x_hat - x||^2 / ||x||^2`.
- Algorithm 2 signed error: `estimate(q, x) - dot(q, x)`.
- Algorithm 2 normalized squared error: `signed_error^2 / (||q||^2 ||x||^2)`.
- Normalized signed bias: `signed_error / (||q|| ||x||)`.
- Paper targets for Algorithm 1 bits 1..4: `(0.36, 0.117, 0.03, 0.009)`.
- Paper targets for Algorithm 2 total bits 1..4: `(1.57/d, 0.56/d, 0.18/d, 0.047/d)`.
- The terminal R1 record has exactly five gates named `round_trip_determinism`, `mse_distortion`, `qjl_bias_equivalence`, `published_qjl_distortion`, and `author_code_differential`. Overall R1 status passes only when all five are present and true.


## Task 6: Canonical, append-only evidence artifacts and CLI

- Console command: `turboquant-qualify = "hamutay.turboquant.qualify:main"`
- `canonical_json_bytes(value: object) -> bytes`
- `sha256_file(path: Path) -> str`
- `create_run_directory(root: Path, run_id: str) -> Path`
- `run_registered_workers(run_directory: Path, config_path: Path, resolved_inputs_path: Path) -> tuple[Path, Path, Path]`
- CLI modes `--profile development|registered`, `--output-root`, and `--run-id`.


## Task 7: Pinned author-QJL CUDA differential

- Repository: `https://github.com/amirzandieh/QJL`
- Commit: `648b3641f96b6e95e091217220b94e4739fd4d82`
- License SHA-256: `c71d239df91726fc519c6eb72d318ec65820627232b2f796219e87dcf35d0ab4`
- `qjl_kernel/csrc/qjl_quant_kernel.cu` SHA-256: `d03b2fd86504554f48da48df2740d73a0cc2d1d8a28c22698da20c9ee801aefd`
- `qjl_kernel/csrc/qjl_score_kernel.cu` SHA-256: `848398bb6b140433aa10f4ccea16eb680ec215cb148956f09e46bbbdabdc030c`
- `models/llama3_utils_qjl.py` SHA-256: `725b6777b752e30b583b6834e258a849c01679c4e3c007f3b4c62212393f34c2`


## Declared numerical and representation conventions

- Registered dimension is 128. Inputs are arbitrary nonzero vectors: normalize before applying a spherical quantizer and restore the original norm on reconstruction.
- A zero vector has norm zero, all-zero MSE indices, zero residual norm, and exact-zero reconstruction. Its *raw projected values* are zero; its *encoded sign bits* are not. See the sign encoding below.
- Vectors are rows. Rotation is `y = x @ rotation.T`; inverse rotation is `x_hat = y_hat @ rotation`. QJL projections are stored as rows, so a batch sketch is `residual @ projection.T`.
- In the transparent reference every zero sign maps to `+1`. The pinned author kernel maps exact zero to `-1`; this is a declared, documented convention difference, not a defect.
- Bit packing is little-endian within each byte: sketch coordinate `j` occupies bit `j % 8` of byte `j // 8`. A set bit decodes to FP32 `+1` and a clear bit to `-1`. Because a zero projected value maps to `+1`, a zero vector's packed sign bytes have every in-range bit SET, not cleared; only unused high bits of the final byte are zero. What remains all-zero for a zero vector is the indices and the norms, and the zero norm is what forces exact-zero reconstruction.
- `derive_seed` wire format: SHA-256 over the UTF-8 string formed by joining the study seed and the given fields with `|`, taking the first 16 bytes as an unsigned big-endian integer. Integer fields serialize as unpadded base-10.
- A `b`-bit product quantizer contains a `b-1`-bit Algorithm 1 codebook plus its fixed QJL sketch and residual norm. Total bits 1 through 4 therefore use 0- through 3-bit MSE codebooks.
- `nearest_code_indices` resolves an exact midpoint tie to the lower centroid.
- `estimate_inner_products` requires paired query/key leading shapes and does not broadcast them; mismatched leading shapes are rejected.
- Rotations and codebooks are constructed in FP64 and frozen as FP32. Quantization, reconstruction, and diagnostic reductions are FP32 unless otherwise stated.


## Public result types

The gate-evaluation API consumes and returns declared types. Field names and roles are public contract; no worked values are given.

- `QualificationMetrics` carries, per bit width: `bits`, `mse_observed`, `mse_analytic_target`, `mse_paper_target`, `product_observed`, `product_paper_target`, `normalized_bias_mean`, `normalized_bias_rmse`, `normalized_bias_ci95`, `normalized_bias_ci9875`, `sample_count`, `product_mse_bits`, `product_analytic_target`, `sensitivity_product_observed`, `sensitivity_normalized_bias_mean`, `sensitivity_normalized_bias_rmse`, `sensitivity_normalized_bias_ci95`, `sensitivity_normalized_bias_ci9875`, `mse_block_means`, `product_block_means`, `normalized_bias_block_means`, `sensitivity_product_block_means`, and `sensitivity_bias_block_means`. Interval fields are `(low, high)` pairs. The `sensitivity_*` fields carry the declared row-orthogonalized projection arm, which is reported and does not gate. The `*_block_means` fields carry block-bootstrap evidence.
- `QualificationResult` carries `metrics` (a sequence of `QualificationMetrics`), `determinism_passed`, `sample_count`, `batch_size`, `bootstrap_blocks`, `bootstrap_resamples`, `dimension`, and `configuration`.
- `GateResult` carries `name`, `passed`, `observed`, `threshold`, `detail`, and `status`. **Every** gate carries `status`, not only the author differential; it resolves to `passed`, `failed`, or `not_run`, the last used for the author differential when the checkout is omitted in development mode.
- `partition_block_ids(sample_count, block_count)` forms contiguous equal blocks and rejects non-divisible inputs.


## Import locations and constructor declarations

- Numerical functions and types in Tasks 1 through 5, including `partition_block_ids`, are exported by `hamutay.turboquant`. Their defining modules are `seeding`, `rotation`, `codebook`, `mse`, `product`, and `qualification` under that package. Task 6 artifact functions are in `hamutay.turboquant.artifacts`; `run_registered_workers` and `main` are in `hamutay.turboquant.qualify`.
- `QualificationConfig` is a frozen slotted dataclass. Its dimension, sample_count, batch_size, bootstrap_blocks, and bootstrap_resamples fields are integers; bits is `tuple[int, ...]`. Defaults appear in Task 5 above.
- `QualificationMetrics` is a frozen slotted dataclass. Required fields, in constructor order, are `bits: int`, then the float fields `mse_observed`, `mse_analytic_target`, `mse_paper_target`, `product_observed`, `product_paper_target`, `normalized_bias_mean`, `normalized_bias_rmse`, then `normalized_bias_ci95` and `normalized_bias_ci9875`, each `tuple[float, float]`. Optional fields are `sample_count: int = 0`, `product_mse_bits: int = 0`; `product_analytic_target`, `sensitivity_product_observed`, `sensitivity_normalized_bias_mean`, and `sensitivity_normalized_bias_rmse` are floats defaulting to 0.0; the two sensitivity interval fields default to `(0.0, 0.0)`; all five block-means fields are `tuple[float, ...] = ()`.
- `QualificationResult` is a frozen slotted dataclass with required `metrics: tuple[QualificationMetrics, ...]`, then `determinism_passed: bool = False`; its sample_count, batch_size, bootstrap_blocks, bootstrap_resamples, and dimension are integers defaulting to zero; `configuration: QualificationConfig | None = None`.
- `GateResult` is a frozen slotted dataclass with required fields `name: str`, `passed: bool`, `observed: Any`, `threshold: Any`, `detail: str`, then `status: str | None = None`. An omitted status is resolved from passed at construction.


## Public CLI and evidence behavior

Stated as behavior, not implementation.

- Registered mode freezes the declared scientific counts and rejects any attempt to override them. Development mode may accept explicit counts and is non-certifying.
- Options are `--profile`, `--output-root`, `--run-id`, `--dimension`, `--sample-count`, `--batch-size`, `--bootstrap-blocks`, `--bootstrap-resamples`, `--bits`, `--author-qjl-checkout`, and `--allow-dirty-path`. Registered mode requires a clean worktree except for declared dirty paths.
- `--bits` takes comma-separated integers; `--allow-dirty-path` is repeatable.
- Output namespaces are enforced before a run directory is created: development output must be at or beneath `experiments/turboquant/development`, registered output at or beneath `experiments/turboquant/qualification`. An otherwise valid temporary output root is rejected.
- A successfully completed run directory contains `manifest.json`, `resolved_inputs.npz`, `execution-0.json`, `execution-1.json`, `execution-2.json`, `qualification.json`, and `run.log`. All five gates and the terminal status appear in `qualification.json`. Evidence schema identifiers are `hamutay.turboquant.manifest.v2`, `hamutay.turboquant.execution.v1`, and `hamutay.turboquant.qualification.v2`.
- An error run may retain only partial artifacts and an incomplete gate set; it cannot certify R1.
- A development run without an author checkout reports `author_code_differential` as `not_run` and is non-certifying. Its terminal status tracks the four completed core gates, and a completed development run exits zero whether that status is `passed` or `failed`.
- Evidence is append-only: creating a run directory that already exists is refused. Terminal status is one of `passed`, `failed`, or `error`.
- Registered exit success is possible only when all five named gates are present and pass.
- Canonical JSON is sorted, compact, non-ASCII-preserving, newline-terminated, and rejects non-finite floats.


## Author CUDA adapter public boundary

- The standalone entry point is `scripts/turboquant/author_qjl_oracle.py`. It requires `--checkout` (pinned author repository) and `--output` (artifact directory); `--device` defaults to `cuda:0`, the only supported device spelling. It writes `author_qjl_differential.json` and `author_qjl_differential.npz` in that directory, with JSON schema `hamutay.turboquant.author-qjl.v1`, refuses existing evidence, and exits zero only when its status is passed.
- Public adapter functions are `verify_pinned_checkout(checkout: Path)`, `preflight_author_qjl(*, checkout: Path, device: str = 'cuda:0')`, and `run_author_qjl_differential(*, checkout: Path, output: Path, device: str = 'cuda:0')`; each returns `dict[str, Any]`.
- Execution requires available CUDA, PyTorch reporting CUDA 12.8, CUDA_HOME resolving to `/usr/local/cuda-12.8`, PATH selecting `/usr/local/cuda-12.8/bin/nvcc`, and that compiler reporting 12.8. The system `/usr/local/cuda` must continue resolving to `/usr/local/cuda-13.2`. The checkout must be clean at the pinned commit, with the declared origin and file hashes. Preconditions are verified before compilation; missing prerequisites are errors, not successful differential evidence.


## Registered CLI requirement (Task 7)

- The registered profile requires `--author-qjl-checkout`. Development mode may omit it and must then report the `author_code_differential` gate as not-run, never as passed.
- The terminal R1 record has exactly five gates named `round_trip_determinism`, `mse_distortion`, `qjl_bias_equivalence`, `published_qjl_distortion`, and `author_code_differential`. `evaluate_algorithm_gates` returns the first four; the fifth is joined at the CLI/evidence layer.
