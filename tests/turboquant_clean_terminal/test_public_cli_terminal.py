"""Independent validation of the public development CLI terminal path and five-gate record.

Tests truthful non-certifying development status, the complete terminal five-gate record,
independent re-evaluation of emitted numerical evidence, namespace enforcement, and append-only refusal rules.

Transport Signing Identity:
    Tony Mason; hamutay@wamason.com; 01193FA2631C8AE8E4DF266E216D3C9B920813A1
"""

from __future__ import annotations

import json
from pathlib import Path
import uuid
import numpy as np
import pytest

from hamutay.turboquant.qualify import main


EXPECTED_GATE_NAMES = (
    "round_trip_determinism",
    "mse_distortion",
    "qjl_bias_equivalence",
    "published_qjl_distortion",
    "author_code_differential",
)
FROZEN_MSE_ANALYTIC_TOLERANCE = 0.005
FROZEN_MSE_PAPER_TOLERANCE = 0.15
FROZEN_PRODUCT_PAPER_TOLERANCE = 0.15
FROZEN_EQUIVALENCE_FACTOR = 0.02
FROZEN_AUTHOR_ATOL = 1e-5
FROZEN_AUTHOR_RTOL = 1e-4


def test_cli_terminal_record_contains_all_five_gates(shared_dev_run_with_author: Path):
    """The terminal qualification record in development with author checkout must contain all 5 gates."""
    qual_path = shared_dev_run_with_author / "qualification.json"
    assert qual_path.is_file(), f"Missing qualification.json at {qual_path}"
    
    with open(qual_path, "r", encoding="utf-8") as f:
        qual_data = json.load(f)
        
    assert qual_data["schema"] == "hamutay.turboquant.qualification.v2"
    assert "gates" in qual_data
    
    reported_gates = qual_data["gates"]
    assert len(reported_gates) == 5, f"Expected exactly 5 gates, found {len(reported_gates)}"
    
    gate_names = tuple(g["name"] for g in reported_gates)
    assert gate_names == EXPECTED_GATE_NAMES, f"Gate order or names mismatch: {gate_names}"
    
    for g in reported_gates:
        assert g["status"] in ("passed", "failed", "not_run"), f"Invalid status in gate: {g}"
        assert isinstance(g["passed"], bool)
        assert isinstance(g["detail"], str) and len(g["detail"]) > 0


def test_cli_terminal_truthful_non_certifying_status(shared_dev_run_with_author: Path):
    """Development profile records must truthfully declare non-certifying status."""
    qual_path = shared_dev_run_with_author / "qualification.json"
    manifest_path = shared_dev_run_with_author / "manifest.json"
    
    with open(qual_path, "r", encoding="utf-8") as f:
        qual_data = json.load(f)
    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest_data = json.load(f)
        
    assert qual_data["certification"]["scope"] == "development"
    assert qual_data["certification"]["certifying"] is False
    assert isinstance(qual_data["certification"]["reason"], str) and len(qual_data["certification"]["reason"]) > 0
    
    assert manifest_data["certification"]["scope"] == "development"
    assert manifest_data["certification"]["certifying"] is False
    assert isinstance(manifest_data["certification"]["reason"], str) and len(manifest_data["certification"]["reason"]) > 0


