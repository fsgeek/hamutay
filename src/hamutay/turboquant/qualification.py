"""Streaming statistics for the registered TurboQuant R1 qualification."""

from __future__ import annotations

import math
import operator
from dataclasses import dataclass
from functools import lru_cache
from numbers import Real
from typing import Any, Mapping, Sequence

import numpy as np
from numpy.typing import ArrayLike, NDArray
from scipy.integrate import quad

from .codebook import lloyd_max_codebook, sphere_coordinate_density
from .mse import MSEQuantizer
from .product import ProductQuantizer
from .rotation import canonical_qr, gaussian_rotation
from .seeding import rng_for

_MSE_PAPER_TARGETS = {1: 0.36, 2: 0.117, 3: 0.03, 4: 0.009}
_PRODUCT_PAPER_NUMERATORS = {1: 1.57, 2: 0.56, 3: 0.18, 4: 0.047}


def _positive_integer(value: int, *, name: str, minimum: int = 1) -> int:
    if isinstance(value, (bool, np.bool_)):
        raise ValueError(f"{name} must be an integer at least {minimum}")
    try:
        resolved = operator.index(value)
    except TypeError as error:
        raise ValueError(f"{name} must be an integer at least {minimum}") from error
    if resolved < minimum:
        raise ValueError(f"{name} must be an integer at least {minimum}")
    return resolved


def _finite_float(value: Real, *, name: str) -> float:
    if isinstance(value, (bool, np.bool_)) or not isinstance(value, Real):
        raise ValueError(f"{name} must be a finite real number")
    resolved = float(value)
    if not math.isfinite(resolved):
        raise ValueError(f"{name} must be a finite real number")
    return resolved


def _interval(value: tuple[float, float], *, name: str) -> tuple[float, float]:
    if not isinstance(value, (tuple, list)) or len(value) != 2:
        raise ValueError(f"{name} must contain exactly two finite endpoints")
    lower = _finite_float(value[0], name=f"{name} lower endpoint")
    upper = _finite_float(value[1], name=f"{name} upper endpoint")
    if lower > upper:
        raise ValueError(f"{name} endpoints must be ordered")
    return (lower, upper)


def _finite_tuple(values: Sequence[Real], *, name: str) -> tuple[float, ...]:
    try:
        resolved = tuple(_finite_float(value, name=f"{name} value") for value in values)
    except TypeError as error:
        raise ValueError(f"{name} must be a finite sequence") from error
    return resolved


@dataclass(frozen=True, slots=True)
class QualificationConfig:
    """Frozen synthetic qualification counts and requested total bit widths."""

    dimension: int = 128
    sample_count: int = 1_000_000
    batch_size: int = 4000
    bootstrap_blocks: int = 1000
    bootstrap_resamples: int = 10_000
    bits: tuple[int, ...] = (1, 2, 3, 4)

    def __post_init__(self) -> None:
        dimension = _positive_integer(self.dimension, name="dimension", minimum=2)
        sample_count = _positive_integer(self.sample_count, name="sample_count")
        batch_size = _positive_integer(self.batch_size, name="batch_size")
        bootstrap_blocks = _positive_integer(
            self.bootstrap_blocks, name="bootstrap_blocks"
        )
        bootstrap_resamples = _positive_integer(
            self.bootstrap_resamples, name="bootstrap_resamples"
        )
        try:
            bits = tuple(
                _positive_integer(bit_width, name="bits value")
                for bit_width in self.bits
            )
        except TypeError as error:
            raise ValueError("bits must be a nonempty sequence") from error
        if not bits:
            raise ValueError("bits must be a nonempty sequence")
        if any(bit_width > 4 for bit_width in bits):
            raise ValueError("every requested bit width must be in 1..4")
        if len(set(bits)) != len(bits):
            raise ValueError("requested bit widths must be unique")
        if sample_count % batch_size != 0:
            raise ValueError("sample_count must be divisible by batch_size")
        if sample_count % bootstrap_blocks != 0:
            raise ValueError("sample_count must be divisible by bootstrap_blocks")

        object.__setattr__(self, "dimension", dimension)
        object.__setattr__(self, "sample_count", sample_count)
        object.__setattr__(self, "batch_size", batch_size)
        object.__setattr__(self, "bootstrap_blocks", bootstrap_blocks)
        object.__setattr__(self, "bootstrap_resamples", bootstrap_resamples)
        object.__setattr__(self, "bits", bits)


