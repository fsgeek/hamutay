from dataclasses import asdict
import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
import zipfile

import numpy as np
import pytest

from hamutay.turboquant.artifacts import canonical_json_bytes, sha256_file
from hamutay.turboquant.qualify import (
    CERTIFICATION_REASON,
    QualificationValidationError,
    _completion_exit_status,
    _compare_worker_outputs,
    _validate_registered_cleanliness,
    build_parser,
    execute_qualification,
    run_registered_workers,
)
from hamutay.turboquant.qualification import (
    QualificationConfig,
    run_synthetic_qualification,
)


def _load_canonical_json(path: Path) -> dict:
    raw = path.read_bytes()
    value = json.loads(raw)
    assert raw == canonical_json_bytes(value)
    return value


@pytest.fixture
def development_output_root(tmp_path: Path):
    repository = Path(__file__).resolve().parents[2]
    output_root = (
        repository
        / "experiments"
        / "turboquant"
        / "development"
        / f"pytest-{tmp_path.name}"
    )
    try:
        yield output_root
    finally:
        shutil.rmtree(output_root, ignore_errors=True)


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

    with pytest.raises(SystemExit) as error:
        parser.parse_args(
            [
                "--profile",
                "registered",
                "--output-root",
                "out",
                "--run-id",
                "r1",
                "--sample-count",
                "10",
            ]
        )

    assert error.value.code != 0


@pytest.mark.parametrize(
    ("flag", "value"),
    [
        ("--dimension", "64"),
        ("--batch-size", "2000"),
        ("--bootstrap-blocks", "500"),
        ("--bootstrap-resamples", "5000"),
        ("--bits", "1,2"),
    ],
)
def test_registered_profile_rejects_every_scientific_override(flag, value):
    with pytest.raises(SystemExit) as error:
        build_parser().parse_args(
            [
                "--profile",
                "registered",
                "--output-root",
                "out",
                "--run-id",
                "r1",
                flag,
                value,
            ]
        )

    assert error.value.code == 2


def test_registered_profile_uses_divisible_batch_size():
    args = build_parser().parse_args(
        ["--profile", "registered", "--output-root", "out", "--run-id", "r1"]
    )

    assert args.batch_size == 4000
    assert args.sample_count % args.batch_size == 0


def test_interim_exit_policy_distinguishes_development_from_registered():
    assert _completion_exit_status("development") == 0
    assert _completion_exit_status("registered") == 1


def test_registered_cleanliness_allows_only_exact_declared_dirty_paths():
    _validate_registered_cleanliness("registered", ["declared.txt"], ["declared.txt"])

    with pytest.raises(ValueError, match="unexpected.txt"):
        _validate_registered_cleanliness(
            "registered",
            ["declared.txt", "unexpected.txt"],
            ["declared.txt"],
        )


def _namespace_args(profile: str, output_root: Path, run_id: str):
    command = [
        "--profile",
        profile,
        "--output-root",
        str(output_root),
        "--run-id",
        run_id,
    ]
    if profile == "development":
        command.extend(
            [
                "--dimension",
                "8",
                "--sample-count",
                "24",
                "--batch-size",
                "12",
                "--bootstrap-blocks",
                "6",
                "--bootstrap-resamples",
                "11",
                "--bits",
                "1",
            ]
        )
    return build_parser().parse_args(command)


def test_development_rejects_arbitrary_output_root_before_run_creation(tmp_path):
    output_root = tmp_path / "arbitrary"

    with pytest.raises(QualificationValidationError, match="development namespace"):
        execute_qualification(_namespace_args("development", output_root, "outside"))

    assert not (output_root / "outside").exists()


def test_development_rejects_cross_profile_parent_traversal_before_creation(
    tmp_path,
):
    repository = Path(__file__).resolve().parents[2]
    development = repository / "experiments" / "turboquant" / "development"
    output_root = development / ".." / "qualification" / f"pytest-{tmp_path.name}"

    with pytest.raises(QualificationValidationError, match="development namespace"):
        execute_qualification(_namespace_args("development", output_root, "cross"))

    assert not (output_root.resolve() / "cross").exists()


