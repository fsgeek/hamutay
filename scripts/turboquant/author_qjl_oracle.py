#!/usr/bin/env python3
"""Pinned CUDA differential against the author QJL implementation."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import re
import shutil
import subprocess
from typing import Any, Mapping, Sequence

import numpy as np
import torch
from torch.utils.cpp_extension import load

from hamutay.turboquant.artifacts import (
    atomic_savez,
    atomic_write_json,
    sha256_array,
    sha256_file,
)
from hamutay.turboquant.product import pack_signs
from hamutay.turboquant.seeding import STUDY_SEED_HEX, rng_for


UPSTREAM_REPOSITORY = "https://github.com/amirzandieh/QJL"
UPSTREAM_COMMIT = "648b3641f96b6e95e091217220b94e4739fd4d82"
PINNED_SHA256 = {
    "LICENSE": "c71d239df91726fc519c6eb72d318ec65820627232b2f796219e87dcf35d0ab4",
    "qjl_kernel/csrc/qjl_quant_kernel.cu": (
        "d03b2fd86504554f48da48df2740d73a0cc2d1d8a28c22698da20c9ee801aefd"
    ),
    "qjl_kernel/csrc/qjl_score_kernel.cu": (
        "848398bb6b140433aa10f4ccea16eb680ec215cb148956f09e46bbbdabdc030c"
    ),
    "models/llama3_utils_qjl.py": (
        "725b6777b752e30b583b6834e258a849c01679c4e3c007f3b4c62212393f34c2"
    ),
}
QUANT_EXTENSION_NAME = "hamutay_qjl_quant_648b3641"
SCORE_EXTENSION_NAME = "hamutay_qjl_score_648b3641"
CUDA_HOME = Path("/usr/local/cuda-12.8")
NVCC = CUDA_HOME / "bin" / "nvcc"
DEFAULT_CUDA = Path("/usr/local/cuda")
EXPECTED_DEFAULT_CUDA = Path("/usr/local/cuda-13.2")
DIMENSION = 128
GROUP_SIZE = 32
OUTLIER_COORDINATE = 127
OUTLIER_SKETCH_DIM = 8
ATOL = 1e-5
RTOL = 1e-4


def _run_text(*command: str, cwd: Path | None = None) -> str:
    completed = subprocess.run(
        list(command), cwd=cwd, check=True, capture_output=True, text=True
    )
    return completed.stdout.strip()


def _validate_compiler_and_device(device: str) -> dict[str, Any]:
    if device != "cuda:0":
        raise ValueError("the pinned author QJL kernels require --device cuda:0")
    if not torch.cuda.is_available():
        raise RuntimeError("CUDA is unavailable")
    if torch.version.cuda != "12.8":
        raise RuntimeError("PyTorch must report torch.version.cuda == 12.8")
    cuda_home = os.environ.get("CUDA_HOME")
    if cuda_home is None or Path(cuda_home).resolve() != CUDA_HOME:
        raise RuntimeError("CUDA_HOME must select /usr/local/cuda-12.8")
    selected_nvcc = shutil.which("nvcc")
    if selected_nvcc is None or Path(selected_nvcc).resolve() != NVCC:
        raise RuntimeError("/usr/local/cuda-12.8/bin must be first on PATH")
    if not NVCC.is_file():
        raise RuntimeError("/usr/local/cuda-12.8/bin/nvcc does not exist")
    try:
        resolved_default_cuda = DEFAULT_CUDA.resolve(strict=True)
    except FileNotFoundError as error:
        raise RuntimeError(
            "default /usr/local/cuda must resolve exactly to /usr/local/cuda-13.2"
        ) from error
    if resolved_default_cuda != EXPECTED_DEFAULT_CUDA:
        raise RuntimeError(
            "default /usr/local/cuda must resolve exactly to /usr/local/cuda-13.2"
        )
    nvcc_output = _run_text(str(NVCC), "--version")
    release_match = re.search(r"release\s+(\d+\.\d+)", nvcc_output)
    version_match = re.search(r"V(\d+\.\d+\.\d+)", nvcc_output)
    if release_match is None or release_match.group(1) != "12.8":
        raise RuntimeError("selected nvcc must report CUDA release 12.8")
    properties = torch.cuda.get_device_properties(0)
    return {
        "cuda_home": str(CUDA_HOME),
        "default_cuda": str(DEFAULT_CUDA),
        "default_cuda_resolved": str(resolved_default_cuda),
        "device": "cuda:0",
        "device_name": properties.name,
        "device_compute_capability": [properties.major, properties.minor],
        "nvcc": str(NVCC),
        "nvcc_release": release_match.group(1),
        "nvcc_version": version_match.group(1) if version_match else "unknown",
        "torch": torch.__version__,
        "torch_cuda": torch.version.cuda,
    }


def verify_pinned_checkout(checkout: Path) -> dict[str, Any]:
    """Verify commit, cleanliness, origin, license, and every frozen source hash."""
    resolved = Path(checkout).resolve(strict=True)
    if not resolved.is_dir():
        raise ValueError("author QJL checkout must be a directory")
    commit = _run_text("git", "rev-parse", "HEAD", cwd=resolved)
    if commit != UPSTREAM_COMMIT:
        raise ValueError(
            f"author QJL checkout commit mismatch: {commit} != {UPSTREAM_COMMIT}"
        )
    status = _run_text(
        "git", "status", "--porcelain=v1", "--untracked-files=all", cwd=resolved
    )
    if status:
        raise ValueError("author QJL checkout must be clean before compilation")
    origin = _run_text("git", "remote", "get-url", "origin", cwd=resolved)
    accepted_origins = {UPSTREAM_REPOSITORY, f"{UPSTREAM_REPOSITORY}.git"}
    if origin not in accepted_origins:
        raise ValueError(f"author QJL origin mismatch: {origin}")

    actual_hashes: dict[str, str] = {}
    for relative, expected in PINNED_SHA256.items():
        artifact = resolved / relative
        if not artifact.is_file() or artifact.is_symlink():
            raise ValueError(
                f"pinned upstream artifact is not a regular file: {relative}"
            )
        actual = sha256_file(artifact)
        if actual != expected:
            raise ValueError(
                f"pinned upstream SHA-256 mismatch for {relative}: {actual} != {expected}"
            )
        actual_hashes[relative] = actual
    return {
        "repository": UPSTREAM_REPOSITORY,
        "origin": origin,
        "commit": commit,
        "clean": True,
        "sha256": actual_hashes,
    }


def preflight_author_qjl(*, checkout: Path, device: str = "cuda:0") -> dict[str, Any]:
    """Validate every environmental and upstream prerequisite without compiling."""
    return {
        "environment": _validate_compiler_and_device(device),
        "upstream": verify_pinned_checkout(checkout),
    }


def _build_extensions(checkout: Path):
    quant_source = checkout / "qjl_kernel" / "csrc" / "qjl_quant_kernel.cu"
    score_source = checkout / "qjl_kernel" / "csrc" / "qjl_score_kernel.cu"
    quant = load(
        name=QUANT_EXTENSION_NAME,
        sources=[str(quant_source)],
        with_cuda=True,
        verbose=True,
    )
    score = load(
        name=SCORE_EXTENSION_NAME,
        sources=[str(score_source)],
        with_cuda=True,
        verbose=True,
    )
    return quant, score


def _fp32_norms(values: np.ndarray) -> np.ndarray:
    squared = np.sum(values * values, axis=-1, dtype=np.float32)
    return np.ascontiguousarray(np.sqrt(squared), dtype=np.float32)


def _differential_batch() -> dict[str, np.ndarray]:
    key_shape = (1, 1, 1, GROUP_SIZE, DIMENSION)
    query_shape = (1, 1, 1, DIMENSION)
    keys = rng_for("qualification", "author_qjl_differential", "keys").standard_normal(
        key_shape
    )
    queries = rng_for(
        "qualification", "author_qjl_differential", "query"
    ).standard_normal(query_shape)
    projection = rng_for(
        "qualification", "algorithm_2", "paper_literal", "projection"
    ).standard_normal((DIMENSION, DIMENSION))
    keys = np.ascontiguousarray(keys, dtype=np.float32)
    queries = np.ascontiguousarray(queries, dtype=np.float32)
    projection = np.ascontiguousarray(projection, dtype=np.float32)
    keys[..., OUTLIER_COORDINATE] = np.float32(0.0)
    queries[..., OUTLIER_COORDINATE] = np.float32(0.0)
    outlier_indices = np.full((1, 1, 1, 1), OUTLIER_COORDINATE, dtype=np.uint8)
    key_norms = _fp32_norms(keys)
    projected_keys = np.ascontiguousarray(keys @ projection.T, dtype=np.float32)
    if np.any(projected_keys == np.float32(0.0)):
        raise RuntimeError(
            "registered generic author-differential batch contains exact FP32 "
            "projected zeros"
        )
    query_sketch = np.ascontiguousarray(queries @ projection.T, dtype=np.float32)
    transparent_inlier_sign_bytes = pack_signs(projected_keys >= np.float32(0.0))
    transparent_signs = np.where(
        projected_keys >= np.float32(0.0), np.float32(1.0), np.float32(-1.0)
    )
    signed_sum = np.sum(
        transparent_signs * query_sketch[..., np.newaxis, :],
        axis=-1,
        dtype=np.float32,
    )
    coefficient = np.float32(np.sqrt(np.pi / 2.0) / DIMENSION)
    transparent_scores = np.ascontiguousarray(
        (coefficient * key_norms * signed_sum).reshape(1, 1, GROUP_SIZE, 1),
        dtype=np.float32,
    )
    return {
        "keys": keys,
        "queries": queries,
        "projection": projection,
        "outlier_indices": outlier_indices,
        "key_norms": key_norms,
        "query_sketch": query_sketch,
        "transparent_inlier_sign_bytes": transparent_inlier_sign_bytes,
        "transparent_scores": transparent_scores,
    }


def _to_device(values: np.ndarray, device: str) -> torch.Tensor:
    return torch.from_numpy(values).to(device=device).contiguous()


def _cpu_array(values: torch.Tensor) -> np.ndarray:
    return np.ascontiguousarray(values.detach().cpu().numpy())


def _array_record(values: np.ndarray, *, name: str) -> dict[str, Any]:
    array = np.ascontiguousarray(values)
    return {
        "dtype": array.dtype.str,
        "shape": list(array.shape),
        "sha256": sha256_array(name, array),
        "values": array.tolist(),
    }


def _comparison_record(
    arrays: Mapping[str, np.ndarray],
) -> tuple[dict[str, Any], bool]:
    author_signs = arrays["author_inlier_sign_bytes"]
    transparent_signs = arrays["transparent_inlier_sign_bytes"]
    author_outlier_norms = arrays["author_outlier_norms"]
    author_scores = arrays["author_scores"]
    transparent_scores = arrays["transparent_scores"]
    zero_author = arrays["zero_author_inlier_sign_bytes"]
    zero_transparent = arrays["zero_transparent_inlier_sign_bytes"]

    sign_bytes_equal = bool(np.array_equal(author_signs, transparent_signs))
    outlier_norms_zero = bool(np.all(author_outlier_norms == np.float32(0.0)))
    score_difference = np.abs(author_scores - transparent_scores)
    max_absolute_error = float(np.max(score_difference))
    relative_error = np.zeros_like(score_difference, dtype=np.float32)
    nonzero_reference = transparent_scores != np.float32(0.0)
    np.divide(
        score_difference,
        np.abs(transparent_scores),
        out=relative_error,
        where=nonzero_reference,
    )
    if np.any(~nonzero_reference & (score_difference != np.float32(0.0))):
        max_relative_error = None
    else:
        max_relative_error = float(np.max(relative_error))
    scores_within_tolerance = bool(
        np.allclose(
            author_scores, transparent_scores, atol=ATOL, rtol=RTOL, equal_nan=False
        )
    )
    zero_author_expected = bool(np.all(zero_author == np.uint8(0)))
    zero_transparent_expected = bool(np.all(zero_transparent == np.uint8(255)))
    zero_difference = zero_author_expected and zero_transparent_expected
    comparisons = {
        "generic_projection_has_no_exact_zero": True,
        "inlier_sign_bytes_equal": sign_bytes_equal,
        "dummy_outlier_norms_exact_zero": outlier_norms_zero,
        "scores": {
            "atol": ATOL,
            "rtol": RTOL,
            "max_absolute_error": max_absolute_error,
            "max_relative_error": max_relative_error,
            "within_tolerance": scores_within_tolerance,
        },
        "constructed_zero_projection": {
            "author_byte": int(zero_author.reshape(-1)[0]),
            "transparent_byte": int(zero_transparent.reshape(-1)[0]),
            "differing_bits_per_byte": 8,
            "expected_declared_difference": zero_difference,
        },
    }
    passed = (
        sign_bytes_equal
        and outlier_norms_zero
        and scores_within_tolerance
        and zero_difference
    )
    return comparisons, passed


def _gate_detail(comparisons: Mapping[str, Any]) -> str:
    """Describe the comparison outcome without claiming failed conditions agree."""
    failures: list[str] = []
    if not comparisons["generic_projection_has_no_exact_zero"]:
        failures.append("the generic projection contains exact FP32 zeros")
    if not comparisons["inlier_sign_bytes_equal"]:
        failures.append("packed inlier sign bytes differ")
    if not comparisons["dummy_outlier_norms_exact_zero"]:
        failures.append("dummy outlier norms are not exact zero")
    if not comparisons["scores"]["within_tolerance"]:
        failures.append(f"scores exceed atol={ATOL} and rtol={RTOL}")
    if not comparisons["constructed_zero_projection"]["expected_declared_difference"]:
        failures.append(
            "the exact-zero signs do not preserve the declared "
            "author-negative/transparent-positive difference"
        )
    if failures:
        return "Pinned author QJL differential failed: " + "; ".join(failures) + "."
    return (
        "Pinned author QJL FP32 packed inlier signs and scores agree with the "
        "transparent paper-literal reference; the dummy outlier channel is exact zero."
    )


def run_author_qjl_differential(
    *, checkout: Path, output: Path, device: str = "cuda:0"
) -> dict[str, Any]:
    """Run the frozen author differential and write canonical JSON plus NPZ."""
    preflight = preflight_author_qjl(checkout=checkout, device=device)
    environment = preflight["environment"]
    upstream = preflight["upstream"]
    resolved_checkout = Path(checkout).resolve(strict=True)
    quant_extension, score_extension = _build_extensions(resolved_checkout)
    batch = _differential_batch()

    keys = _to_device(batch["keys"], device)
    queries = _to_device(batch["queries"], device)
    projection = _to_device(batch["projection"], device)
    outlier_indices = _to_device(batch["outlier_indices"], device)
    key_norms = _to_device(batch["key_norms"], device)
    query_sketch = _to_device(batch["query_sketch"], device)

    with torch.no_grad():
        author_signs, author_outlier_signs, author_outlier_norms = (
            quant_extension.qjl_quant_float_float(
                keys, outlier_indices, projection, OUTLIER_SKETCH_DIM
            )
        )
        author_outlier_signs_evidence = _cpu_array(author_outlier_signs)
        author_scores = score_extension.qjl_score_cuda_float_float(
            author_signs,
            author_outlier_signs,
            key_norms,
            author_outlier_norms,
            outlier_indices,
            query_sketch,
            queries,
            projection.T.contiguous(),
        )
        zero_projection = torch.zeros_like(projection)
        zero_author_signs, _, _ = quant_extension.qjl_quant_float_float(
            keys, outlier_indices, zero_projection, OUTLIER_SKETCH_DIM
        )
    torch.cuda.synchronize(torch.device(device))
    if not np.array_equal(
        author_outlier_signs_evidence, _cpu_array(author_outlier_signs)
    ):
        raise RuntimeError("author score kernel mutated its outlier-sign input")

    zero_transparent = pack_signs(
        np.zeros_like(batch["keys"], dtype=np.float32) >= np.float32(0.0)
    )
    arrays = {
        **batch,
        "author_inlier_sign_bytes": _cpu_array(author_signs),
        "author_outlier_norms": _cpu_array(author_outlier_norms),
        "author_outlier_signs": author_outlier_signs_evidence,
        "author_scores": _cpu_array(author_scores),
        "zero_projection": np.zeros_like(batch["projection"], dtype=np.float32),
        "zero_author_inlier_sign_bytes": _cpu_array(zero_author_signs),
        "zero_transparent_inlier_sign_bytes": np.ascontiguousarray(
            zero_transparent, dtype=np.uint8
        ),
    }
    comparisons, passed = _comparison_record(arrays)

    output_directory = Path(output)
    output_directory.mkdir(parents=True, exist_ok=True)
    json_path = output_directory / "author_qjl_differential.json"
    npz_path = output_directory / "author_qjl_differential.npz"
    if os.path.lexists(json_path) or os.path.lexists(npz_path):
        raise FileExistsError("author QJL differential artifacts are append-only")
    artifact_arrays = {
        name: np.ascontiguousarray(arrays[name])
        for name in (
            "author_inlier_sign_bytes",
            "author_outlier_norms",
            "author_outlier_signs",
            "author_scores",
            "key_norms",
            "keys",
            "outlier_indices",
            "projection",
            "queries",
            "query_sketch",
            "transparent_inlier_sign_bytes",
            "transparent_scores",
            "zero_author_inlier_sign_bytes",
            "zero_projection",
            "zero_transparent_inlier_sign_bytes",
        )
    }
    atomic_savez(npz_path, artifact_arrays)

    detail = _gate_detail(comparisons)
    gate = {
        "name": "author_code_differential",
        "passed": passed,
        "observed": {
            "inlier_sign_bytes_equal": comparisons["inlier_sign_bytes_equal"],
            "max_absolute_score_error": comparisons["scores"]["max_absolute_error"],
            "max_relative_score_error": comparisons["scores"]["max_relative_error"],
            "outlier_norms_exact_zero": comparisons["dummy_outlier_norms_exact_zero"],
        },
        "threshold": {"atol": ATOL, "rtol": RTOL},
        "detail": detail,
    }
    result = {
        "schema": "hamutay.turboquant.author-qjl.v1",
        "status": "passed" if passed else "failed",
        "study_seed_hex": STUDY_SEED_HEX,
        "seed_fields": {
            "keys": ["qualification", "author_qjl_differential", "keys"],
            "query": ["qualification", "author_qjl_differential", "query"],
            "projection": [
                "qualification",
                "algorithm_2",
                "paper_literal",
                "projection",
            ],
        },
        "environment": environment,
        "upstream": upstream,
        "extensions": {
            "quant": QUANT_EXTENSION_NAME,
            "score": SCORE_EXTENSION_NAME,
        },
        "batch": {
            "dimension": DIMENSION,
            "key_shape": list(batch["keys"].shape),
            "query_shape": list(batch["queries"].shape),
            "outlier_index_shape": list(batch["outlier_indices"].shape),
            "outlier_sketch_dim": OUTLIER_SKETCH_DIM,
        },
        "conventions": {
            "transparent_exact_zero_sign": "positive",
            "author_exact_zero_sign": "negative",
            "bit_packing": "little-endian within each byte",
            "quant_projection_layout": "S",
            "score_projection_layout": "S.T contiguous",
            "query_sketch": "query @ S.T",
        },
        "comparisons": comparisons,
        "gate": gate,
        "arrays": {
            name: _array_record(array, name=name)
            for name, array in sorted(artifact_arrays.items())
        },
        "npz": {
            "filename": npz_path.name,
            "sha256": sha256_file(npz_path),
        },
    }
    atomic_write_json(json_path, result)
    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="author_qjl_oracle.py")
    parser.add_argument("--checkout", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--device", default="cuda:0")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    result = run_author_qjl_differential(
        checkout=args.checkout, output=args.output, device=args.device
    )
    return 0 if result["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