@dataclass(frozen=True, slots=True)
class QualificationMetrics:
    """One total-bit width's gating metrics and non-gating diagnostics."""

    bits: int
    mse_observed: float
    mse_analytic_target: float
    mse_paper_target: float
    product_observed: float
    product_paper_target: float
    normalized_bias_mean: float
    normalized_bias_rmse: float
    normalized_bias_ci95: tuple[float, float]
    normalized_bias_ci9875: tuple[float, float]
    sample_count: int = 0
    product_mse_bits: int = 0
    product_analytic_target: float = 0.0
    sensitivity_product_observed: float = 0.0
    sensitivity_normalized_bias_mean: float = 0.0
    sensitivity_normalized_bias_rmse: float = 0.0
    sensitivity_normalized_bias_ci95: tuple[float, float] = (0.0, 0.0)
    sensitivity_normalized_bias_ci9875: tuple[float, float] = (0.0, 0.0)
    mse_block_means: tuple[float, ...] = ()
    product_block_means: tuple[float, ...] = ()
    normalized_bias_block_means: tuple[float, ...] = ()
    sensitivity_product_block_means: tuple[float, ...] = ()
    sensitivity_bias_block_means: tuple[float, ...] = ()

    def __post_init__(self) -> None:
        bits = _positive_integer(self.bits, name="bits")
        if bits > 4:
            raise ValueError("bits must be in 1..4")
        sample_count = operator.index(self.sample_count)
        if sample_count < 0:
            raise ValueError("sample_count must be nonnegative")
        product_mse_bits = operator.index(self.product_mse_bits)
        if not 0 <= product_mse_bits <= 3:
            raise ValueError("product_mse_bits must be in 0..3")

        positive_names = (
            "mse_analytic_target",
            "mse_paper_target",
            "product_paper_target",
        )
        nonnegative_names = (
            "mse_observed",
            "product_observed",
            "normalized_bias_rmse",
            "product_analytic_target",
            "sensitivity_product_observed",
            "sensitivity_normalized_bias_rmse",
        )
        scalar_names = (
            "mse_observed",
            "mse_analytic_target",
            "mse_paper_target",
            "product_observed",
            "product_paper_target",
            "normalized_bias_mean",
            "normalized_bias_rmse",
            "product_analytic_target",
            "sensitivity_product_observed",
            "sensitivity_normalized_bias_mean",
            "sensitivity_normalized_bias_rmse",
        )
        for name in scalar_names:
            resolved = _finite_float(getattr(self, name), name=name)
            object.__setattr__(self, name, resolved)
        for name in positive_names:
            if getattr(self, name) <= 0.0:
                raise ValueError(f"{name} must be positive")
        for name in nonnegative_names:
            if getattr(self, name) < 0.0:
                raise ValueError(f"{name} must be nonnegative")

        interval_names = (
            "normalized_bias_ci95",
            "normalized_bias_ci9875",
            "sensitivity_normalized_bias_ci95",
            "sensitivity_normalized_bias_ci9875",
        )
        for name in interval_names:
            object.__setattr__(self, name, _interval(getattr(self, name), name=name))
        block_names = (
            "mse_block_means",
            "product_block_means",
            "normalized_bias_block_means",
            "sensitivity_product_block_means",
            "sensitivity_bias_block_means",
        )
        block_lengths: set[int] = set()
        for name in block_names:
            values = _finite_tuple(getattr(self, name), name=name)
            object.__setattr__(self, name, values)
            if values:
                block_lengths.add(len(values))
        if len(block_lengths) > 1:
            raise ValueError(
                "all populated block-mean sequences must have equal length"
            )

        object.__setattr__(self, "bits", bits)
        object.__setattr__(self, "sample_count", sample_count)
        object.__setattr__(self, "product_mse_bits", product_mse_bits)


