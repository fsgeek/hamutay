# Public evidence schemas and boundary constraints

Declarative supplement to the sanitized public interface contract. JSON tuples serialize as arrays; SHA-256 values are lowercase hexadecimal strings.

## Author adapter return values

`verify_pinned_checkout(checkout: Path) -> dict[str, Any]` returns an object with `repository: str`, `origin: str`, `commit: str`, `clean: bool`, and `sha256: dict[str, str]`. The hash map uses the four already-declared upstream relative filenames. Accepted origin spellings are the declared HTTPS repository URL with or without the `.git` suffix. This function returns only after commit, cleanliness, origin, regular-file/non-symlink status, and pinned hashes have been verified. Its failure interface is exceptions, not a failed result object; failures from filesystem and Git subprocess operations can propagate, including `subprocess.CalledProcessError`.

`preflight_author_qjl(*, checkout: Path, device: str = 'cuda:0') -> dict[str, Any]` returns exactly `environment` and `upstream`; it has no `status` field. `upstream` has the preceding checkout schema. `environment` contains `cuda_home`, `default_cuda`, `default_cuda_resolved`, `device`, `device_name`, `nvcc`, `nvcc_release`, `nvcc_version`, `torch`, and `torch_cuda` strings, plus `device_compute_capability: list[int]` containing major and minor numbers. Failure is an exception, not a returned failure status. No compilation occurs in preflight.

`run_author_qjl_differential` returns the same object serialized to `author_qjl_differential.json`. Its top-level fields are:

- `schema: str`, fixed to `hamutay.turboquant.author-qjl.v1`.
- `status: str`, either `passed` or `failed`.
- `study_seed_hex: str`; `seed_fields: dict[str, list[str | int]]` with `keys`, `query`, and `projection` identifying the recorded random streams.
- `environment` and `upstream`, as above.
- `extensions: dict[str, str]`, with `quant` and `score` extension identifiers.
- `batch`: `dimension: int`, `key_shape: list[int]`, `query_shape: list[int]`, `outlier_index_shape: list[int]`, and `outlier_sketch_dim: int`.
- `conventions`: string fields `transparent_exact_zero_sign`, `author_exact_zero_sign`, `bit_packing`, `quant_projection_layout`, `score_projection_layout`, and `query_sketch` describing the declared layouts and signs.
- `comparisons`, `gate`, `arrays`, and `npz`, defined below.

`comparisons` contains `generic_projection_has_no_exact_zero: bool`, `inlier_sign_bytes_equal: bool`, `dummy_outlier_norms_exact_zero: bool`, `scores`, and `constructed_zero_projection`.

`scores` contains `atol: float`, `rtol: float`, `max_absolute_error: float`, `max_relative_error: float | null`, and `within_tolerance: bool`. The frozen tolerances are `atol=1e-5` and `rtol=1e-4`. Agreement means the elementwise combined bound `abs(author - reference) <= atol + rtol * abs(reference)` for every score, with NaNs unequal. It does not mean two independent bounds on the two reported maxima. A nonzero difference at a zero reference makes `max_relative_error` null; otherwise zero-reference exact matches contribute zero to the relative diagnostic.

`constructed_zero_projection` contains `author_byte: int`, `transparent_byte: int`, `differing_bits_per_byte: int`, and `expected_declared_difference: bool`. These describe the already-declared exact-zero sign-convention difference. The author differential passes exactly when inlier bytes agree, dummy outlier norms are exact zero, scores satisfy the combined tolerance, and the declared exact-zero convention difference is observed.

The adapter's nested `gate` contains `name`, `passed`, `observed`, `threshold`, and `detail`; it does not contain `status`. Its name is `author_code_differential`; `threshold` contains `atol` and `rtol`; `observed` contains `inlier_sign_bytes_equal`, `max_absolute_score_error`, `max_relative_score_error`, and `outlier_norms_exact_zero`. The CLI converts this record to a `GateResult` with its own resolved `status`. Do not confuse the adapter gate schema with the terminal gate schema.

