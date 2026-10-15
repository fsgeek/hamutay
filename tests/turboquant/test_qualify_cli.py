from dataclasses import asdict
import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace
import zipfile

import numpy as np
import pytest

import hamutay.turboquant.artifacts as artifact_io
from hamutay.turboquant.artifacts import canonical_json_bytes, sha256_file
from hamutay.turboquant.qualify import (
    CERTIFICATION_REASON,
    QualificationValidationError,
    _TerminalPair,
    _completion_exit_status,
    _compare_worker_outputs,
    _publish_terminal_pair,
    _terminal_certification,
    _validate_output_root,
    _validate_registered_cleanliness,
    build_parser,
    execute_qualification,
    run_registered_workers,
)
from hamutay.turboquant.qualification import (
    GateResult,
    QualificationConfig,
    author_code_differential_gate,
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
        [
            "--profile",
            "registered",
            "--output-root",
            "out",
            "--run-id",
            "r1",
            "--author-qjl-checkout",
            "/tmp/QJL",
        ]
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
                "--author-qjl-checkout",
                "/tmp/QJL",
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
                "--author-qjl-checkout",
                "/tmp/QJL",
                flag,
                value,
            ]
        )

    assert error.value.code == 2


def test_registered_profile_uses_divisible_batch_size():
    args = build_parser().parse_args(
        [
            "--profile",
            "registered",
            "--output-root",
            "out",
            "--run-id",
            "r1",
            "--author-qjl-checkout",
            "/tmp/QJL",
        ]
    )

    assert args.batch_size == 4000
    assert args.sample_count % args.batch_size == 0


def test_registered_profile_requires_author_checkout():
    with pytest.raises(SystemExit) as error:
        build_parser().parse_args(
            ["--profile", "registered", "--output-root", "out", "--run-id", "r1"]
        )

    assert error.value.code == 2


def test_development_profile_may_omit_author_checkout():
    args = build_parser().parse_args(
        ["--profile", "development", "--output-root", "out", "--run-id", "dev"]
    )

    assert args.author_qjl_checkout is None


def test_registered_exit_policy_is_zero_only_when_all_five_gates_pass():
    assert _completion_exit_status("development", all_five_passed=False) == 0
    assert _completion_exit_status("development", all_five_passed=True) == 0
    assert _completion_exit_status("registered", all_five_passed=False) == 1
    assert _completion_exit_status("registered", all_five_passed=True) == 0


def test_author_gate_reports_not_run_without_checkout():
    gate = author_code_differential_gate(None)

    assert asdict(gate) == {
        "name": "author_code_differential",
        "passed": False,
        "observed": "not_run",
        "threshold": {"atol": 1e-5, "rtol": 1e-4},
        "detail": "Author QJL checkout was omitted in development mode.",
        "status": "not_run",
    }


def test_registered_certification_requires_five_passed_gates():
    passed = tuple(
        GateResult(
            name=name,
            passed=True,
            observed=True,
            threshold=True,
            detail="passed",
        )
        for name in (
            "round_trip_determinism",
            "mse_distortion",
            "qjl_bias_equivalence",
            "published_qjl_distortion",
            "author_code_differential",
        )
    )
    assert _terminal_certification("registered", passed) == {
        "scope": "r1",
        "certifying": True,
        "reason": "All five registered R1 qualification gates passed.",
    }
    failed = (*passed[:-1], author_code_differential_gate(None))
    assert _terminal_certification("registered", failed) == {
        "scope": "r1",
        "certifying": False,
        "reason": "At least one of the five registered R1 gates did not pass.",
    }


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
    else:
        command.extend(["--author-qjl-checkout", "/tmp/QJL"])
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


