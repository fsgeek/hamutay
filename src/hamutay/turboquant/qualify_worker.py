"""Fresh-process worker for one deterministic TurboQuant qualification pass."""

from __future__ import annotations

import argparse
from contextlib import redirect_stderr, redirect_stdout
from dataclasses import asdict
import hashlib
import io
import math
import os
from pathlib import Path
import traceback
from typing import Sequence

import numpy as np

from .artifacts import (
    ArrayStreamHasher,
    atomic_write_json,
    canonical_json_bytes,
    read_canonical_json,
    sha256_file,
)
from .mse import MSEQuantizer
from .product import ProductQuantizer
from .qualification import (
    QualificationConfig,
    QualificationMetrics,
    QualificationResult,
    analytic_codebook_distortion,
    bootstrap_mean_interval,
)
from .seeding import rng_for

_MSE_PAPER_TARGETS = {1: 0.36, 2: 0.117, 3: 0.03, 4: 0.009}
_PRODUCT_PAPER_NUMERATORS = {1: 1.57, 2: 0.56, 3: 0.18, 4: 0.047}
_WORKER_ENVIRONMENT_NAMES = (
    "BLIS_NUM_THREADS",
    "CUBLAS_WORKSPACE_CONFIG",
    "MKL_NUM_THREADS",
    "NUMEXPR_NUM_THREADS",
    "OMP_NUM_THREADS",
    "OPENBLAS_NUM_THREADS",
    "PYTHONHASHSEED",
    "VECLIB_MAXIMUM_THREADS",
)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m hamutay.turboquant.qualify_worker")
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--resolved-inputs", type=Path, required=True)
    parser.add_argument("--execution-index", type=int, choices=(0, 1, 2), required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser


def _configuration_dict(config: QualificationConfig) -> dict[str, object]:
    return {
        "dimension": config.dimension,
        "sample_count": config.sample_count,
        "batch_size": config.batch_size,
        "bootstrap_blocks": config.bootstrap_blocks,
        "bootstrap_resamples": config.bootstrap_resamples,
        "bits": list(config.bits),
    }


def _load_configuration(path: Path) -> tuple[QualificationConfig, dict[str, object]]:
    value = read_canonical_json(path)
    if not isinstance(value, dict) or value.get("schema") != (
        "hamutay.turboquant.worker-config.v1"
    ):
        raise ValueError("worker configuration has the wrong schema")
    configuration = value.get("configuration")
    if not isinstance(configuration, dict):
        raise ValueError("worker configuration is missing configuration")
    config = QualificationConfig(
        dimension=configuration.get("dimension"),
        sample_count=configuration.get("sample_count"),
        batch_size=configuration.get("batch_size"),
        bootstrap_blocks=configuration.get("bootstrap_blocks"),
        bootstrap_resamples=configuration.get("bootstrap_resamples"),
        bits=tuple(configuration.get("bits", ())),
    )
    if configuration != _configuration_dict(config):
        raise ValueError("worker configuration contains unknown or noncanonical fields")
    return config, value


def _load_resolved_inputs(
    path: Path, config: QualificationConfig
) -> dict[str, np.ndarray]:
    required_codebook_bits = {*config.bits, *(bits - 1 for bits in config.bits)}
    required_names = {
        "rotation",
        "paper_projection",
        "sensitivity_projection",
        *(f"codebook_bits_{bits}" for bits in required_codebook_bits),
    }
    with np.load(path, allow_pickle=False) as archive:
        if set(archive.files) != required_names:
            raise ValueError(
                "resolved input names do not match the frozen configuration"
            )
        arrays = {
            name: np.array(archive[name], dtype=np.float32, order="C", copy=True)
            for name in sorted(required_names)
        }
    dimension = config.dimension
    matrix_names = ("rotation", "paper_projection", "sensitivity_projection")
    for name in matrix_names:
        array = arrays[name]
        if array.dtype != np.float32 or array.shape != (dimension, dimension):
            raise ValueError(f"{name} must be FP32 with shape (dimension, dimension)")
    for bits in required_codebook_bits:
        name = f"codebook_bits_{bits}"
        codebook = arrays[name]
        if codebook.dtype != np.float32 or codebook.shape != (2**bits,):
            raise ValueError(f"{name} has the wrong FP32 shape")
    return arrays


def _add_to_blocks(
    block_sums: np.ndarray,
    values: np.ndarray,
    *,
    offset: int,
    sample_count: int,
) -> None:
    block_size = sample_count // block_sums.size
    block_ids = np.arange(offset, offset + values.size, dtype=np.int64) // block_size
    block_sums += np.bincount(
        block_ids,
        weights=np.asarray(values, dtype=np.float64),
        minlength=block_sums.size,
    )[: block_sums.size]


def _normalized_mse(keys: np.ndarray, reconstructed: np.ndarray) -> np.ndarray:
    difference = reconstructed - keys
    numerator = np.sum(difference * difference, axis=-1, dtype=np.float32)
    denominator = np.sum(keys * keys, axis=-1, dtype=np.float32)
    values = np.zeros_like(numerator, dtype=np.float32)
    np.divide(numerator, denominator, out=values, where=denominator != 0.0)
    return values


def _normalized_product_errors(
    queries: np.ndarray, keys: np.ndarray, estimates: np.ndarray
) -> tuple[np.ndarray, np.ndarray]:
    exact = np.sum(queries * keys, axis=-1, dtype=np.float32)
    signed_error = estimates - exact
    query_squared_norm = np.sum(queries * queries, axis=-1, dtype=np.float32)
    key_squared_norm = np.sum(keys * keys, axis=-1, dtype=np.float32)
    normalizer = np.sqrt(query_squared_norm) * np.sqrt(key_squared_norm)
    signed = np.zeros_like(signed_error, dtype=np.float32)
    np.divide(signed_error, normalizer, out=signed, where=normalizer != 0.0)
    return signed * signed, signed


def _block_means(block_sums: np.ndarray, sample_count: int) -> tuple[float, ...]:
    block_size = sample_count // block_sums.size
    return tuple(float(value) for value in block_sums / block_size)


def _mean(values: tuple[float, ...]) -> float:
    return math.fsum(values) / len(values)


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


def _run_frozen_qualification(
    config: QualificationConfig, arrays: dict[str, np.ndarray]
) -> tuple[QualificationResult, dict[str, str]]:
    rotation = arrays["rotation"]
    paper_projection = arrays["paper_projection"]
    sensitivity_projection = arrays["sensitivity_projection"]
    scalar_quantizers: dict[int, MSEQuantizer] = {}
    paper_quantizers: dict[int, ProductQuantizer] = {}
    sensitivity_quantizers: dict[int, ProductQuantizer] = {}
    for bits in config.bits:
        scalar_quantizers[bits] = MSEQuantizer(
            rotation, arrays[f"codebook_bits_{bits}"]
        )
        embedded = MSEQuantizer(rotation, arrays[f"codebook_bits_{bits - 1}"])
        paper_quantizers[bits] = ProductQuantizer(embedded, paper_projection)
        sensitivity_quantizers[bits] = ProductQuantizer(
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
            bits: np.zeros(config.bootstrap_blocks, dtype=np.float64)
            for bits in config.bits
        }
        for name in accumulator_names
    }
    stream_hashers: dict[str, ArrayStreamHasher] = {}

    def record(name: str, label: str, values: np.ndarray) -> None:
        stream_hashers.setdefault(name, ArrayStreamHasher()).update(label, values)

    key_rng = rng_for("qualification", "synthetic", "keys")
    query_rng = rng_for("qualification", "synthetic", "queries")
    for offset in range(0, config.sample_count, config.batch_size):
        keys = key_rng.standard_normal(
            (config.batch_size, config.dimension), dtype=np.float32
        )
        queries = query_rng.standard_normal(
            (config.batch_size, config.dimension), dtype=np.float32
        )
        record("synthetic.keys", "keys", keys)
        record("synthetic.queries", "queries", queries)
        for bits in config.bits:
            scalar = scalar_quantizers[bits]
            mse_codes = scalar.quantize(keys)
            mse_reconstructed = scalar.dequantize(mse_codes)
            record(f"algorithm_1.bits_{bits}.codes", "codes", mse_codes.indices)
            record(f"algorithm_1.bits_{bits}.norms", "norms", mse_codes.norms)
            record(
                f"algorithm_1.bits_{bits}.reconstruction",
                "reconstruction",
                mse_reconstructed,
            )
            mse_values = _normalized_mse(keys, mse_reconstructed)

            paper = paper_quantizers[bits]
            paper_codes = paper.quantize(keys)
            paper_reconstructed = paper.dequantize(paper_codes)
            paper_estimates = paper.estimate_inner_products(queries, paper_codes)
            paper_squared, paper_bias = _normalized_product_errors(
                queries, keys, paper_estimates
            )
            for suffix, label, values in (
                ("codes", "codes", paper_codes.mse.indices),
                ("norms", "norms", paper_codes.mse.norms),
                ("signs", "signs", paper_codes.packed_signs),
                ("residual_norms", "residual_norms", paper_codes.residual_norms),
                ("reconstruction", "reconstruction", paper_reconstructed),
            ):
                record(f"algorithm_2.paper.bits_{bits}.{suffix}", label, values)

            sensitivity = sensitivity_quantizers[bits]
            sensitivity_codes = sensitivity.quantize(keys)
            sensitivity_reconstructed = sensitivity.dequantize(sensitivity_codes)
            sensitivity_estimates = sensitivity.estimate_inner_products(
                queries, sensitivity_codes
            )
            sensitivity_squared, sensitivity_bias = _normalized_product_errors(
                queries, keys, sensitivity_estimates
            )
            for suffix, label, values in (
                ("codes", "codes", sensitivity_codes.mse.indices),
                ("norms", "norms", sensitivity_codes.mse.norms),
                ("signs", "signs", sensitivity_codes.packed_signs),
                (
                    "residual_norms",
                    "residual_norms",
                    sensitivity_codes.residual_norms,
                ),
                ("reconstruction", "reconstruction", sensitivity_reconstructed),
            ):
                record(f"algorithm_2.sensitivity.bits_{bits}.{suffix}", label, values)

            for name, values in (
                ("mse", mse_values),
                ("product", paper_squared),
                ("bias", paper_bias),
                ("sensitivity_product", sensitivity_squared),
                ("sensitivity_bias", sensitivity_bias),
            ):
                _add_to_blocks(
                    accumulators[name][bits],
                    values,
                    offset=offset,
                    sample_count=config.sample_count,
                )

    metrics: list[QualificationMetrics] = []
    for bits in config.bits:
        blocks = {
            name: _block_means(accumulators[name][bits], config.sample_count)
            for name in accumulator_names
        }
        product_observed = _mean(blocks["product"])
        sensitivity_observed = _mean(blocks["sensitivity_product"])
        bias_ci95, bias_ci9875 = _bias_intervals(
            blocks["bias"],
            bits=bits,
            resamples=config.bootstrap_resamples,
            purpose="bias",
        )
        sensitivity_ci95, sensitivity_ci9875 = _bias_intervals(
            blocks["sensitivity_bias"],
            bits=bits,
            resamples=config.bootstrap_resamples,
            purpose="sensitivity_bias",
        )
        embedded_codebook = arrays[f"codebook_bits_{bits - 1}"]
        metrics.append(
            QualificationMetrics(
                bits=bits,
                mse_observed=_mean(blocks["mse"]),
                mse_analytic_target=analytic_codebook_distortion(
                    arrays[f"codebook_bits_{bits}"], config.dimension
                ),
                mse_paper_target=_MSE_PAPER_TARGETS[bits],
                product_observed=product_observed,
                product_paper_target=_PRODUCT_PAPER_NUMERATORS[bits] / config.dimension,
                normalized_bias_mean=_mean(blocks["bias"]),
                normalized_bias_rmse=math.sqrt(product_observed),
                normalized_bias_ci95=bias_ci95,
                normalized_bias_ci9875=bias_ci9875,
                sample_count=config.sample_count,
                product_mse_bits=bits - 1,
                product_analytic_target=(
                    math.pi
                    / 2.0
                    * analytic_codebook_distortion(embedded_codebook, config.dimension)
                    / config.dimension
                ),
                sensitivity_product_observed=sensitivity_observed,
                sensitivity_normalized_bias_mean=_mean(blocks["sensitivity_bias"]),
                sensitivity_normalized_bias_rmse=math.sqrt(sensitivity_observed),
                sensitivity_normalized_bias_ci95=sensitivity_ci95,
                sensitivity_normalized_bias_ci9875=sensitivity_ci9875,
                mse_block_means=blocks["mse"],
                product_block_means=blocks["product"],
                normalized_bias_block_means=blocks["bias"],
                sensitivity_product_block_means=blocks["sensitivity_product"],
                sensitivity_bias_block_means=blocks["sensitivity_bias"],
            )
        )
    result = QualificationResult(
        metrics=tuple(metrics),
        determinism_passed=False,
        sample_count=config.sample_count,
        batch_size=config.batch_size,
        bootstrap_blocks=config.bootstrap_blocks,
        bootstrap_resamples=config.bootstrap_resamples,
        dimension=config.dimension,
        configuration=config,
    )
    return result, {
        name: hasher.hexdigest() for name, hasher in sorted(stream_hashers.items())
    }