@dataclass(frozen=True, slots=True)
class QualificationResult:
    """Compact synthetic results; raw query/key pairs are deliberately absent."""

    metrics: tuple[QualificationMetrics, ...]
    determinism_passed: bool = False
    sample_count: int = 0
    batch_size: int = 0
    bootstrap_blocks: int = 0
    bootstrap_resamples: int = 0
    dimension: int = 0
    configuration: QualificationConfig | None = None

    def __post_init__(self) -> None:
        metrics = tuple(self.metrics)
        if not metrics:
            raise ValueError("metrics must be nonempty")
        if not all(isinstance(metric, QualificationMetrics) for metric in metrics):
            raise ValueError("metrics must contain QualificationMetrics instances")
        if len({metric.bits for metric in metrics}) != len(metrics):
            raise ValueError("metrics must contain unique bit widths")
        if not isinstance(self.determinism_passed, (bool, np.bool_)):
            raise ValueError("determinism_passed must be boolean")
        for name in (
            "sample_count",
            "batch_size",
            "bootstrap_blocks",
            "bootstrap_resamples",
            "dimension",
        ):
            value = operator.index(getattr(self, name))
            if value < 0:
                raise ValueError(f"{name} must be nonnegative")
            object.__setattr__(self, name, value)
        if self.configuration is not None and not isinstance(
            self.configuration, QualificationConfig
        ):
            raise ValueError("configuration must be a QualificationConfig")
        object.__setattr__(self, "metrics", metrics)
        object.__setattr__(self, "determinism_passed", bool(self.determinism_passed))


@dataclass(frozen=True, slots=True)
class GateResult:
    """One named qualification decision and its auditable boundary."""

    name: str
    passed: bool
    observed: Any
    threshold: Any
    detail: str
    status: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not self.name:
            raise ValueError("gate name must be a nonempty string")
        if not isinstance(self.passed, bool):
            raise ValueError("gate passed must be boolean")
        if not isinstance(self.detail, str) or not self.detail:
            raise ValueError("gate detail must be a nonempty string")
        status = self.status or ("passed" if self.passed else "failed")
        if status not in {"passed", "failed", "not_run"}:
            raise ValueError("gate status must be passed, failed, or not_run")
        if self.passed != (status == "passed"):
            raise ValueError("gate passed must agree with gate status")
        object.__setattr__(self, "status", status)


def author_code_differential_gate(
    oracle_result: Mapping[str, Any] | None,
) -> GateResult:
    """Return the fifth gate, explicitly retaining a development non-run."""
    threshold = {"atol": 1e-5, "rtol": 1e-4}
    if oracle_result is None:
        return GateResult(
            name="author_code_differential",
            passed=False,
            observed="not_run",
            threshold=threshold,
            detail="Author QJL checkout was omitted in development mode.",
            status="not_run",
        )
    if not isinstance(oracle_result, Mapping):
        raise ValueError("author QJL oracle result must be a mapping")
    record = oracle_result.get("gate")
    if not isinstance(record, Mapping):
        raise ValueError("author QJL oracle result is missing its gate")
    if record.get("name") != "author_code_differential":
        raise ValueError("author QJL oracle returned the wrong gate name")
    passed = record.get("passed")
    if not isinstance(passed, bool):
        raise ValueError("author QJL oracle gate passed value must be boolean")
    oracle_status = oracle_result.get("status")
    expected_status = "passed" if passed else "failed"
    if oracle_status != expected_status:
        raise ValueError("author QJL oracle status disagrees with its gate")
    if record.get("threshold") != threshold:
        raise ValueError("author QJL oracle changed the frozen FP32 tolerance")
    detail = record.get("detail")
    if not isinstance(detail, str) or not detail:
        raise ValueError("author QJL oracle gate detail must be nonempty")
    return GateResult(
        name="author_code_differential",
        passed=passed,
        observed=record.get("observed"),
        threshold=threshold,
        detail=detail,
        status=expected_status,
    )


def partition_block_ids(sample_count: int, block_count: int) -> NDArray[np.int64]:
    """Assign every sample to one of equally sized contiguous blocks."""
    samples = _positive_integer(sample_count, name="sample_count")
    blocks = _positive_integer(block_count, name="block_count")
    if samples % blocks != 0:
        raise ValueError("sample_count must be divisible by block_count")
    block_size = samples // blocks
    return np.repeat(np.arange(blocks, dtype=np.int64), block_size)


