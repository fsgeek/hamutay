"""Tests for Task 6: Canonical Artifacts, CLI Namespaces, and Lifecycle."""

from __future__ import annotations

import json
from pathlib import Path
import pytest
import numpy as np

from hamutay.turboquant.artifacts import (
    canonical_json_bytes,
    sha256_file,
    create_run_directory,
)
from hamutay.turboquant.qualify import main


def test_canonical_json_bytes_contract() -> None:
    """Verify canonical_json_bytes outputs sorted, compact, unicode-preserving, newline JSON."""
    data = {
        "z_key": 1,
        "a_key": "Hamut'ay \u00f1",
        "nested": {"b": 2, "a": 1},
    }
    raw = canonical_json_bytes(data)

    # Ends with newline
    assert raw.endswith(b"\n")

    # Compactness: no space after commas or colons
    text = raw.decode("utf-8")
    assert ", " not in text
    assert ": " not in text

    # Key sorting: a_key before z_key
    assert text.index('"a_key"') < text.index('"z_key"')

    # Non-ASCII preservation: not \u00f1
    assert "ñ" in text

    # Rejection of NaN and Inf
    with pytest.raises(ValueError):
        canonical_json_bytes({"invalid": float("nan")})
    with pytest.raises(ValueError):
        canonical_json_bytes({"invalid": float("inf")})


def test_create_run_directory_append_only_refusal(tmp_path: Path) -> None:
    """Verify create_run_directory creates unique directory and refuses existing directory."""
    run_id = "test_run_001"
    dir1 = create_run_directory(tmp_path, run_id)
    assert dir1.exists()
    assert dir1.is_dir()

    # Second creation of same directory must be refused (append-only)
    with pytest.raises((FileExistsError, OSError)):
        create_run_directory(tmp_path, run_id)


def test_sha256_file_accuracy(tmp_path: Path) -> None:
    """Verify sha256_file computes exact sha256 checksum."""
    file_path = tmp_path / "test.txt"
    file_path.write_bytes(b"hello turboquant")
    expected = "2a52efc6ff4d34f2d7a2fa7dcfbfa993f434c3fb2b67f1057c793ff826284ad4"
    assert sha256_file(file_path) == expected


def test_cli_namespace_enforcement_refusal(tmp_path: Path) -> None:
    """Verify CLI rejects output roots not at/under experiments/turboquant/development or qualification."""
    # Attempting to use tmp_path directly as output root must fail before run directory creation
    invalid_root = str(tmp_path / "arbitrary_output")
    exit_code = main(["--profile", "development", "--output-root", invalid_root, "--run-id", "test_refuse"])
    assert exit_code != 0
    assert not Path(invalid_root).exists()


def test_cli_registered_mode_override_refusal(registered_output_root: Path) -> None:
    """Verify registered profile rejects any override of scientific counts."""
    forbidden_overrides = [
        ["--sample-count", "1000"],
        ["--batch-size", "500"],
        ["--dimension", "64"],
        ["--bootstrap-blocks", "50"],
        ["--bootstrap-resamples", "100"],
        ["--bits", "1,2"],
    ]
    for override in forbidden_overrides:
        cmd = [
            "--profile", "registered",
            "--output-root", str(registered_output_root),
            "--run-id", "refused_run",
        ] + override
        exit_code = main(cmd)
        assert exit_code != 0, f"Registered profile accepted count override: {override}"


def test_cli_registered_mode_missing_checkout_refusal(registered_output_root: Path) -> None:
    """Verify registered profile requires --author-qjl-checkout and rejects run if omitted."""
    cmd = [
        "--profile", "registered",
        "--output-root", str(registered_output_root),
        "--run-id", "missing_checkout_run",
    ]
    exit_code = main(cmd)
    assert exit_code != 0


def test_cli_development_mode_lifecycle_and_artifacts(
    dev_output_root: Path,
    unique_run_id: str,
) -> None:
    """Verify development mode completes with small explicit counts and emits all required artifacts."""
    run_id = unique_run_id
    cmd = [
        "--profile", "development",
        "--output-root", str(dev_output_root),
        "--run-id", run_id,
        "--sample-count", "200",
        "--batch-size", "100",
        "--bootstrap-blocks", "2",
        "--bootstrap-resamples", "10",
        "--bits", "1,2",
    ]
    exit_code = main(cmd)
    assert exit_code == 0, f"Development CLI run failed with exit code {exit_code}"

    run_dir = dev_output_root / run_id
    assert run_dir.exists()

    expected_files = [
        "manifest.json",
        "resolved_inputs.npz",
        "execution-0.json",
        "execution-1.json",
        "execution-2.json",
        "qualification.json",
        "run.log",
    ]
    for fname in expected_files:
        fpath = run_dir / fname
        assert fpath.exists(), f"Required artifact {fname} missing from run directory"
        assert fpath.stat().st_size > 0, f"Artifact {fname} was empty"

    # Verify manifest schema
    manifest_data = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
    assert manifest_data.get("schema") == "hamutay.turboquant.manifest.v2"

    # Verify execution schemas
    for i in range(3):
        exec_data = json.loads((run_dir / f"execution-{i}.json").read_text(encoding="utf-8"))
        assert exec_data.get("schema") == "hamutay.turboquant.execution.v1"

    # Verify qualification schema and gate structure
    qual_data = json.loads((run_dir / "qualification.json").read_text(encoding="utf-8"))
    assert qual_data.get("schema") == "hamutay.turboquant.qualification.v2"
    assert "gates" in qual_data
    assert "terminal_status" in qual_data

    # Development mode without author checkout reports author_code_differential as not_run
    gates = {g["name"]: g for g in qual_data["gates"]}
    assert "author_code_differential" in gates
    assert gates["author_code_differential"]["status"] == "not_run"