@pytest.mark.parametrize(
    ("profile", "namespace_name"),
    [("development", "development"), ("registered", "qualification")],
)
def test_profile_rejects_symlinked_trusted_namespace_root(
    profile, namespace_name, tmp_path
):
    repository = tmp_path / "repository"
    outside = tmp_path / "outside"
    outside.mkdir()
    namespace = repository / "experiments" / "turboquant" / namespace_name
    namespace.parent.mkdir(parents=True)
    namespace.symlink_to(outside, target_is_directory=True)

    with pytest.raises(QualificationValidationError, match="must not be a symlink"):
        _validate_output_root(profile, namespace, repository)


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

    with pytest.raises(ValueError, match="byte-identical"):
        _compare_worker_outputs(
            paths,
            configuration_sha256="3" * 64,
            resolved_inputs_sha256="4" * 64,
            parent_pid=os.getpid(),
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
    assert manifest["schema"] == "hamutay.turboquant.manifest.v2"
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

    assert qualification["schema"] == "hamutay.turboquant.qualification.v2"
    assert qualification["status"] == manifest["status"]
    assert qualification["certification"] == certification
    assert [gate["name"] for gate in qualification["gates"]] == [
        "round_trip_determinism",
        "mse_distortion",
        "qjl_bias_equivalence",
        "published_qjl_distortion",
        "author_code_differential",
    ]
    assert qualification["gates"][0]["passed"] is True
    assert qualification["gates"][-1] == {
        "name": "author_code_differential",
        "passed": False,
        "observed": "not_run",
        "threshold": {"atol": 1e-5, "rtol": 1e-4},
        "detail": "Author QJL checkout was omitted in development mode.",
        "status": "not_run",
    }
    assert qualification["author_code_differential"] == "not_run"
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


@pytest.mark.parametrize(
    ("error_type", "message"),
    [
        (FileNotFoundError, "controlled missing author checkout"),
        (ValueError, "controlled pinned checkout mismatch"),
        (RuntimeError, "controlled CUDA compiler mismatch"),
    ],
)
def test_author_preflight_fault_writes_terminal_error_pair_before_reraising(
    error_type, message, monkeypatch, development_output_root
):
    run_id = f"author-preflight-{error_type.__name__.lower()}"
    args = _namespace_args("development", development_output_root, run_id)
    args.author_qjl_checkout = Path("/controlled/QJL")

    def fail_preflight(**_kwargs):
        raise error_type(message)

    monkeypatch.setattr(
        "hamutay.turboquant.qualify._load_author_qjl_oracle",
        lambda _repository: SimpleNamespace(preflight_author_qjl=fail_preflight),
    )

    with pytest.raises(error_type, match=message):
        execute_qualification(args)

    run_directory = development_output_root / run_id
    assert {path.name for path in run_directory.iterdir()} == {
        "manifest.json",
        "qualification.json",
        "run.log",
    }
    manifest = _load_canonical_json(run_directory / "manifest.json")
    qualification = _load_canonical_json(run_directory / "qualification.json")
    assert manifest["status"] == qualification["status"] == "error"
    assert manifest["author_qjl_preflight"] == {
        "error": {"message": message, "type": error_type.__name__},
        "status": "error",
    }
    assert qualification["author_code_differential"] == "error"
    assert qualification["error"] == {
        "message": message,
        "traceback": qualification["error"]["traceback"],
        "type": error_type.__name__,
    }


def test_real_cli_missing_author_checkout_is_nonzero_with_terminal_error_pair(
    development_output_root, tmp_path
):
    run_id = "real-missing-author-checkout"
    missing_checkout = tmp_path / "missing-QJL"
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
            "1",
            "--author-qjl-checkout",
            str(missing_checkout),
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode != 0
    assert "FileNotFoundError" in completed.stderr
    run_directory = development_output_root / run_id
    assert {path.name for path in run_directory.iterdir()} == {
        "manifest.json",
        "qualification.json",
        "run.log",
    }
    manifest = _load_canonical_json(run_directory / "manifest.json")
    qualification = _load_canonical_json(run_directory / "qualification.json")
    assert manifest["status"] == qualification["status"] == "error"
    assert manifest["author_qjl_preflight"]["status"] == "error"
    assert qualification["error"]["type"] == "FileNotFoundError"


def test_author_gate_contract_fault_uses_existing_terminal_recovery(
    monkeypatch, development_output_root
):
    run_id = "author-contract-error"
    args = _namespace_args("development", development_output_root, run_id)
    args.author_qjl_checkout = Path("/controlled/QJL")
    preflight = {
        "environment": {
            "default_cuda": "/usr/local/cuda",
            "default_cuda_resolved": "/usr/local/cuda-13.2",
        },
        "upstream": {"commit": "648b3641f96b6e95e091217220b94e4739fd4d82"},
    }
    monkeypatch.setattr(
        "hamutay.turboquant.qualify._load_author_qjl_oracle",
        lambda _repository: SimpleNamespace(
            preflight_author_qjl=lambda **_kwargs: preflight
        ),
    )
    monkeypatch.setattr(
        "hamutay.turboquant.qualify._run_author_qjl_oracle",
        lambda **_kwargs: {
            "status": "passed",
            "gate": {
                "name": "author_code_differential",
                "passed": True,
                "threshold": {"atol": 9.0, "rtol": 9.0},
                "detail": "invalid contract",
            },
        },
    )

    with pytest.raises(ValueError, match="changed the frozen FP32 tolerance"):
        execute_qualification(args)

    run_directory = development_output_root / run_id
    assert {path.name for path in run_directory.iterdir()} == {
        "execution-0.json",
        "execution-1.json",
        "execution-2.json",
        "manifest.json",
        "qualification.json",
        "resolved_inputs.npz",
        "run.log",
    }
    manifest = _load_canonical_json(run_directory / "manifest.json")
    qualification = _load_canonical_json(run_directory / "qualification.json")
    assert manifest["status"] == qualification["status"] == "error"
    assert manifest["author_qjl_preflight"] == preflight
    assert qualification["author_code_differential"] == "error"
    assert qualification["error"]["type"] == "ValueError"
    assert qualification["error"]["message"] == (
        "author QJL oracle changed the frozen FP32 tolerance"
    )


def test_development_with_checkout_embeds_complete_passed_author_oracle(
    development_output_root,
):
    checkout_value = os.environ.get("QJL_AUTHOR_CHECKOUT")
    if checkout_value is None:
        pytest.skip("development author integration requires QJL_AUTHOR_CHECKOUT")
    args = _namespace_args(
        "development", development_output_root, "development-with-author"
    )
    args.author_qjl_checkout = Path(checkout_value)

    exit_status = execute_qualification(args)

    run_directory = development_output_root / "development-with-author"
    assert exit_status == 0
    assert {path.name for path in run_directory.iterdir()} == {
        "execution-0.json",
        "execution-1.json",
        "execution-2.json",
        "manifest.json",
        "qualification.json",
        "resolved_inputs.npz",
        "run.log",
    }
    manifest = _load_canonical_json(run_directory / "manifest.json")
    qualification = _load_canonical_json(run_directory / "qualification.json")
    assert manifest["certification"] == {
        "certifying": False,
        "reason": CERTIFICATION_REASON,
        "scope": "development",
    }
    assert (
        manifest["author_qjl_preflight"]["environment"]
        == (qualification["author_code_differential"]["environment"])
    )
    assert qualification["gates"][-1]["name"] == "author_code_differential"
    assert qualification["gates"][-1]["status"] == "passed"
    assert qualification["author_code_differential"]["status"] == "passed"
    assert "author_outlier_signs" in qualification["author_code_differential"]["arrays"]
    assert qualification["certification"]["certifying"] is False


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


def _install_terminal_publication_fault(monkeypatch, stage, *, persistent=False):
    real_link = artifact_io.os.link
    real_replace = artifact_io.os.replace
    real_fsync_directory = artifact_io._fsync_directory
    state = {"faulted": False, "qualification_linked": False}
    history = []

    def should_fault(selected_stage):
        if stage != selected_stage or (state["faulted"] and not persistent):
            return False
        state["faulted"] = True
        return True

    def record(destination):
        path = Path(destination)
        if path.name in {"manifest.json", "qualification.json"}:
            history.append((path.name, _load_canonical_json(path)["status"]))

    def controlled_link(source, destination):
        path = Path(destination)
        if path.name == "qualification.json" and should_fault("qualification_link"):
            raise OSError("controlled qualification link failure")
        result = real_link(source, destination)
        record(path)
        if path.name == "qualification.json":
            state["qualification_linked"] = True
        return result

    def controlled_replace(source, destination):
        path = Path(destination)
        if path.name == "manifest.json" and should_fault("manifest_replace"):
            raise OSError("controlled manifest replacement failure")
        result = real_replace(source, destination)
        record(path)
        return result

    def controlled_fsync_directory(directory):
        if state["qualification_linked"] and should_fault("qualification_fsync"):
            raise OSError("controlled qualification fsync failure")
        return real_fsync_directory(directory)

    monkeypatch.setattr(artifact_io.os, "link", controlled_link)
    monkeypatch.setattr(artifact_io.os, "replace", controlled_replace)
    monkeypatch.setattr(artifact_io, "_fsync_directory", controlled_fsync_directory)
    return history


def _assert_terminal_history_never_transitions(history):
    terminal_by_name = {}
    for name, status in history:
        if status == "running":
            continue
        terminal_by_name.setdefault(name, status)
        assert terminal_by_name[name] == status


def _record_terminal_pair_attempts(monkeypatch):
    real_publish = _publish_terminal_pair
    attempts = []

    def record_and_publish(run_directory, pair):
        attempts.append((pair.manifest_bytes, pair.qualification_bytes))
        return real_publish(run_directory, pair)

    monkeypatch.setattr(
        "hamutay.turboquant.qualify._publish_terminal_pair", record_and_publish
    )
    return attempts


@pytest.mark.parametrize(
    ("stage", "message", "expected_status"),
    [
        ("manifest_replace", "controlled manifest replacement failure", None),
        ("qualification_link", "controlled qualification link failure", None),
        ("qualification_fsync", "controlled qualification fsync failure", None),
    ],
)
def test_terminal_pair_fault_recovery_never_changes_terminal_status(
    stage,
    message,
    expected_status,
    monkeypatch,
    development_output_root,
):
    run_id = f"terminal-{stage}"
    args = _namespace_args("development", development_output_root, run_id)
    history = _install_terminal_publication_fault(monkeypatch, stage)

    with pytest.raises(OSError, match=message):
        execute_qualification(args)

    run_directory = development_output_root / run_id
    manifest_path = run_directory / "manifest.json"
    qualification_path = run_directory / "qualification.json"
    manifest = _load_canonical_json(manifest_path)
    qualification = _load_canonical_json(qualification_path)
    assert manifest["status"] == qualification["status"]
    if expected_status is not None:
        assert manifest["status"] == expected_status
    else:
        assert manifest["status"] in {"passed", "failed"}
    _assert_terminal_history_never_transitions(history)

    immutable = (manifest_path.read_bytes(), qualification_path.read_bytes())
    with pytest.raises(QualificationValidationError):
        execute_qualification(args)
    assert immutable == (manifest_path.read_bytes(), qualification_path.read_bytes())


def test_persistent_qualification_link_fault_leaves_immutable_manifest_only(
    monkeypatch, development_output_root
):
    run_id = "terminal-persistent-qualification-link"
    args = _namespace_args("development", development_output_root, run_id)
    history = _install_terminal_publication_fault(
        monkeypatch, "qualification_link", persistent=True
    )

    with pytest.raises(OSError, match="controlled qualification link failure"):
        execute_qualification(args)

    run_directory = development_output_root / run_id
    manifest_path = run_directory / "manifest.json"
    manifest_before = manifest_path.read_bytes()
    assert _load_canonical_json(manifest_path)["status"] in {"passed", "failed"}
    assert not (run_directory / "qualification.json").exists()
    _assert_terminal_history_never_transitions(history)

    with pytest.raises(QualificationValidationError):
        execute_qualification(args)
    assert manifest_path.read_bytes() == manifest_before


def test_terminal_pair_rejects_contradictory_qualification_before_commit(tmp_path):
    run_directory = tmp_path / "run"
    run_directory.mkdir()
    manifest_path = run_directory / "manifest.json"
    qualification_path = run_directory / "qualification.json"
    manifest_path.write_bytes(canonical_json_bytes({"status": "running"}))
    qualification_path.write_bytes(canonical_json_bytes({"status": "error"}))
    pair = _TerminalPair(
        status="passed",
        manifest_bytes=canonical_json_bytes({"status": "passed"}),
        qualification_bytes=canonical_json_bytes({"status": "passed"}),
    )

    with pytest.raises(RuntimeError, match="qualification is immutable"):
        _publish_terminal_pair(run_directory, pair)

    assert _load_canonical_json(manifest_path)["status"] == "running"
    assert _load_canonical_json(qualification_path)["status"] == "error"


@pytest.mark.parametrize("stage", ["manifest_replace", "qualification_link"])
def test_preterminal_error_pair_retries_same_frozen_bytes_after_one_shot_fault(
    stage, monkeypatch, development_output_root
):
    run_id = f"preterminal-one-shot-{stage}"
    args = _namespace_args("development", development_output_root, run_id)
    history = _install_terminal_publication_fault(monkeypatch, stage)
    attempts = _record_terminal_pair_attempts(monkeypatch)

    def fail_metadata():
        raise RuntimeError("controlled preterminal metadata failure")

    monkeypatch.setattr("hamutay.turboquant.qualify._platform_metadata", fail_metadata)

    with pytest.raises(RuntimeError, match="controlled preterminal metadata failure"):
        execute_qualification(args)

    run_directory = development_output_root / run_id
    manifest = _load_canonical_json(run_directory / "manifest.json")
    qualification = _load_canonical_json(run_directory / "qualification.json")
    assert manifest["status"] == qualification["status"] == "error"
    assert qualification["error"]["type"] == "RuntimeError"
    assert (
        qualification["error"]["message"] == "controlled preterminal metadata failure"
    )
    _assert_terminal_history_never_transitions(history)
    assert len(attempts) == 2
    assert attempts[0] == attempts[1]


@pytest.mark.parametrize(
    ("stage", "visible_manifest_status"),
    [("manifest_replace", "running"), ("qualification_link", "error")],
)
def test_preterminal_error_pair_persistent_fault_fails_closed(
    stage, visible_manifest_status, monkeypatch, development_output_root
):
    run_id = f"preterminal-persistent-{stage}"
    args = _namespace_args("development", development_output_root, run_id)
    history = _install_terminal_publication_fault(monkeypatch, stage, persistent=True)
    attempts = _record_terminal_pair_attempts(monkeypatch)

    def fail_metadata():
        raise RuntimeError("controlled persistent preterminal failure")

    monkeypatch.setattr("hamutay.turboquant.qualify._platform_metadata", fail_metadata)

    with pytest.raises(RuntimeError, match="controlled persistent preterminal failure"):
        execute_qualification(args)

    run_directory = development_output_root / run_id
    assert _load_canonical_json(run_directory / "manifest.json")["status"] == (
        visible_manifest_status
    )
    assert not (run_directory / "qualification.json").exists()
    _assert_terminal_history_never_transitions(history)
    assert len(attempts) == 2
    assert attempts[0] == attempts[1]