def test_cli_terminal_recomputes_all_five_gates_from_emitted_evidence(shared_dev_run_with_author: Path):
    """Independently re-evaluates all five gate decisions from the actual emitted numerical evidence."""
    qual_path = shared_dev_run_with_author / "qualification.json"
    manifest_path = shared_dev_run_with_author / "manifest.json"
    
    with open(qual_path, "r", encoding="utf-8") as f:
        qual_data = json.load(f)
    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest_data = json.load(f)
        
    metrics = qual_data["metrics"]
    assert isinstance(metrics, list) and len(metrics) > 0, "Empty metrics list in qualification.json"
    
    # 1. Independent Re-evaluation of Gate 1: round_trip_determinism
    det_passed = qual_data["process_determinism"]["passed"]
    assert isinstance(det_passed, bool)
    gate1_record = qual_data["gates"][0]
    assert gate1_record["name"] == "round_trip_determinism"
    assert gate1_record["passed"] == det_passed
    assert gate1_record["status"] == ("passed" if det_passed else "failed")
    
    # 2. Independent Re-evaluation of Gate 2: mse_distortion
    independent_gate2_passed = True
    for m in metrics:
        rel_an = abs(m["mse_observed"] - m["mse_analytic_target"]) / m["mse_analytic_target"]
        rel_pap = abs(m["mse_observed"] - m["mse_paper_target"]) / m["mse_paper_target"]
        if rel_an > FROZEN_MSE_ANALYTIC_TOLERANCE or rel_pap > FROZEN_MSE_PAPER_TOLERANCE:
            independent_gate2_passed = False
            break
    gate2_record = qual_data["gates"][1]
    assert gate2_record["name"] == "mse_distortion"
    assert gate2_record["passed"] == independent_gate2_passed
    assert gate2_record["status"] == ("passed" if independent_gate2_passed else "failed")
    
    # 3. Independent Re-evaluation of Gate 3: qjl_bias_equivalence
    independent_gate3_passed = True
    for m in metrics:
        bound = FROZEN_EQUIVALENCE_FACTOR * m["normalized_bias_rmse"]
        ci_low, ci_high = m["normalized_bias_ci9875"]
        if ci_low < -bound or ci_high > bound:
            independent_gate3_passed = False
            break
    gate3_record = qual_data["gates"][2]
    assert gate3_record["name"] == "qjl_bias_equivalence"
    assert gate3_record["passed"] == independent_gate3_passed
    assert gate3_record["status"] == ("passed" if independent_gate3_passed else "failed")
    
    # 4. Independent Re-evaluation of Gate 4: published_qjl_distortion
    independent_gate4_passed = True
    for m in metrics:
        rel_prod = abs(m["product_observed"] - m["product_paper_target"]) / m["product_paper_target"]
        if rel_prod > FROZEN_PRODUCT_PAPER_TOLERANCE:
            independent_gate4_passed = False
            break
    gate4_record = qual_data["gates"][3]
    assert gate4_record["name"] == "published_qjl_distortion"
    assert gate4_record["passed"] == independent_gate4_passed
    assert gate4_record["status"] == ("passed" if independent_gate4_passed else "failed")
    
    # 5. Independent Re-evaluation of Gate 5: author_code_differential from embedded arrays
    author_record = qual_data["author_code_differential"]
    assert isinstance(author_record, dict), "Author differential not embedded in qualification.json"
    assert author_record["status"] == "passed"
    
    # Validate embedded arrays directly from JSON values
    arrays = author_record["arrays"]
    trans_inlier = np.array(arrays["transparent_inlier_sign_bytes"]["values"], dtype=np.uint8)
    auth_inlier = np.array(arrays["author_inlier_sign_bytes"]["values"], dtype=np.uint8)
    assert np.array_equal(trans_inlier, auth_inlier)
    
    outlier_norms = np.array(arrays["author_outlier_norms"]["values"], dtype=np.float32)
    assert np.all(outlier_norms == 0.0)
    
    trans_scores = np.array(arrays["transparent_scores"]["values"], dtype=np.float32)
    auth_scores = np.array(arrays["author_scores"]["values"], dtype=np.float32)
    assert np.all(np.isfinite(trans_scores))
    assert np.all(np.isfinite(auth_scores))
    abs_score_diff = np.abs(auth_scores - trans_scores)
    allowed_tol = FROZEN_AUTHOR_ATOL + FROZEN_AUTHOR_RTOL * np.abs(trans_scores)
    assert np.all(abs_score_diff <= allowed_tol)
    
    zero_trans = np.array(arrays["zero_transparent_inlier_sign_bytes"]["values"], dtype=np.uint8)
    zero_auth = np.array(arrays["zero_author_inlier_sign_bytes"]["values"], dtype=np.uint8)
    assert np.all(zero_trans == 255)
    assert np.all(zero_auth == 0)
    
    gate5_record = qual_data["gates"][4]
    assert gate5_record["name"] == "author_code_differential"
    assert gate5_record["passed"] is True
    assert gate5_record["status"] == "passed"
    
    # 6. Overall Terminal Decision
    all_recomputed_passed = (
        independent_gate2_passed and independent_gate3_passed and
        independent_gate4_passed and det_passed and gate5_record["passed"]
    )
    expected_terminal_status = "passed" if all_recomputed_passed else "failed"
    assert qual_data["status"] == expected_terminal_status
    assert manifest_data["status"] == expected_terminal_status


