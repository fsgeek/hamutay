"""Parent command for append-only TurboQuant qualification evidence."""

from __future__ import annotations

import argparse
from dataclasses import asdict
from datetime import UTC, datetime
import hashlib
import importlib.metadata
import os
from pathlib import Path
import platform
import subprocess
import sys
import traceback
from typing import Sequence
import uuid

import numpy as np

from .artifacts import (
    atomic_savez,
    atomic_write_json,
    canonical_json_bytes,
    create_run_directory,
    read_canonical_json,
    sha256_array,
    sha256_file,
)
from .codebook import lloyd_max_codebook
from .qualification import (
    QualificationConfig,
    QualificationMetrics,
    QualificationResult,
    evaluate_algorithm_gates,
)
from .rotation import canonical_qr, gaussian_rotation
from .seeding import STUDY_SEED_HEX, rng_for

CERTIFICATION_REASON = (
    "Task 7 has not joined the author_code_differential gate; this four-gate "
    "result cannot certify R1."
)

_REGISTERED_COUNTS = {
    "dimension": 128,
    "sample_count": 1_000_000,
    "batch_size": 4000,
    "bootstrap_blocks": 1000,
    "bootstrap_resamples": 10_000,
    "bits": (1, 2, 3, 4),
}

_DEVELOPMENT_COUNTS = {
    "dimension": 128,
    "sample_count": 20_000,
    "batch_size": 1000,
    "bootstrap_blocks": 100,
    "bootstrap_resamples": 200,
    "bits": (1, 2, 3, 4),
}

_DETERMINISTIC_WORKER_ENVIRONMENT = {
    "BLIS_NUM_THREADS": "1",
    "CUBLAS_WORKSPACE_CONFIG": ":4096:8",
    "MKL_NUM_THREADS": "1",
    "NUMEXPR_NUM_THREADS": "1",
    "OMP_NUM_THREADS": "1",
    "OPENBLAS_NUM_THREADS": "1",
    "PYTHONHASHSEED": "0",
    "VECLIB_MAXIMUM_THREADS": "1",
}

_MSE_PAPER_TARGETS = {1: 0.36, 2: 0.117, 3: 0.03, 4: 0.009}
_PRODUCT_PAPER_NUMERATORS = {1: 1.57, 2: 0.56, 3: 0.18, 4: 0.047}

_NUMERICAL_CONVENTIONS = {
    "construction_dtype": "FP64 for rotations and codebooks, frozen as FP32",
    "reference_dtype": "FP32 quantization, reconstruction, and diagnostics",
    "rotation": "row vectors: y = x @ rotation.T; x_hat = y_hat @ rotation",
    "qjl_projection": "projection rows; batch sketches = residual @ projection.T",
    "zero_vectors": ("zero norm, zero codes/sketches, and exact zero reconstruction"),
    "transparent_zero_sign": "+1",
    "bit_packing": "little-endian within each byte",
}

_DECLARED_LOSSES = {
    "algorithm_1": "squared L2 reconstruction error normalized by squared input norm",
    "algorithm_2_bias": (
        "estimated minus exact inner product, normalized by query norm times key norm"
    ),
    "algorithm_2_distortion": (
        "squared signed error normalized by squared query norm times squared key norm"
    ),
}


class QualificationValidationError(ValueError):
    """A pre-run validation error that must not create a run directory."""


def _bits(value: str) -> tuple[int, ...]:
    try:
        parsed = tuple(int(part) for part in value.split(","))
    except ValueError as error:
        raise argparse.ArgumentTypeError(
            "bits must be comma-separated integers"
        ) from error
    if not parsed:
        raise argparse.ArgumentTypeError("bits must be nonempty")
    return parsed


class _QualificationParser(argparse.ArgumentParser):
    def parse_args(
        self,
        args: Sequence[str] | None = None,
        namespace: argparse.Namespace | None = None,
    ) -> argparse.Namespace:
        parsed = super().parse_args(args, namespace)
        configured = {
            name for name in _REGISTERED_COUNTS if getattr(parsed, name) is not None
        }
        if parsed.profile == "registered" and configured:
            self.error(
                "registered profile freezes scientific counts; overrides are forbidden: "
                + ", ".join(sorted(configured))
            )
        defaults = (
            _REGISTERED_COUNTS
            if parsed.profile == "registered"
            else _DEVELOPMENT_COUNTS
        )
        for name, default in defaults.items():
            if getattr(parsed, name) is None:
                setattr(parsed, name, default)
        return parsed