def test_registered_rejects_development_namespace_before_cleanliness(tmp_path):
    repository = Path(__file__).resolve().parents[2]
    output_root = (
        repository
        / "experiments"
        / "turboquant"
        / "development"
        / f"registered-{tmp_path.name}"
    )

    with pytest.raises(QualificationValidationError, match="registered namespace"):
        execute_qualification(_namespace_args("registered", output_root, "cross"))

    assert not (output_root / "cross").exists()


def test_development_rejects_symlink_that_resolves_outside_namespace(tmp_path):
    repository = Path(__file__).resolve().parents[2]
    base = repository / "experiments" / "turboquant" / "development"
    base.mkdir(parents=True, exist_ok=True)
    output_root = base / f"symlink-{tmp_path.name}"
    outside = tmp_path / "outside"
    outside.mkdir()
    output_root.symlink_to(outside, target_is_directory=True)
    try:
        with pytest.raises(QualificationValidationError, match="development namespace"):
            execute_qualification(
                _namespace_args("development", output_root, "escaped")
            )

        assert not (outside / "escaped").exists()
    finally:
        output_root.unlink(missing_ok=True)


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
    assert [command[command.index("--execution-index") + 1] for command in calls] == [
        "0",
        "1",
        "2",
    ]
    assert all(
        command[:3] == [sys.executable, "-m", "hamutay.turboquant.qualify_worker"]
        for command in calls
    )
    assert outputs == tuple(tmp_path / f"execution-{index}.json" for index in range(3))


def test_registered_workers_freeze_numerical_environment(monkeypatch, tmp_path):
    environments: list[dict[str, str]] = []

    def fake_run(command, *, check, env):
        environments.append(env)
        Path(command[command.index("--output") + 1]).write_text(
            "{}\n", encoding="utf-8"
        )

    monkeypatch.setattr(subprocess, "run", fake_run)
    run_registered_workers(tmp_path, tmp_path / "config.json", tmp_path / "inputs.npz")

    assert len(environments) == 3
    assert all(environment["PYTHONHASHSEED"] == "0" for environment in environments)
    assert all(environment["OMP_NUM_THREADS"] == "1" for environment in environments)
    assert all(
        environment["OPENBLAS_NUM_THREADS"] == "1" for environment in environments
    )
    assert environments[0] == environments[1] == environments[2]


def test_registered_workers_refuse_any_existing_execution_before_launch(
    monkeypatch, tmp_path
):
    existing = tmp_path / "execution-1.json"
    existing.write_bytes(b"preserve me\n")
    called = False

    def fake_run(command, *, check, env):
        nonlocal called
        called = True

    monkeypatch.setattr(subprocess, "run", fake_run)

    with pytest.raises(FileExistsError):
        run_registered_workers(
            tmp_path, tmp_path / "config.json", tmp_path / "inputs.npz"
        )

    assert not called
    assert existing.read_bytes() == b"preserve me\n"


def _execution_fixture(index: int, *, payload: dict | None = None) -> dict:
    determinism_payload = payload or {
        "metric_sha256": "1" * 64,
        "stream_sha256": {"codes": "2" * 64},
    }
    return {
        "schema": "hamutay.turboquant.execution.v1",
        "status": "passed",
        "execution_index": index,
        "configuration_sha256": "3" * 64,
        "resolved_inputs_sha256": "4" * 64,
        "provenance": {
            "pid": 100 + index,
            "parent_pid": os.getpid(),
            "worker_environment": {
                "PYTHONHASHSEED": "0",
                "OMP_NUM_THREADS": "1",
                "OPENBLAS_NUM_THREADS": "1",
            },
        },
        "stdout": "",
        "stderr": "",
        "determinism_payload": determinism_payload,
        "determinism_payload_sha256": hashlib.sha256(
            canonical_json_bytes(determinism_payload)
        ).hexdigest(),
    }