def test_cli_development_run_without_author_checkout(
    repo_root: Path,
    dev_run_output_root: Path,
):
    """Development run without author checkout marks author gate as not_run and exits zero."""
    unique_run_id = f"cli_no_author_{uuid.uuid4().hex[:10]}"
    run_dir = dev_run_output_root / unique_run_id
    
    argv = [
        "--profile", "development",
        "--output-root", str(dev_run_output_root),
        "--run-id", unique_run_id,
        "--dimension", "128",
        "--sample-count", "8000",
        "--batch-size", "4000",
        "--bootstrap-blocks", "10",
        "--bootstrap-resamples", "100",
        "--bits", "1,2",
    ]
    exit_code = main(argv)
    assert exit_code == 0
    
    with open(run_dir / "qualification.json", "r", encoding="utf-8") as f:
        qual_data = json.load(f)
        
    gate5 = next(g for g in qual_data["gates"] if g["name"] == "author_code_differential")
    assert gate5["status"] == "not_run"
    assert gate5["passed"] is False
    assert qual_data["author_code_differential"] == "not_run"
    assert qual_data["certification"]["certifying"] is False


def test_cli_enforces_output_namespaces(repo_root: Path):
    """CLI must reject output roots outside declared development/qualification namespaces."""
    invalid_root = repo_root / "tmp" / "illegal_output_tree"
    
    argv = [
        "--profile", "development",
        "--output-root", str(invalid_root),
        "--run-id", "test_namespace_rejection",
    ]
    with pytest.raises((SystemExit, ValueError)):
        main(argv)


def test_cli_append_only_run_directory_refusal(
    shared_dev_run_with_author: Path,
    author_checkout_path: Path,
    dev_run_output_root: Path,
):
    """CLI refuses to execute when the run directory already exists."""
    existing_run_id = shared_dev_run_with_author.name
    
    argv = [
        "--profile", "development",
        "--output-root", str(dev_run_output_root),
        "--run-id", existing_run_id,
        "--author-qjl-checkout", str(author_checkout_path),
    ]
    with pytest.raises((SystemExit, FileExistsError, ValueError)):
        main(argv)


def test_cli_registered_profile_refuses_override_and_missing_checkout(repo_root: Path):
    """Registered mode must refuse explicit count overrides and missing checkout."""
    qual_root = repo_root / "experiments" / "turboquant" / "qualification"
    
    # 1. Attempting smaller counts in registered profile is refused
    argv_count_override = [
        "--profile", "registered",
        "--output-root", str(qual_root),
        "--run-id", "refuse_count_override",
        "--sample-count", "8000",
    ]
    with pytest.raises((SystemExit, ValueError)):
        main(argv_count_override)

    # 2. Registered mode without author checkout is refused
    argv_no_author = [
        "--profile", "registered",
        "--output-root", str(qual_root),
        "--run-id", "refuse_no_author",
    ]
    with pytest.raises((SystemExit, ValueError)):
        main(argv_no_author)