def build_parser() -> argparse.ArgumentParser:
    """Build the frozen registered/development qualification parser."""
    parser = _QualificationParser(prog="turboquant-qualify")
    parser.add_argument(
        "--profile", choices=("development", "registered"), required=True
    )
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--dimension", type=int)
    parser.add_argument("--sample-count", type=int)
    parser.add_argument("--batch-size", type=int)
    parser.add_argument("--bootstrap-blocks", type=int)
    parser.add_argument("--bootstrap-resamples", type=int)
    parser.add_argument("--bits", type=_bits)
    parser.add_argument("--allow-dirty-path", action="append", default=[])
    return parser


def run_registered_workers(
    run_directory: Path, config_path: Path, resolved_inputs_path: Path
) -> tuple[Path, Path, Path]:
    """Launch three sequential, fresh interpreters against identical frozen inputs."""
    resolved_run_directory = Path(run_directory)
    outputs = tuple(
        resolved_run_directory / f"execution-{index}.json" for index in range(3)
    )
    if any(output.exists() for output in outputs):
        raise FileExistsError("worker execution artifacts are append-only")

    worker_env = os.environ.copy()
    worker_env.update(_DETERMINISTIC_WORKER_ENVIRONMENT)
    for index, output in enumerate(outputs):
        command = [
            sys.executable,
            "-m",
            "hamutay.turboquant.qualify_worker",
            "--config",
            str(config_path),
            "--resolved-inputs",
            str(resolved_inputs_path),
            "--execution-index",
            str(index),
            "--output",
            str(output),
        ]
        subprocess.run(command, check=True, env=worker_env)
    return outputs


def _utc_now() -> str:
    return datetime.now(UTC).isoformat(timespec="microseconds").replace("+00:00", "Z")


def _new_uuid() -> uuid.UUID:
    return uuid.uuid4()


def _configuration(args: argparse.Namespace) -> QualificationConfig:
    try:
        return QualificationConfig(
            dimension=args.dimension,
            sample_count=args.sample_count,
            batch_size=args.batch_size,
            bootstrap_blocks=args.bootstrap_blocks,
            bootstrap_resamples=args.bootstrap_resamples,
            bits=args.bits,
        )
    except (TypeError, ValueError) as error:
        raise QualificationValidationError(str(error)) from error


def _configuration_dict(config: QualificationConfig) -> dict[str, object]:
    return {
        "dimension": config.dimension,
        "sample_count": config.sample_count,
        "batch_size": config.batch_size,
        "bootstrap_blocks": config.bootstrap_blocks,
        "bootstrap_resamples": config.bootstrap_resamples,
        "bits": list(config.bits),
    }