def test_process_comparison_requires_canonical_byte_identical_payloads(tmp_path):
    paths = tuple(tmp_path / f"execution-{index}.json" for index in range(3))
    for index, path in enumerate(paths):
        path.write_bytes(canonical_json_bytes(_execution_fixture(index)))

    comparison = _compare_worker_outputs(
        paths,
        configuration_sha256="3" * 64,
        resolved_inputs_sha256="4" * 64,
        parent_pid=os.getpid(),
    )

    assert comparison == {
        "canonical_payload_sha256": hashlib.sha256(
            canonical_json_bytes(_execution_fixture(0)["determinism_payload"])
        ).hexdigest(),
        "execution_indices": [0, 1, 2],
        "passed": True,
        "worker_pids": [100, 101, 102],
    }


def test_process_comparison_rejects_one_differing_child(tmp_path):
    paths = tuple(tmp_path / f"execution-{index}.json" for index in range(3))
    for index, path in enumerate(paths):
        payload = None if index < 2 else {"metric_sha256": "9" * 64}
        path.write_bytes(
            canonical_json_bytes(_execution_fixture(index, payload=payload))
        )


@pytest.mark.parametrize(
    ("field", "differing_value"),
    [
        ("worker_environment", "2"),
        ("stdout", "unexpected output\n"),
        ("stderr", "unexpected error output\n"),
    ],
)
def test_process_comparison_rejects_differing_deterministic_evidence(
    tmp_path, field, differing_value
):
    paths = tuple(tmp_path / f"execution-{index}.json" for index in range(3))
    for index, path in enumerate(paths):
        record = _execution_fixture(index)
        if index == 2 and field == "worker_environment":
            record["provenance"]["worker_environment"]["OMP_NUM_THREADS"] = (
                differing_value
            )
        elif index == 2:
            record[field] = differing_value
        path.write_bytes(canonical_json_bytes(record))

    with pytest.raises(ValueError, match="deterministic evidence"):
        _compare_worker_outputs(
            paths,
            configuration_sha256="3" * 64,
            resolved_inputs_sha256="4" * 64,
            parent_pid=os.getpid(),
        )

    with pytest.raises(ValueError, match="byte-identical"):
        _compare_worker_outputs(
            paths,
            configuration_sha256="3" * 64,
            resolved_inputs_sha256="4" * 64,
            parent_pid=os.getpid(),
        )


def test_process_comparison_rejects_noncanonical_child_record(tmp_path):
    paths = tuple(tmp_path / f"execution-{index}.json" for index in range(3))
    for index, path in enumerate(paths):
        record = _execution_fixture(index)
        if index == 1:
            path.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
        else:
            path.write_bytes(canonical_json_bytes(record))

    with pytest.raises(ValueError, match="canonical JSON"):
        _compare_worker_outputs(
            paths,
            configuration_sha256="3" * 64,
            resolved_inputs_sha256="4" * 64,
            parent_pid=os.getpid(),
        )