`npz` contains `filename: str` and `sha256: str`, binding the standalone NPZ file bytes. `arrays` maps each NPZ member name to `dtype: str` (NumPy dtype string), `shape: list[int]`, `sha256: str` (the typed array hash described below), and `values` (nested JSON numbers). The exact NPZ member names and roles are:

| Name | Role / dimensions |
|---|---|
| `keys` | FP32 input key vectors, final dimension `batch.dimension`, shape `batch.key_shape` |
| `queries` | FP32 query vectors, shape `batch.query_shape` |
| `projection` | FP32 sketch projection, rows are sketch coordinates; square `dimension × dimension` |
| `outlier_indices` | uint8 coordinate-selection metadata, shape `batch.outlier_index_shape` |
| `key_norms` | FP32 full key norms, key shape without its vector dimension |
| `query_sketch` | FP32 projected queries, same leading dimensions as queries and one coordinate per projection row |
| `transparent_inlier_sign_bytes`, `author_inlier_sign_bytes` | uint8 packed inlier sketches associated with keys |
| `author_outlier_signs` | uint8 packed outlier-channel sketches associated with keys |
| `author_outlier_norms` | FP32 outlier-channel norms associated with keys |
| `transparent_scores`, `author_scores` | FP32 paired query/key score outputs, with author-kernel score layout recorded in `arrays.*.shape` |
| `zero_projection` | FP32 projection with the same shape as `projection`, for the declared exact-zero convention record |
| `zero_author_inlier_sign_bytes`, `zero_transparent_inlier_sign_bytes` | uint8 packed inlier sketches under `zero_projection` |

The `arrays` records are the authoritative concrete shapes/dtypes for kernel-produced tensors. No assumption that score tensors have the same rank/order as key tensors is warranted. All array members have corresponding JSON records. The standalone adapter refuses either preexisting output artifact; environmental or execution exceptions need not produce completed artifacts.

## CLI normal terminal evidence

The terminal status key is `status`, never `terminal_status`. A completed development evaluation returns exit code zero for either `passed` or `failed`; it remains non-certifying. With an author checkout its terminal decision includes all five gates; without one its author gate is `not_run` and the decision uses the four core gates. Registered execution requires all five passing gates for exit zero and R1 certification. Parser/validation refusals can raise `SystemExit` through public `main`; they are process exit failures through the console command.

`certification` contains `scope: str` (`development` or `r1`), `certifying: bool`, and `reason: str`. Human-readable reason/detail text is explanatory, not an enumerated schema value.

`manifest.json`, schema `hamutay.turboquant.manifest.v2`, normally contains:

- `run_id`, `run_uuid`, `started_at_utc`, `ended_at_utc`, `profile`, `status`, and `certification`.
- `author_qjl_checkout: str | null`; `author_qjl_preflight`, either the preflight object or `not_run` in a completed run.
- `configuration`: the six `QualificationConfig` fields, with `bits` a JSON array.
- `configuration_sha256`: SHA-256 of canonical JSON bytes of `configuration`.
- `worker_configuration_sha256`: SHA-256 of canonical JSON bytes of the worker configuration object, which has `schema='hamutay.turboquant.worker-config.v1'`, `configuration`, and `resolved_inputs_sha256`. This hash differs in meaning from `configuration_sha256`.
- `provenance`: `git_commit: str`, `dirty_paths: list[str]`, `allowed_dirty_paths: list[str]`, `repository: str`, `source_sha256: dict[str, str]` keyed by repository-relative implementation source paths.
- `study`: `seed_hex: str`, `seed_derivation: str`.
- `software`: version strings `python`, `numpy`, `scipy`, `torch`.
- `platform`: `cpu` metadata (`count`, `machine`, `processor`, `platform`) and `accelerators` metadata (`cuda_available`, `torch_cuda_version`, `driver_query`, `gpus`). GPU records contain `index`, `name`, `total_memory_bytes`, `compute_capability`, `uuid`; absence of CUDA permits an empty GPU list.
- `resolved_inputs`: `filename`, `file_sha256`, and `array_sha256` (member-name to typed-array hash).
- `source_paper_targets`: mappings `mse` and `qjl_numerator`, keyed by decimal bit-width strings.
- `numerical_conventions` and `declared_losses`: descriptive metadata.
- `author_code_differential`: `not_run`, or a summary object containing `status`, `upstream`, `extensions`, and `npz_sha256`.
- `artifact_sha256`: filename-to-file-hash map of non-hidden regular run artifacts excluding `manifest.json` and `qualification.json`.