def bootstrap_mean_interval(
    block_means: ArrayLike,
    *,
    rng: np.random.Generator,
    resamples: int = 10_000,
    confidence: float = 0.95,
) -> tuple[float, float]:
    """Percentile-bootstrap a mean by resampling whole block means."""
    values = np.asarray(block_means, dtype=np.float64)
    if values.ndim != 1 or values.size == 0 or not np.all(np.isfinite(values)):
        raise ValueError("block_means must be a nonempty finite one-dimensional array")
    if not isinstance(rng, np.random.Generator):
        raise ValueError("rng must be a numpy.random.Generator")
    resolved_resamples = _positive_integer(resamples, name="resamples")
    resolved_confidence = _finite_float(confidence, name="confidence")
    if not 0.0 < resolved_confidence < 1.0:
        raise ValueError("confidence must be strictly between zero and one")

    bootstrap_means = np.empty(resolved_resamples, dtype=np.float64)
    chunk_size = min(256, resolved_resamples)
    for start in range(0, resolved_resamples, chunk_size):
        stop = min(start + chunk_size, resolved_resamples)
        indices = rng.integers(0, values.size, size=(stop - start, values.size))
        bootstrap_means[start:stop] = np.mean(values[indices], axis=1, dtype=np.float64)
    alpha = 1.0 - resolved_confidence
    bounds = np.quantile(
        bootstrap_means, (alpha / 2.0, 1.0 - alpha / 2.0), method="linear"
    )
    return (float(bounds[0]), float(bounds[1]))


def analytic_codebook_distortion(
    codebook: NDArray[np.float32], dimension: int
) -> float:
    """Integrate the frozen codebook's normalized spherical MSE in FP64."""
    resolved_dimension = _positive_integer(dimension, name="dimension", minimum=2)
    resolved_codebook = np.asarray(codebook)
    if resolved_codebook.ndim != 1 or resolved_codebook.size == 0:
        raise ValueError("codebook must be a nonempty one-dimensional array")
    if resolved_codebook.dtype.kind != "f":
        raise ValueError("codebook must have a floating-point dtype")
    centroids = resolved_codebook.astype(np.float64)
    if (
        not np.all(np.isfinite(centroids))
        or np.any(np.diff(centroids) <= 0.0)
        or centroids[0] < -1.0
        or centroids[-1] > 1.0
    ):
        raise ValueError(
            "codebook must contain finite, strictly increasing centroids in [-1, 1]"
        )
    boundaries = np.concatenate(
        (
            np.array([-1.0]),
            (centroids[:-1] + centroids[1:]) / 2.0,
            np.array([1.0]),
        )
    )
    distortion = math.fsum(
        quad(
            lambda value, centroid=centroid: (
                (value - centroid) ** 2
                * sphere_coordinate_density(value, resolved_dimension)
            ),
            lower,
            upper,
            epsabs=1e-14,
            epsrel=1e-13,
            limit=200,
        )[0]
        for centroid, lower, upper in zip(
            centroids, boundaries[:-1], boundaries[1:], strict=True
        )
    )
    return float(resolved_dimension * distortion)


def _relative_error(observed: float, target: float) -> float:
    return abs(observed - target) / target