def test_development_cli_writes_complete_noncertifying_fresh_process_evidence(
    development_output_root,
):
    output_root = development_output_root
    run_id = "fresh-processes"
    command = [
        sys.executable,
        "-m",
        "hamutay.turboquant.qualify",
        "--profile",
        "development",
        "--output-root",
        str(output_root),
        "--run-id",
        run_id,
        "--dimension",
        "8",
        "--sample-count",
        "240",
        "--batch-size",
        "60",
        "--bootstrap-blocks",
        "12",
        "--bootstrap-resamples",
        "31",
        "--bits",
        "1",
    ]

    completed = subprocess.run(command, check=False, capture_output=True, text=True)

    assert completed.returncode == 0, completed.stderr
    run_directory = output_root / run_id
    expected_names = {
        "manifest.json",
        "resolved_inputs.npz",
        "execution-0.json",
        "execution-1.json",
        "execution-2.json",
        "qualification.json",
        "run.log",
    }
    assert {path.name for path in run_directory.iterdir()} == expected_names

    manifest = _load_canonical_json(run_directory / "manifest.json")
    qualification = _load_canonical_json(run_directory / "qualification.json")
    executions = [
        _load_canonical_json(run_directory / f"execution-{index}.json")
        for index in range(3)
    ]

    certification = {
        "certifying": False,
        "reason": CERTIFICATION_REASON,
        "scope": "development",
    }
    assert manifest["schema"] == "hamutay.turboquant.manifest.v1"
    assert manifest["status"] in {"passed", "failed"}
    assert manifest["certification"] == certification
    assert manifest["run_id"] == run_id
    assert manifest["run_uuid"]
    assert manifest["started_at_utc"].endswith("Z")
    assert manifest["ended_at_utc"].endswith("Z")
    assert manifest["configuration"] == {
        "batch_size": 60,
        "bits": [1],
        "bootstrap_blocks": 12,
        "bootstrap_resamples": 31,
        "dimension": 8,
        "sample_count": 240,
    }
    assert len(manifest["provenance"]["git_commit"]) == 40
    assert isinstance(manifest["provenance"]["dirty_paths"], list)
    assert manifest["study"]["seed_hex"] == "0b311d5d4eceaf773efde389305a1b5a"
    assert manifest["study"]["seed_derivation"]
    assert {"numpy", "scipy", "torch", "python"} <= manifest["software"].keys()
    assert {"cpu", "accelerators"} <= manifest["platform"].keys()
    assert {
        "rotation",
        "codebook_bits_0",
        "codebook_bits_1",
        "paper_projection",
        "sensitivity_projection",
    } == manifest["resolved_inputs"]["array_sha256"].keys()
    assert manifest["source_paper_targets"]["mse"] == {"1": 0.36}
    assert manifest["source_paper_targets"]["qjl_numerator"] == {"1": 1.57}
    assert manifest["provenance"]["source_sha256"]

    assert qualification["schema"] == "hamutay.turboquant.qualification.v1"
    assert qualification["status"] == manifest["status"]
    assert qualification["certification"] == certification
    assert [gate["name"] for gate in qualification["gates"]] == [
        "round_trip_determinism",
        "mse_distortion",
        "qjl_bias_equivalence",
        "published_qjl_distortion",
    ]
    assert qualification["gates"][0]["passed"] is True
    assert "author_code_differential" not in json.dumps(qualification["gates"])
    assert qualification["process_determinism"]["passed"] is True
    assert len(qualification["metrics"]) == 1
    assert np.isfinite(qualification["metrics"][0]["mse_observed"])
    expected_result = run_synthetic_qualification(
        QualificationConfig(
            dimension=8,
            sample_count=240,
            batch_size=60,
            bootstrap_blocks=12,
            bootstrap_resamples=31,
            bits=(1,),
        )
    )
    expected_metrics = json.loads(
        canonical_json_bytes([asdict(metric) for metric in expected_result.metrics])
    )
    assert qualification["metrics"] == expected_metrics
    assert qualification["declared_losses"]
    assert qualification["numerical_conventions"]

    assert "manifest.json" not in manifest["artifact_sha256"]
    for name, digest in manifest["artifact_sha256"].items():
        assert digest == sha256_file(run_directory / name)

    pids = [execution["provenance"]["pid"] for execution in executions]
    parent_pids = {execution["provenance"]["parent_pid"] for execution in executions}
    assert len(set(pids)) == 3
    assert len(parent_pids) == 1
    assert not set(pids) & parent_pids
    assert [execution["execution_index"] for execution in executions] == [0, 1, 2]
    assert all(execution["status"] == "passed" for execution in executions)
    assert all(execution["stdout"] == "" for execution in executions)
    assert all(execution["stderr"] == "" for execution in executions)
    assert all(
        execution["configuration_sha256"] == manifest["worker_configuration_sha256"]
        for execution in executions
    )
    assert all(
        execution["resolved_inputs_sha256"]
        == manifest["resolved_inputs"]["file_sha256"]
        for execution in executions
    )
    payload_bytes = [
        canonical_json_bytes(execution["determinism_payload"])
        for execution in executions
    ]
    assert payload_bytes[0] == payload_bytes[1] == payload_bytes[2]

    for name, digest in qualification["artifact_sha256"].items():
        assert digest == sha256_file(run_directory / name)
    with zipfile.ZipFile(run_directory / "resolved_inputs.npz") as archive:
        assert all(
            info.compress_type == zipfile.ZIP_STORED for info in archive.infolist()
        )
    with np.load(run_directory / "resolved_inputs.npz", allow_pickle=False) as inputs:
        assert inputs["rotation"].dtype == np.float32
        assert inputs["paper_projection"].shape == (8, 8)
        assert inputs["sensitivity_projection"].shape == (8, 8)
    assert "terminal artifacts written" in (run_directory / "run.log").read_text()
    assert not list(output_root.glob(f".{run_id}.worker-config.*.json"))

    before = {name: sha256_file(run_directory / name) for name in expected_names}
    repeated = subprocess.run(command, check=False, capture_output=True, text=True)
    assert repeated.returncode != 0
    assert before == {
        name: sha256_file(run_directory / name) for name in expected_names
    }