`resolved_inputs.npz` contains FP32 `rotation`, `paper_projection`, and `sensitivity_projection`, each shaped `(dimension, dimension)`, plus `codebook_bits_b` for every requested scalar bit width and every requested product bit width minus one. Each codebook has shape `(2**b,)`. These are immutable shared worker inputs.

Each `execution-i.json`, schema `hamutay.turboquant.execution.v1`, contains `status`, `execution_index`, `configuration_sha256`, `resolved_inputs_sha256`, `provenance`, `stdout`, and `stderr`. Here `configuration_sha256` refers to the worker configuration object, not the manifest's plain configuration hash. `provenance` contains `pid`, `parent_pid`, and `worker_environment` (environment-name to string-or-null map). Successful execution adds `determinism_payload` and `determinism_payload_sha256`. The payload contains `metrics` (full serialized metrics records), `metric_sha256` (canonical JSON hash of that list), and `stream_sha256` (typed-array-stream hashes). Error execution instead may contain `error` with `type`, `message`, and `traceback`, and null input hashes if unavailable.

Stream keys are `synthetic.keys`, `synthetic.queries`; `algorithm_1.bits_b.codes`, `.norms`, `.reconstruction`; and `algorithm_2.paper.bits_b` / `algorithm_2.sensitivity.bits_b` followed by `.codes`, `.norms`, `.signs`, `.residual_norms`, or `.reconstruction`. These bind the corresponding full batched streams. Execution records have differing indices and process IDs; whole-file equality is not the determinism criterion. The declared comparison removes only `execution_index` and `provenance.pid`, retaining all other evidence; three distinct child PIDs share the launching parent. Canonical payloads and their hashes agree.

`qualification.json`, schema `hamutay.turboquant.qualification.v2`, normally contains `run_id`, `profile`, `status`, `certification`, `metrics`, `gates`, `author_code_differential`, `process_determinism`, `declared_losses`, `numerical_conventions`, and `artifact_sha256`. `metrics` is the full serialized metrics list. `gates` contains the five declared `GateResult` records in declared order, including `status` on every record. `process_determinism` contains `canonical_payload_sha256`, `execution_indices`, `passed`, and `worker_pids`. `author_code_differential` is either `not_run` or the full adapter JSON object above. The CLI retains that full object's arrays/values in qualification JSON; it does not retain separate standalone author JSON/NPZ files in the run directory. The embedded NPZ hash identifies the adapter's temporary NPZ, not a promised additional run artifact.

Qualification's `artifact_sha256` equals the manifest's map with the final `manifest.json` hash added. Neither map includes `qualification.json`; the manifest does not contain its own hash. The run log is finalized before normal terminal artifact hashing. Error runs can have partial artifacts, empty metrics, incomplete gates, null process determinism, and additional `error` / `recovery_errors` fields. Manifest/qualification terminal statuses agree when both terminal artifacts are published. Pre-run refusals need not create a run directory.

## Typed array hash wire format