def evaluate_algorithm_gates(result: QualificationResult) -> Sequence[GateResult]:
    """Evaluate the four Task 5 gates; Task 7 later joins the author gate."""
    if not isinstance(result, QualificationResult):
        raise ValueError("result must be a QualificationResult")
    metrics = result.metrics

    mse_ratios = tuple(
        (
            metric.bits,
            _relative_error(metric.mse_observed, metric.mse_analytic_target),
            _relative_error(metric.mse_observed, metric.mse_paper_target),
        )
        for metric in metrics
    )
    mse_passed = all(
        analytic_error <= 0.005 and paper_error <= 0.15
        for _, analytic_error, paper_error in mse_ratios
    )

    bias_conditions = tuple(
        (
            metric.bits,
            metric.normalized_bias_ci9875[0],
            metric.normalized_bias_ci9875[1],
            -0.02 * metric.normalized_bias_rmse,
            0.02 * metric.normalized_bias_rmse,
        )
        for metric in metrics
    )
    bias_passed = all(
        interval_lower >= region_lower and interval_upper <= region_upper
        for _, interval_lower, interval_upper, region_lower, region_upper in bias_conditions
    )

    product_ratios = tuple(
        (
            metric.bits,
            _relative_error(metric.product_observed, metric.product_paper_target),
            metric.product_observed / metric.product_paper_target,
            metric.product_analytic_target,
        )
        for metric in metrics
    )
    product_passed = all(
        relative_error <= 0.15 for _, relative_error, _, _ in product_ratios
    )
    rounding_detail = (
        " The four-bit paper target inherits rounding from the paper's "
        "three-bit scalar value; its registered tolerance is unchanged."
        if any(metric.bits == 4 for metric in metrics)
        else ""
    )

    return (
        GateResult(
            name="round_trip_determinism",
            passed=result.determinism_passed,
            observed=result.determinism_passed,
            threshold=True,
            detail="Three-process comparison is supplied by the artifact worker stage.",
        ),
        GateResult(
            name="mse_distortion",
            passed=mse_passed,
            observed=mse_ratios,
            threshold=(
                ("analytic_relative_error", 0.005),
                ("paper_relative_error", 0.15),
            ),
            detail="Each bit width must independently satisfy both relative-error bounds.",
        ),
        GateResult(
            name="qjl_bias_equivalence",
            passed=bias_passed,
            observed=bias_conditions,
            threshold="98.75% interval wholly within +/-2% of normalized RMSE",
            detail="Ordinary 95% intervals are diagnostic only and do not gate.",
        ),
        GateResult(
            name="published_qjl_distortion",
            passed=product_passed,
            observed=product_ratios,
            threshold=(("paper_relative_error", 0.15),),
            detail=(
                "Observed/paper ratios and analytic residual diagnostics are reported "
                "separately." + rounding_detail
            ),
        ),
    )


@lru_cache(maxsize=None)
def _cached_codebook(dimension: int, bits: int) -> NDArray[np.float32]:
    codebook = lloyd_max_codebook(dimension, bits)
    codebook.setflags(write=False)
    return codebook


def _paper_projection(dimension: int) -> NDArray[np.float32]:
    projection = rng_for(
        "qualification", "algorithm_2", "paper_literal", "projection"
    ).standard_normal((dimension, dimension))
    return np.ascontiguousarray(projection, dtype=np.float32)


def _row_orthogonal_projection(dimension: int) -> NDArray[np.float32]:
    """Return an independent row-orthogonal sensitivity projection at scale sqrt(d)."""
    resolved_dimension = _positive_integer(dimension, name="dimension", minimum=2)
    matrix = rng_for(
        "qualification", "algorithm_2", "row_orthogonal", "projection"
    ).standard_normal((resolved_dimension, resolved_dimension))
    row_orthogonal = canonical_qr(matrix.T).T * math.sqrt(resolved_dimension)
    return np.ascontiguousarray(row_orthogonal, dtype=np.float32)


def _normalized_product_errors(
    queries: NDArray[np.float32],
    keys: NDArray[np.float32],
    estimates: NDArray[np.float32],
) -> tuple[NDArray[np.float32], NDArray[np.float32]]:
    """Return normalized squared and signed paired product errors in FP32."""
    resolved_queries = np.asarray(queries, dtype=np.float32)
    resolved_keys = np.asarray(keys, dtype=np.float32)
    resolved_estimates = np.asarray(estimates, dtype=np.float32)
    if (
        resolved_queries.ndim < 1
        or resolved_queries.shape != resolved_keys.shape
        or resolved_estimates.shape != resolved_queries.shape[:-1]
    ):
        raise ValueError("queries, keys, and estimates must have paired shapes")
    exact = np.sum(resolved_queries * resolved_keys, axis=-1, dtype=np.float32)
    signed_error = resolved_estimates - exact
    query_squared_norm = np.sum(
        resolved_queries * resolved_queries, axis=-1, dtype=np.float32
    )
    key_squared_norm = np.sum(resolved_keys * resolved_keys, axis=-1, dtype=np.float32)
    normalizer = np.sqrt(query_squared_norm) * np.sqrt(key_squared_norm)
    normalized_signed = np.zeros_like(signed_error, dtype=np.float32)
    np.divide(
        signed_error,
        normalizer,
        out=normalized_signed,
        where=normalizer != 0.0,
    )
    normalized_squared = normalized_signed * normalized_signed
    return (
        np.array(normalized_squared, dtype=np.float32, order="C", copy=True),
        np.array(normalized_signed, dtype=np.float32, order="C", copy=True),
    )