def test_development_cli_real_process_supports_bit_subset_without_total_bit_one(
    development_output_root,
):
    run_id = "bits-two-only"
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "hamutay.turboquant.qualify",
            "--profile",
            "development",
            "--output-root",
            str(development_output_root),
            "--run-id",
            run_id,
            "--dimension",
            "8",
            "--sample-count",
            "24",
            "--batch-size",
            "12",
            "--bootstrap-blocks",
            "6",
            "--bootstrap-resamples",
            "11",
            "--bits",
            "2",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
    run_directory = development_output_root / run_id
    qualification = _load_canonical_json(run_directory / "qualification.json")
    assert qualification["status"] in {"passed", "failed"}
    assert [metric["bits"] for metric in qualification["metrics"]] == [2]
    with np.load(run_directory / "resolved_inputs.npz", allow_pickle=False) as inputs:
        assert set(inputs.files) == {
            "rotation",
            "paper_projection",
            "sensitivity_projection",
            "codebook_bits_1",
            "codebook_bits_2",
        }
    assert [
        _load_canonical_json(run_directory / f"execution-{index}.json")[
            "execution_index"
        ]
        for index in range(3)
    ] == [0, 1, 2]


def test_execution_exception_preserves_partial_run_and_terminal_error(
    monkeypatch, development_output_root
):
    output_root = development_output_root
    args = build_parser().parse_args(
        [
            "--profile",
            "development",
            "--output-root",
            str(output_root),
            "--run-id",
            "partial",
            "--dimension",
            "8",
            "--sample-count",
            "24",
            "--batch-size",
            "12",
            "--bootstrap-blocks",
            "6",
            "--bootstrap-resamples",
            "11",
            "--bits",
            "1",
        ]
    )

    def fail_workers(*_args, **_kwargs):
        raise RuntimeError("controlled worker failure")

    monkeypatch.setattr(
        "hamutay.turboquant.qualify.run_registered_workers", fail_workers
    )

    with pytest.raises(RuntimeError, match="controlled worker failure"):
        execute_qualification(args)

    run_directory = output_root / "partial"
    manifest = _load_canonical_json(run_directory / "manifest.json")
    qualification = _load_canonical_json(run_directory / "qualification.json")
    assert manifest["status"] == "error"
    assert qualification["status"] == "error"
    assert qualification["certification"] == {
        "certifying": False,
        "reason": CERTIFICATION_REASON,
        "scope": "development",
    }
    assert qualification["error"]["type"] == "RuntimeError"
    assert qualification["error"]["message"] == "controlled worker failure"
    assert "controlled worker failure" in (run_directory / "run.log").read_text()
    assert not any(path.name.endswith(".tmp") for path in run_directory.iterdir())