Public `hamutay.turboquant.artifacts.sha256_array(name, values)` binds one array; `ArrayStreamHasher` binds ordered labeled batches. Both initialize SHA-256 with the bytes of `hamutay.turboquant.array-stream.v1` followed by a NUL byte. Each array contributes: a UTF-8 label prefixed by its unsigned 64-bit big-endian byte length; an ASCII NumPy `dtype.str` prefixed the same way; unsigned 64-bit big-endian rank; each shape extent as unsigned 64-bit big-endian; and contiguous C-order array data bytes. The stream form concatenates these contributions in update order. Labels must be nonempty strings, and object dtype is rejected. File hashes separately bind complete file bytes.

## Public constructor and numerical constraints

`hamutay.turboquant.qualification.author_code_differential_gate(oracle_result: Mapping[str, Any] | None) -> GateResult` is a public function in the qualification module, not a package-top-level re-export. None produces the author gate with `passed=False`, `status='not_run'`, `observed='not_run'`, and threshold `{'atol': 1e-5, 'rtol': 1e-4}`. A non-None value must be a mapping containing a `gate` mapping with name `author_code_differential`, a Python Boolean `passed`, the exact frozen threshold mapping, and nonempty string `detail`. The outer `status` must be `passed` when gate.passed is true and `failed` otherwise. Invalid records raise ValueError. The returned GateResult copies nested gate `observed` (or None if absent), detail, and passed, and resolves status from the outer record. This adapter-to-gate conversion validates record consistency and frozen threshold identity; it does not independently recompute comparisons from arrays. Gate constructor status constraints remain applicable.

`QualificationConfig` requires integer dimension at least two; positive integer sample/batch/block/resample counts; a nonempty sequence of unique bit widths in 1..4; and sample-count divisibility by batch size and block count. Boolean values are rejected for these integer inputs.

`QualificationMetrics` requires bit width in 1..4, nonnegative integer sample count, product MSE bits in 0..3; finite scalar metrics; positive analytic/paper MSE targets and product paper target; and nonnegative observed MSE/product distortion, RMSE, product analytic target, sensitivity distortion, and sensitivity RMSE. Bias means may be signed. Intervals are two finite ordered endpoints. Populated block-mean sequences must all have equal lengths and finite elements. Empty block sequences are permitted. Validation does not require scientific counts to be nonzero in manually constructed metric records.

`QualificationResult.metrics` is nonempty, contains only `QualificationMetrics`, and has unique bit widths. `determinism_passed` accepts Python/NumPy Booleans and is normalized to Python bool. Result count fields and dimension are nonnegative integer-valued inputs; `configuration` is None or a `QualificationConfig`. Constructor validation does not automatically infer process determinism or require result count fields to agree with configuration counts.

`GateResult.status` is resolved from `passed` when omitted/falsy. Allowed resolved values are `passed`, `failed`, `not_run`; `passed` must equal whether status is `passed`. Name/detail are nonempty strings, and passed is a Python bool. Observed and threshold are arbitrary public evidence values.

`nearest_code_indices` uses midpoints calculated in FP64 from the actual supplied centroid values. Exact ties refer to those values, not their rounded decimal spelling or a separately rounded FP32 midpoint. Codebooks are nonempty, one-dimensional, strictly increasing, and contain at most 256 centroids.

`bootstrap_mean_interval` consumes a finite, nonempty one-dimensional sequence of block means, a NumPy Generator, a positive integer resample count, and finite confidence strictly between zero and one. It returns two Python floats using the percentile interval of equally sized resampled block-mean means and linear quantile interpolation. A random bootstrap interval is not defined by a guarantee that it contains the original empirical mean.

`create_run_directory` requires a nonempty run ID beginning with an ASCII alphanumeric character and containing only ASCII alphanumerics, period, underscore, or hyphen; it rejects path separators and ambiguous dot-directory names. It creates missing root parents, creates exactly one new run directory, and refuses an existing run path. CLI output namespaces remain a separate CLI requirement.