def _normalized_mse(
    keys: NDArray[np.float32], reconstructed: NDArray[np.float32]
) -> NDArray[np.float32]:
    difference = reconstructed - keys
    numerator = np.sum(difference * difference, axis=-1, dtype=np.float32)
    denominator = np.sum(keys * keys, axis=-1, dtype=np.float32)
    result = np.zeros_like(numerator, dtype=np.float32)
    np.divide(numerator, denominator, out=result, where=denominator != 0.0)
    return result


def _add_batch_to_blocks(
    block_sums: NDArray[np.float64],
    values: NDArray[np.float32],
    *,
    sample_offset: int,
    sample_count: int,
) -> None:
    block_size = sample_count // block_sums.size
    sample_indices = np.arange(sample_offset, sample_offset + values.size)
    block_ids = sample_indices // block_size
    block_sums += np.bincount(
        block_ids,
        weights=np.asarray(values, dtype=np.float64),
        minlength=block_sums.size,
    )[: block_sums.size]


def _block_means(
    block_sums: NDArray[np.float64], *, sample_count: int
) -> tuple[float, ...]:
    block_size = sample_count // block_sums.size
    return tuple(float(value) for value in block_sums / block_size)


def _mean_of_blocks(block_means: tuple[float, ...]) -> float:
    return math.fsum(block_means) / len(block_means)


def _bias_intervals(
    block_means: tuple[float, ...],
    *,
    bits: int,
    resamples: int,
    purpose: str,
) -> tuple[tuple[float, float], tuple[float, float]]:
    ci95 = bootstrap_mean_interval(
        block_means,
        rng=rng_for("qualification", "bootstrap", purpose, "0.95", bits),
        resamples=resamples,
        confidence=0.95,
    )
    ci9875 = bootstrap_mean_interval(
        block_means,
        rng=rng_for("qualification", "bootstrap", purpose, "0.9875", bits),
        resamples=resamples,
        confidence=0.9875,
    )
    return ci95, ci9875