def _worker_record(
    args: argparse.Namespace,
    *,
    status: str,
    configuration_sha256: str | None,
    resolved_inputs_sha256: str | None,
    stdout: str,
    stderr: str,
    determinism_payload: dict[str, object] | None = None,
    error: BaseException | None = None,
) -> dict[str, object]:
    record: dict[str, object] = {
        "schema": "hamutay.turboquant.execution.v1",
        "status": status,
        "execution_index": args.execution_index,
        "configuration_sha256": configuration_sha256,
        "resolved_inputs_sha256": resolved_inputs_sha256,
        "provenance": {
            "pid": os.getpid(),
            "parent_pid": os.getppid(),
            "worker_environment": {
                name: os.environ.get(name) for name in _WORKER_ENVIRONMENT_NAMES
            },
        },
        "stdout": stdout,
        "stderr": stderr,
    }
    if determinism_payload is not None:
        payload_bytes = canonical_json_bytes(determinism_payload)
        record["determinism_payload"] = determinism_payload
        record["determinism_payload_sha256"] = hashlib.sha256(payload_bytes).hexdigest()
    if error is not None:
        record["error"] = {
            "type": type(error).__name__,
            "message": str(error),
            "traceback": traceback.format_exc(),
        }
    return record


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    if args.output.exists():
        parser.error(f"refusing to overwrite execution artifact: {args.output}")
    stdout_buffer = io.StringIO()
    stderr_buffer = io.StringIO()
    configuration_sha256: str | None = None
    resolved_inputs_sha256: str | None = None
    try:
        with redirect_stdout(stdout_buffer), redirect_stderr(stderr_buffer):
            config, worker_config = _load_configuration(args.config)
            configuration_sha256 = sha256_file(args.config)
            resolved_inputs_sha256 = sha256_file(args.resolved_inputs)
            if worker_config.get("resolved_inputs_sha256") != resolved_inputs_sha256:
                raise ValueError(
                    "resolved input file hash does not match worker config"
                )
            arrays = _load_resolved_inputs(args.resolved_inputs, config)
            result, stream_hashes = _run_frozen_qualification(config, arrays)
            metrics = [asdict(metric) for metric in result.metrics]
            metric_sha256 = hashlib.sha256(canonical_json_bytes(metrics)).hexdigest()
            payload: dict[str, object] = {
                "metrics": metrics,
                "metric_sha256": metric_sha256,
                "stream_sha256": stream_hashes,
            }
        record = _worker_record(
            args,
            status="passed",
            configuration_sha256=configuration_sha256,
            resolved_inputs_sha256=resolved_inputs_sha256,
            stdout=stdout_buffer.getvalue(),
            stderr=stderr_buffer.getvalue(),
            determinism_payload=payload,
        )
        atomic_write_json(args.output, record)
        return 0
    except BaseException as error:
        record = _worker_record(
            args,
            status="error",
            configuration_sha256=configuration_sha256,
            resolved_inputs_sha256=resolved_inputs_sha256,
            stdout=stdout_buffer.getvalue(),
            stderr=stderr_buffer.getvalue(),
            error=error,
        )
        atomic_write_json(args.output, record)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