def _git_output(repository: Path, *arguments: str) -> str:
    completed = subprocess.run(
        ["git", "-C", str(repository), *arguments],
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()


def _repository_root() -> Path:
    try:
        return Path(_git_output(Path.cwd(), "rev-parse", "--show-toplevel"))
    except (subprocess.CalledProcessError, FileNotFoundError) as error:
        raise QualificationValidationError(
            "qualification must run inside a Git worktree"
        ) from error


def _validate_output_root(profile: str, output_root: Path, repository: Path) -> Path:
    namespace_name = "development" if profile == "development" else "qualification"
    namespace = (repository / "experiments" / "turboquant" / namespace_name).resolve(
        strict=False
    )
    candidate = Path(output_root).resolve(strict=False)
    if candidate != namespace and not candidate.is_relative_to(namespace):
        raise QualificationValidationError(
            f"{profile} namespace requires --output-root at or beneath {namespace}"
        )
    return candidate


def _git_state(repository: Path) -> tuple[str, list[str]]:
    commit = _git_output(repository, "rev-parse", "HEAD")
    status = _git_output(
        repository, "status", "--porcelain=v1", "--untracked-files=all"
    )
    dirty_paths: list[str] = []
    for line in status.splitlines():
        path = line[3:]
        if " -> " in path:
            before, after = path.split(" -> ", 1)
            dirty_paths.extend((before, after))
        else:
            dirty_paths.append(path)
    return commit, sorted(set(dirty_paths))


def _validate_registered_cleanliness(
    profile: str, dirty_paths: list[str], allowed_paths: Sequence[str]
) -> None:
    if profile != "registered":
        return
    allowed = {Path(path).as_posix() for path in allowed_paths}
    unexpected = sorted(set(dirty_paths) - allowed)
    if unexpected:
        raise QualificationValidationError(
            "registered profile requires a clean worktree; unexpected dirty paths: "
            + ", ".join(unexpected)
        )


def _source_hashes(repository: Path) -> dict[str, str]:
    source_root = repository / "src" / "hamutay" / "turboquant"
    return {
        path.relative_to(repository).as_posix(): sha256_file(path)
        for path in sorted(source_root.glob("*.py"))
    }


def _package_version(distribution: str) -> str:
    try:
        return importlib.metadata.version(distribution)
    except importlib.metadata.PackageNotFoundError:
        return "not-installed"


def _accelerator_metadata() -> dict[str, object]:
    import torch

    gpus: list[dict[str, object]] = []
    if torch.cuda.is_available():
        for index in range(torch.cuda.device_count()):
            properties = torch.cuda.get_device_properties(index)
            gpus.append(
                {
                    "index": index,
                    "name": properties.name,
                    "total_memory_bytes": properties.total_memory,
                    "compute_capability": [properties.major, properties.minor],
                    "uuid": str(getattr(properties, "uuid", "unavailable")),
                }
            )
    driver_query: list[str] = []
    try:
        completed = subprocess.run(
            [
                "nvidia-smi",
                "--query-gpu=name,uuid,driver_version,memory.total",
                "--format=csv,noheader",
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        driver_query = [line for line in completed.stdout.splitlines() if line]
    except FileNotFoundError, subprocess.CalledProcessError:
        pass
    return {
        "cuda_available": torch.cuda.is_available(),
        "torch_cuda_version": torch.version.cuda,
        "driver_query": driver_query,
        "gpus": gpus,
    }


def _platform_metadata() -> dict[str, object]:
    return {
        "cpu": {
            "count": os.cpu_count(),
            "machine": platform.machine(),
            "processor": platform.processor(),
            "platform": platform.platform(),
        },
        "accelerators": _accelerator_metadata(),
    }


def _freeze_resolved_inputs(
    path: Path, config: QualificationConfig
) -> tuple[dict[str, str], str]:
    paper_projection = rng_for(
        "qualification", "algorithm_2", "paper_literal", "projection"
    ).standard_normal((config.dimension, config.dimension))
    sensitivity_source = rng_for(
        "qualification", "algorithm_2", "row_orthogonal", "projection"
    ).standard_normal((config.dimension, config.dimension))
    sensitivity_projection = canonical_qr(sensitivity_source.T).T * np.sqrt(
        config.dimension
    )
    arrays: dict[str, np.ndarray] = {
        "rotation": gaussian_rotation(
            config.dimension, "qualification", "algorithm_1", "rotation"
        ),
        "paper_projection": paper_projection,
        "sensitivity_projection": sensitivity_projection,
    }
    required_codebook_bits = sorted({*config.bits, *(bits - 1 for bits in config.bits)})
    for bits in required_codebook_bits:
        arrays[f"codebook_bits_{bits}"] = lloyd_max_codebook(config.dimension, bits)
    arrays = {
        name: np.ascontiguousarray(value, dtype=np.float32)
        for name, value in sorted(arrays.items())
    }
    atomic_savez(path, arrays)
    return (
        {name: sha256_array(name, array) for name, array in arrays.items()},
        sha256_file(path),
    )


class _RunLog:
    def __init__(self, path: Path) -> None:
        self._artifact = path.open("x", encoding="utf-8")
        self._closed = False

    def write(self, stage: str, detail: str) -> None:
        if self._closed:
            raise RuntimeError("run log is already immutable")
        self._artifact.write(f"{_utc_now()} {stage} {detail}\n")
        self._artifact.flush()
        os.fsync(self._artifact.fileno())

    def close(self) -> None:
        if not self._closed:
            self._artifact.close()
            self._closed = True


def _certification(profile: str) -> dict[str, object]:
    return {
        "scope": "development" if profile == "development" else "interim_r1",
        "certifying": False,
        "reason": CERTIFICATION_REASON,
    }


def _completion_exit_status(profile: str) -> int:
    if profile == "development":
        return 0
    if profile == "registered":
        return 1
    raise ValueError("unknown qualification profile")


def _paper_targets(config: QualificationConfig) -> dict[str, dict[str, float]]:
    return {
        "mse": {str(bits): _MSE_PAPER_TARGETS[bits] for bits in config.bits},
        "qjl_numerator": {
            str(bits): _PRODUCT_PAPER_NUMERATORS[bits] for bits in config.bits
        },
    }


def _provisional_manifest(
    *,
    args: argparse.Namespace,
    config: QualificationConfig,
    repository: Path,
    commit: str,
    dirty_paths: list[str],
    started_at: str,
) -> dict[str, object]:
    configuration = _configuration_dict(config)
    return {
        "schema": "hamutay.turboquant.manifest.v1",
        "run_id": args.run_id,
        "run_uuid": str(_new_uuid()),
        "started_at_utc": started_at,
        "ended_at_utc": None,
        "profile": args.profile,
        "status": "running",
        "certification": _certification(args.profile),
        "configuration": configuration,
        "configuration_sha256": hashlib.sha256(
            canonical_json_bytes(configuration)
        ).hexdigest(),
        "provenance": {
            "git_commit": commit,
            "dirty_paths": dirty_paths,
            "allowed_dirty_paths": sorted(args.allow_dirty_path),
            "repository": str(repository),
            "source_sha256": {},
        },
        "study": {
            "seed_hex": STUDY_SEED_HEX,
            "seed_derivation": (
                "SHA-256 of study_seed|field..., first 16 bytes interpreted as an "
                "unsigned big-endian integer; PCG64 uses the derived integer"
            ),
        },
        "software": {},
        "platform": {},
        "resolved_inputs": None,
        "source_paper_targets": _paper_targets(config),
        "numerical_conventions": _NUMERICAL_CONVENTIONS,
        "declared_losses": _DECLARED_LOSSES,
        "artifact_sha256": {},
    }


def _read_execution(path: Path) -> dict[str, object]:
    value = read_canonical_json(path)
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def _compare_worker_outputs(
    outputs: tuple[Path, Path, Path],
    *,
    configuration_sha256: str,
    resolved_inputs_sha256: str,
    parent_pid: int,
) -> dict[str, object]:
    if len(outputs) != 3:
        raise ValueError("process determinism requires exactly three executions")
    records = [_read_execution(path) for path in outputs]
    payload_bytes: list[bytes] = []
    deterministic_evidence_bytes: list[bytes] = []
    worker_pids: list[int] = []
    for expected_index, record in enumerate(records):
        if record.get("schema") != "hamutay.turboquant.execution.v1":
            raise ValueError("worker execution has the wrong schema")
        if record.get("status") != "passed":
            raise ValueError("worker execution did not pass")
        if record.get("execution_index") != expected_index:
            raise ValueError("worker execution index does not match its artifact name")
        if record.get("configuration_sha256") != configuration_sha256:
            raise ValueError("worker configuration hash differs from the parent")
        if record.get("resolved_inputs_sha256") != resolved_inputs_sha256:
            raise ValueError("worker resolved-input hash differs from the parent")
        provenance = record.get("provenance")
        if not isinstance(provenance, dict):
            raise ValueError("worker provenance is missing")
        pid = provenance.get("pid")
        if not isinstance(pid, int) or pid == parent_pid:
            raise ValueError("worker did not prove a fresh child process")
        if provenance.get("parent_pid") != parent_pid:
            raise ValueError("worker parent PID does not match the launching parent")
        worker_pids.append(pid)
        deterministic_evidence = dict(record)
        deterministic_evidence.pop("execution_index")
        deterministic_provenance = dict(provenance)
        deterministic_provenance.pop("pid")
        deterministic_evidence["provenance"] = deterministic_provenance
        deterministic_evidence_bytes.append(
            canonical_json_bytes(deterministic_evidence)
        )
        payload = record.get("determinism_payload")
        if not isinstance(payload, dict):
            raise ValueError("worker determinism payload is missing")
        encoded = canonical_json_bytes(payload)
        if (
            record.get("determinism_payload_sha256")
            != hashlib.sha256(encoded).hexdigest()
        ):
            raise ValueError("worker determinism payload hash is invalid")
        payload_bytes.append(encoded)
    if len(set(worker_pids)) != 3:
        raise ValueError("process determinism requires three distinct worker PIDs")
    if not (
        deterministic_evidence_bytes[0]
        == deterministic_evidence_bytes[1]
        == deterministic_evidence_bytes[2]
    ):
        raise ValueError("worker deterministic evidence is not byte-identical")
    return {
        "canonical_payload_sha256": hashlib.sha256(payload_bytes[0]).hexdigest(),
        "execution_indices": [0, 1, 2],
        "passed": True,
        "worker_pids": worker_pids,
    }


def _result_from_execution(
    execution: dict[str, object], config: QualificationConfig
) -> QualificationResult:
    payload = execution.get("determinism_payload")
    if not isinstance(payload, dict):
        raise ValueError("execution determinism payload is missing")
    metrics_value = payload.get("metrics")
    if not isinstance(metrics_value, list):
        raise ValueError("execution metrics are missing")
    expected_metric_hash = hashlib.sha256(
        canonical_json_bytes(metrics_value)
    ).hexdigest()
    if payload.get("metric_sha256") != expected_metric_hash:
        raise ValueError("execution metric hash is invalid")
    metrics = tuple(QualificationMetrics(**value) for value in metrics_value)
    return QualificationResult(
        metrics=metrics,
        determinism_passed=True,
        sample_count=config.sample_count,
        batch_size=config.batch_size,
        bootstrap_blocks=config.bootstrap_blocks,
        bootstrap_resamples=config.bootstrap_resamples,
        dimension=config.dimension,
        configuration=config,
    )


def _existing_artifact_hashes(
    run_directory: Path, *, include_manifest: bool
) -> dict[str, str]:
    return {
        path.name: sha256_file(path)
        for path in sorted(run_directory.iterdir())
        if path.is_file()
        and not path.name.startswith(".")
        and path.name != "qualification.json"
        and (include_manifest or path.name != "manifest.json")
    }


def _terminal_error_record(
    *,
    args: argparse.Namespace,
    error: BaseException,
    traceback_text: str,
    artifact_hashes: dict[str, str],
    recovery_errors: list[dict[str, str]],
) -> dict[str, object]:
    return {
        "schema": "hamutay.turboquant.qualification.v1",
        "run_id": args.run_id,
        "profile": args.profile,
        "status": "error",
        "certification": _certification(args.profile),
        "metrics": [],
        "gates": [],
        "process_determinism": None,
        "declared_losses": _DECLARED_LOSSES,
        "numerical_conventions": _NUMERICAL_CONVENTIONS,
        "artifact_sha256": artifact_hashes,
        "error": {
            "type": type(error).__name__,
            "message": str(error),
            "traceback": traceback_text,
        },
        "recovery_errors": recovery_errors,
    }


def _emergency_manifest(
    *,
    args: argparse.Namespace,
    config: QualificationConfig,
    repository: Path,
    commit: str,
    dirty_paths: list[str],
) -> dict[str, object]:
    """Return a no-fail, partial manifest suitable for terminal recovery."""
    return {
        "schema": "hamutay.turboquant.manifest.v1",
        "run_id": args.run_id,
        "run_uuid": None,
        "started_at_utc": None,
        "ended_at_utc": None,
        "profile": args.profile,
        "status": "running",
        "certification": _certification(args.profile),
        "configuration": _configuration_dict(config),
        "configuration_sha256": None,
        "provenance": {
            "git_commit": commit,
            "dirty_paths": dirty_paths,
            "allowed_dirty_paths": sorted(args.allow_dirty_path),
            "repository": str(repository),
            "source_sha256": {},
        },
        "study": {
            "seed_hex": STUDY_SEED_HEX,
            "seed_derivation": (
                "SHA-256 of study_seed|field..., first 16 bytes interpreted as an "
                "unsigned big-endian integer; PCG64 uses the derived integer"
            ),
        },
        "software": {},
        "platform": {},
        "resolved_inputs": None,
        "source_paper_targets": _paper_targets(config),
        "numerical_conventions": _NUMERICAL_CONVENTIONS,
        "declared_losses": _DECLARED_LOSSES,
        "artifact_sha256": {},
    }


def _record_recovery_error(
    recovery_errors: list[dict[str, str]], stage: str, error: BaseException
) -> None:
    recovery_errors.append(
        {"stage": stage, "type": type(error).__name__, "message": str(error)}
    )


def _best_effort_hashes(
    run_directory: Path,
    *,
    include_manifest: bool,
    recovery_errors: list[dict[str, str]],
) -> dict[str, str]:
    try:
        return _existing_artifact_hashes(
            run_directory, include_manifest=include_manifest
        )
    except BaseException as error:
        _record_recovery_error(recovery_errors, "artifact_hashes", error)
        return {}


def _publish_terminal_error(
    *,
    args: argparse.Namespace,
    config: QualificationConfig,
    repository: Path,
    commit: str,
    dirty_paths: list[str],
    run_directory: Path,
    run_log: _RunLog | None,
    manifest: dict[str, object] | None,
    original_error: BaseException,
    traceback_text: str,
) -> None:
    """Best-effort terminal publication that never masks the original error."""
    recovery_errors: list[dict[str, str]] = []
    if run_log is not None:
        try:
            run_log.write(
                "error",
                f"{type(original_error).__name__}: {original_error}; retaining partial evidence",
            )
            run_log.write(
                "terminal", "terminal error artifact written; run is immutable"
            )
        except BaseException as error:
            _record_recovery_error(recovery_errors, "run_log_write", error)
        try:
            run_log.close()
        except BaseException as error:
            _record_recovery_error(recovery_errors, "run_log_close", error)

    if manifest is None:
        try:
            manifest = _emergency_manifest(
                args=args,
                config=config,
                repository=repository,
                commit=commit,
                dirty_paths=dirty_paths,
            )
        except BaseException as error:
            _record_recovery_error(recovery_errors, "emergency_manifest", error)
            manifest = {
                "schema": "hamutay.turboquant.manifest.v1",
                "run_id": str(getattr(args, "run_id", "unknown")),
                "profile": str(getattr(args, "profile", "unknown")),
            }
    manifest["ended_at_utc"] = None
    try:
        manifest["ended_at_utc"] = _utc_now()
    except BaseException as error:
        _record_recovery_error(recovery_errors, "ended_at_utc", error)
    manifest["status"] = "error"
    manifest["artifact_sha256"] = _best_effort_hashes(
        run_directory,
        include_manifest=False,
        recovery_errors=recovery_errors,
    )
    manifest_path = run_directory / "manifest.json"
    try:
        atomic_write_json(
            manifest_path,
            manifest,
            replace=os.path.lexists(manifest_path),
        )
    except BaseException as error:
        _record_recovery_error(recovery_errors, "terminal_manifest", error)

    artifact_hashes = _best_effort_hashes(
        run_directory,
        include_manifest=True,
        recovery_errors=recovery_errors,
    )
    qualification_path = run_directory / "qualification.json"
    try:
        atomic_write_json(
            qualification_path,
            _terminal_error_record(
                args=args,
                error=original_error,
                traceback_text=traceback_text,
                artifact_hashes=artifact_hashes,
                recovery_errors=recovery_errors,
            ),
        )
    except BaseException:
        # No remaining append-only channel exists for a qualification writer
        # failure. Preserve the original exception rather than masking it.
        pass


def execute_qualification(args: argparse.Namespace) -> int:
    """Execute one append-only qualification, retaining terminal error evidence."""
    config = _configuration(args)
    repository = _repository_root()
    args.output_root = _validate_output_root(args.profile, args.output_root, repository)
    commit, dirty_paths = _git_state(repository)
    _validate_registered_cleanliness(args.profile, dirty_paths, args.allow_dirty_path)

    try:
        run_directory = create_run_directory(args.output_root, args.run_id)
    except (FileExistsError, ValueError) as error:
        raise QualificationValidationError(str(error)) from error
    manifest_path = run_directory / "manifest.json"
    qualification_path = run_directory / "qualification.json"
    resolved_inputs_path = run_directory / "resolved_inputs.npz"
    run_log: _RunLog | None = None
    manifest: dict[str, object] | None = None
    worker_config_path: Path | None = None
    terminal_written = False
    try:
        run_log = _RunLog(run_directory / "run.log")
        started_at = _utc_now()
        manifest = _provisional_manifest(
            args=args,
            config=config,
            repository=repository,
            commit=commit,
            dirty_paths=dirty_paths,
            started_at=started_at,
        )
        worker_config_path = run_directory.parent / (
            f".{args.run_id}.worker-config.{_new_uuid().hex}.json"
        )
        atomic_write_json(manifest_path, manifest)
        run_log.write("manifest", "provisional manifest written")
        manifest["provenance"]["source_sha256"] = _source_hashes(repository)
        manifest["software"] = {
            "python": platform.python_version(),
            "numpy": _package_version("numpy"),
            "scipy": _package_version("scipy"),
            "torch": _package_version("torch"),
        }
        manifest["platform"] = _platform_metadata()
        run_log.write("inputs", "constructing resolved FP32 arrays")
        array_hashes, resolved_inputs_sha256 = _freeze_resolved_inputs(
            resolved_inputs_path, config
        )
        manifest["resolved_inputs"] = {
            "filename": resolved_inputs_path.name,
            "file_sha256": resolved_inputs_sha256,
            "array_sha256": array_hashes,
        }
        worker_config = {
            "schema": "hamutay.turboquant.worker-config.v1",
            "configuration": _configuration_dict(config),
            "resolved_inputs_sha256": resolved_inputs_sha256,
        }
        atomic_write_json(worker_config_path, worker_config)
        configuration_sha256 = sha256_file(worker_config_path)
        manifest["worker_configuration_sha256"] = configuration_sha256
        run_log.write("workers", "launching three sequential fresh processes")
        outputs = run_registered_workers(
            run_directory, worker_config_path, resolved_inputs_path
        )
        process_determinism = _compare_worker_outputs(
            outputs,
            configuration_sha256=configuration_sha256,
            resolved_inputs_sha256=resolved_inputs_sha256,
            parent_pid=os.getpid(),
        )
        first_execution = _read_execution(outputs[0])
        result = _result_from_execution(first_execution, config)
        gates = tuple(evaluate_algorithm_gates(result))
        status = "passed" if all(gate.passed for gate in gates) else "failed"
        run_log.write("gates", f"four interim gates evaluated with status {status}")
        run_log.write("terminal", "terminal artifacts written; run is now immutable")
        run_log.close()

        manifest["ended_at_utc"] = _utc_now()
        manifest["status"] = status
        manifest["artifact_sha256"] = _existing_artifact_hashes(
            run_directory, include_manifest=False
        )
        atomic_write_json(manifest_path, manifest, replace=True)
        artifact_hashes = _existing_artifact_hashes(
            run_directory, include_manifest=True
        )
        qualification = {
            "schema": "hamutay.turboquant.qualification.v1",
            "run_id": args.run_id,
            "profile": args.profile,
            "status": status,
            "certification": _certification(args.profile),
            "metrics": [asdict(metric) for metric in result.metrics],
            "gates": [asdict(gate) for gate in gates],
            "process_determinism": process_determinism,
            "declared_losses": _DECLARED_LOSSES,
            "numerical_conventions": _NUMERICAL_CONVENTIONS,
            "artifact_sha256": artifact_hashes,
        }
        atomic_write_json(qualification_path, qualification)
        terminal_written = True
        return _completion_exit_status(args.profile)
    except BaseException as error:
        if terminal_written:
            raise
        traceback_text = traceback.format_exc()
        _publish_terminal_error(
            args=args,
            config=config,
            repository=repository,
            commit=commit,
            dirty_paths=dirty_paths,
            run_directory=run_directory,
            run_log=run_log,
            manifest=manifest,
            original_error=error,
            traceback_text=traceback_text,
        )
        raise
    finally:
        if worker_config_path is not None:
            try:
                worker_config_path.unlink(missing_ok=True)
            except OSError:
                pass


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return execute_qualification(args)
    except QualificationValidationError as error:
        parser.error(str(error))
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