def run_synthetic_qualification(config: QualificationConfig) -> QualificationResult:
    """Stream deterministic synthetic query/key pairs through Algorithms 1 and 2."""
    if not isinstance(config, QualificationConfig):
        raise ValueError("config must be a QualificationConfig")

    dimension = config.dimension
    rotation = gaussian_rotation(dimension, "qualification", "algorithm_1", "rotation")
    paper_projection = _paper_projection(dimension)
    sensitivity_projection = _row_orthogonal_projection(dimension)

    scalar_quantizers: dict[int, MSEQuantizer] = {}
    paper_product_quantizers: dict[int, ProductQuantizer] = {}
    sensitivity_product_quantizers: dict[int, ProductQuantizer] = {}
    for bit_width in config.bits:
        scalar_quantizers[bit_width] = MSEQuantizer(
            rotation, _cached_codebook(dimension, bit_width)
        )
        embedded = MSEQuantizer(rotation, _cached_codebook(dimension, bit_width - 1))
        paper_product_quantizers[bit_width] = ProductQuantizer(
            embedded, paper_projection
        )
        sensitivity_product_quantizers[bit_width] = ProductQuantizer(
            embedded, sensitivity_projection
        )

    accumulator_names = (
        "mse",
        "product",
        "bias",
        "sensitivity_product",
        "sensitivity_bias",
    )
    accumulators = {
        name: {
            bit_width: np.zeros(config.bootstrap_blocks, dtype=np.float64)
            for bit_width in config.bits
        }
        for name in accumulator_names
    }
    key_rng = rng_for("qualification", "synthetic", "keys")
    query_rng = rng_for("qualification", "synthetic", "queries")

    for sample_offset in range(0, config.sample_count, config.batch_size):
        keys = key_rng.standard_normal((config.batch_size, dimension), dtype=np.float32)
        queries = query_rng.standard_normal(
            (config.batch_size, dimension), dtype=np.float32
        )
        for bit_width in config.bits:
            mse_quantizer = scalar_quantizers[bit_width]
            mse_codes = mse_quantizer.quantize(keys)
            mse_values = _normalized_mse(keys, mse_quantizer.dequantize(mse_codes))

            paper_quantizer = paper_product_quantizers[bit_width]
            paper_codes = paper_quantizer.quantize(keys)
            paper_squared, paper_bias = _normalized_product_errors(
                queries,
                keys,
                paper_quantizer.estimate_inner_products(queries, paper_codes),
            )

            sensitivity_quantizer = sensitivity_product_quantizers[bit_width]
            sensitivity_codes = sensitivity_quantizer.quantize(keys)
            sensitivity_squared, sensitivity_bias = _normalized_product_errors(
                queries,
                keys,
                sensitivity_quantizer.estimate_inner_products(
                    queries, sensitivity_codes
                ),
            )

            for name, values in (
                ("mse", mse_values),
                ("product", paper_squared),
                ("bias", paper_bias),
                ("sensitivity_product", sensitivity_squared),
                ("sensitivity_bias", sensitivity_bias),
            ):
                _add_batch_to_blocks(
                    accumulators[name][bit_width],
                    values,
                    sample_offset=sample_offset,
                    sample_count=config.sample_count,
                )

    metrics: list[QualificationMetrics] = []
    for bit_width in config.bits:
        block_values = {
            name: _block_means(
                accumulators[name][bit_width], sample_count=config.sample_count
            )
            for name in accumulator_names
        }
        product_observed = _mean_of_blocks(block_values["product"])
        sensitivity_product_observed = _mean_of_blocks(
            block_values["sensitivity_product"]
        )
        bias_ci95, bias_ci9875 = _bias_intervals(
            block_values["bias"],
            bits=bit_width,
            resamples=config.bootstrap_resamples,
            purpose="bias",
        )
        sensitivity_ci95, sensitivity_ci9875 = _bias_intervals(
            block_values["sensitivity_bias"],
            bits=bit_width,
            resamples=config.bootstrap_resamples,
            purpose="sensitivity_bias",
        )
        embedded_codebook = paper_product_quantizers[bit_width].mse_quantizer.codebook
        product_mse_bits = embedded_codebook.size.bit_length() - 1
        embedded_distortion = analytic_codebook_distortion(embedded_codebook, dimension)
        metrics.append(
            QualificationMetrics(
                bits=bit_width,
                mse_observed=_mean_of_blocks(block_values["mse"]),
                mse_analytic_target=analytic_codebook_distortion(
                    scalar_quantizers[bit_width].codebook, dimension
                ),
                mse_paper_target=_MSE_PAPER_TARGETS[bit_width],
                product_observed=product_observed,
                product_paper_target=(_PRODUCT_PAPER_NUMERATORS[bit_width] / dimension),
                normalized_bias_mean=_mean_of_blocks(block_values["bias"]),
                normalized_bias_rmse=math.sqrt(product_observed),
                normalized_bias_ci95=bias_ci95,
                normalized_bias_ci9875=bias_ci9875,
                sample_count=config.sample_count,
                product_mse_bits=product_mse_bits,
                product_analytic_target=(
                    (math.pi / 2.0) * embedded_distortion / dimension
                ),
                sensitivity_product_observed=sensitivity_product_observed,
                sensitivity_normalized_bias_mean=_mean_of_blocks(
                    block_values["sensitivity_bias"]
                ),
                sensitivity_normalized_bias_rmse=math.sqrt(
                    sensitivity_product_observed
                ),
                sensitivity_normalized_bias_ci95=sensitivity_ci95,
                sensitivity_normalized_bias_ci9875=sensitivity_ci9875,
                mse_block_means=block_values["mse"],
                product_block_means=block_values["product"],
                normalized_bias_block_means=block_values["bias"],
                sensitivity_product_block_means=block_values["sensitivity_product"],
                sensitivity_bias_block_means=block_values["sensitivity_bias"],
            )
        )

    return QualificationResult(
        metrics=tuple(metrics),
        determinism_passed=False,
        sample_count=config.sample_count,
        batch_size=config.batch_size,
        bootstrap_blocks=config.bootstrap_blocks,
        bootstrap_resamples=config.bootstrap_resamples,
        dimension=config.dimension,
        configuration=config,
    )