def test_metadata_exception_after_directory_creation_is_terminally_recorded(
    monkeypatch, development_output_root
):
    output_root = development_output_root
    args = build_parser().parse_args(
        [
            "--profile",
            "development",
            "--output-root",
            str(output_root),
            "--run-id",
            "metadata-error",
            "--dimension",
            "8",
            "--sample-count",
            "24",
            "--batch-size",
            "12",
            "--bootstrap-blocks",
            "6",
            "--bootstrap-resamples",
            "11",
            "--bits",
            "1",
        ]
    )

    def fail_metadata():
        raise RuntimeError("controlled metadata failure")

    monkeypatch.setattr("hamutay.turboquant.qualify._platform_metadata", fail_metadata)

    with pytest.raises(RuntimeError, match="controlled metadata failure"):
        execute_qualification(args)

    run_directory = output_root / "metadata-error"
    assert _load_canonical_json(run_directory / "manifest.json")["status"] == "error"
    qualification = _load_canonical_json(run_directory / "qualification.json")
    assert qualification["status"] == "error"
    assert qualification["error"]["message"] == "controlled metadata failure"


def test_uuid_failure_after_directory_creation_still_writes_terminal_error(
    monkeypatch, development_output_root
):
    output_root = development_output_root
    args = build_parser().parse_args(
        [
            "--profile",
            "development",
            "--output-root",
            str(output_root),
            "--run-id",
            "uuid-error",
            "--dimension",
            "8",
            "--sample-count",
            "24",
            "--batch-size",
            "12",
            "--bootstrap-blocks",
            "6",
            "--bootstrap-resamples",
            "11",
            "--bits",
            "1",
        ]
    )
    monkeypatch.setattr(
        "hamutay.turboquant.qualify._new_uuid",
        lambda: (_ for _ in ()).throw(RuntimeError("controlled UUID failure")),
    )

    with pytest.raises(RuntimeError, match="controlled UUID failure"):
        execute_qualification(args)

    run_directory = output_root / "uuid-error"
    manifest = _load_canonical_json(run_directory / "manifest.json")
    qualification = _load_canonical_json(run_directory / "qualification.json")
    assert manifest["status"] == "error"
    assert qualification["status"] == "error"
    assert qualification["error"]["message"] == "controlled UUID failure"


def test_final_hash_failure_after_log_close_preserves_original_terminal_error(
    monkeypatch, development_output_root
):
    output_root = development_output_root
    args = build_parser().parse_args(
        [
            "--profile",
            "development",
            "--output-root",
            str(output_root),
            "--run-id",
            "final-hash-error",
            "--dimension",
            "8",
            "--sample-count",
            "24",
            "--batch-size",
            "12",
            "--bootstrap-blocks",
            "6",
            "--bootstrap-resamples",
            "11",
            "--bits",
            "1",
        ]
    )
    monkeypatch.setattr(
        "hamutay.turboquant.qualify._existing_artifact_hashes",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            ValueError("controlled final hash failure")
        ),
    )

    with pytest.raises(ValueError, match="controlled final hash failure"):
        execute_qualification(args)

    run_directory = output_root / "final-hash-error"
    manifest = _load_canonical_json(run_directory / "manifest.json")
    qualification = _load_canonical_json(run_directory / "qualification.json")
    assert manifest["status"] == "error"
    assert qualification["status"] == "error"
    assert qualification["error"]["type"] == "ValueError"
    assert qualification["error"]["message"] == "controlled final hash failure"
