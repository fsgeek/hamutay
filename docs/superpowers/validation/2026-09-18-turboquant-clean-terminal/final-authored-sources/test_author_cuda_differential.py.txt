"""Independent validation of the pinned author QJL CUDA differential evidence.

Tests actual successful execution, environment preflight, pinned checkout verification,
and independently re-evaluates all reported numerical comparisons without trusting
returned status labels or weakening tolerances.

Transport Signing Identity:
    Tony Mason; hamutay@wamason.com; 01193FA2631C8AE8E4DF266E216D3C9B920813A1
"""

from __future__ import annotations

import json
from pathlib import Path
import uuid
import numpy as np
import pytest
import torch

from hamutay.turboquant.artifacts import sha256_array, sha256_file
from hamutay.turboquant.qualification import author_code_differential_gate


PINNED_COMMIT = "648b3641f96b6e95e091217220b94e4739fd4d82"
PINNED_ORIGIN = "https://github.com/amirzandieh/QJL"
PINNED_FILE_HASHES = {
    "LICENSE": "c71d239df91726fc519c6eb72d318ec65820627232b2f796219e87dcf35d0ab4",
    "qjl_kernel/csrc/qjl_quant_kernel.cu": "d03b2fd86504554f48da48df2740d73a0cc2d1d8a28c22698da20c9ee801aefd",
    "qjl_kernel/csrc/qjl_score_kernel.cu": "848398bb6b140433aa10f4ccea16eb680ec215cb148956f09e46bbbdabdc030c",
    "models/llama3_utils_qjl.py": "725b6777b752e30b583b6834e258a849c01679c4e3c007f3b4c62212393f34c2",
}
REQUIRED_ARRAY_NAMES = (
    "keys",
    "queries",
    "projection",
    "outlier_indices",
    "key_norms",
    "query_sketch",
    "transparent_inlier_sign_bytes",
    "author_inlier_sign_bytes",
    "author_outlier_signs",
    "author_outlier_norms",
    "transparent_scores",
    "author_scores",
    "zero_projection",
    "zero_transparent_inlier_sign_bytes",
    "zero_author_inlier_sign_bytes",
)
FROZEN_ATOL = 1e-5
FROZEN_RTOL = 1e-4


def test_author_cuda_preflight_and_environment(author_adapter, author_checkout_path: Path):
    """Verifies declared CUDA 12.8 environment prerequisites before kernel compilation."""
    preflight = author_adapter.preflight_author_qjl(checkout=author_checkout_path, device="cuda:0")
    
    assert "environment" in preflight
    assert "upstream" in preflight
    assert "status" not in preflight  # Public contract constraint
    
    env = preflight["environment"]
    assert env["device"] == "cuda:0"
    assert "cuda_home" in env and "12.8" in env["cuda_home"]
    assert "default_cuda_resolved" in env and "13.2" in env["default_cuda_resolved"]
    assert "torch_cuda" in env and env["torch_cuda"].startswith("12.8")
    assert "nvcc_version" in env and "12.8" in env["nvcc_version"]
    assert isinstance(env["device_compute_capability"], list)
    assert len(env["device_compute_capability"]) == 2


def test_author_pinned_checkout_verification(author_adapter, author_checkout_path: Path):
    """Verifies cleanliness, commit, origin, and cryptographic file hashes of pinned checkout."""
    checkout_meta = author_adapter.verify_pinned_checkout(author_checkout_path)
    
    assert checkout_meta["clean"] is True
    assert checkout_meta["commit"] == PINNED_COMMIT
    assert checkout_meta["origin"] in (PINNED_ORIGIN, f"{PINNED_ORIGIN}.git")
    
    for rel_path, expected_hash in PINNED_FILE_HASHES.items():
        assert checkout_meta["sha256"][rel_path] == expected_hash
        # Independently verify the actual file bytes on disk
        computed_hash = sha256_file(author_checkout_path / rel_path)
        assert computed_hash == expected_hash, f"Hash mismatch on {rel_path}"


def test_author_cuda_differential_live_execution_and_independent_math(
    author_adapter,
    author_checkout_path: Path,
    dev_run_output_root: Path,
):
    """Executes live CUDA differential and independently evaluates reported numerical evidence."""
    unique_run_id = f"author_diff_{uuid.uuid4().hex[:12]}"
    output_dir = dev_run_output_root / unique_run_id
    output_dir.mkdir(parents=True, exist_ok=True)
    
    result = author_adapter.run_author_qjl_differential(
        checkout=author_checkout_path,
        output=output_dir,
        device="cuda:0",
    )
    
    # 1. Verify schema and top-level fields
    assert result["schema"] == "hamutay.turboquant.author-qjl.v1"
    assert result["status"] == "passed"
    assert result["study_seed_hex"] == "0b311d5d4eceaf773efde389305a1b5a"
    assert result["conventions"]["transparent_exact_zero_sign"] == "+1"
    assert result["conventions"]["author_exact_zero_sign"] == "-1"
    
    # 2. Check physical artifact existence
    json_path = output_dir / "author_qjl_differential.json"
    npz_path = output_dir / "author_qjl_differential.npz"
    assert json_path.is_file()
    assert npz_path.is_file()
    
    # 3. Cryptographic hash binding
    assert sha256_file(npz_path) == result["npz"]["sha256"]
    
    # 4. Independent Numerical Validation directly from NPZ arrays
    npz = np.load(npz_path)
    
    # Check completeness of required array inventory
    for name in REQUIRED_ARRAY_NAMES:
        assert name in npz, f"Required array member {name} missing from NPZ artifact"
        assert name in result["arrays"], f"Required array metadata for {name} missing from JSON"
    
    # Check A: Inlier sign bytes must be bit-identical
    trans_inlier = npz["transparent_inlier_sign_bytes"]
    auth_inlier = npz["author_inlier_sign_bytes"]
    assert np.array_equal(trans_inlier, auth_inlier), "Inlier sign bytes mismatch between transparent and author"
    
    # Check B: Dummy outlier norms must be exact zero
    outlier_norms = npz["author_outlier_norms"]
    assert np.all(outlier_norms == 0.0), "Dummy outlier norms are not exact zero"
    
    # Check C: Score kernel differential must satisfy combined tolerance
    trans_scores = npz["transparent_scores"]
    auth_scores = npz["author_scores"]
    assert np.all(np.isfinite(trans_scores)), "Non-finite values in transparent scores"
    assert np.all(np.isfinite(auth_scores)), "Non-finite values in author scores"
    
    abs_diff = np.abs(auth_scores - trans_scores)
    allowed_tolerance = FROZEN_ATOL + FROZEN_RTOL * np.abs(trans_scores)
    elementwise_satisfied = abs_diff <= allowed_tolerance
    assert np.all(elementwise_satisfied), "Score difference exceeded combined tolerance abs(diff) <= atol + rtol*abs(ref)"
    
    # Verify independent max absolute error
    independent_max_abs = float(np.max(abs_diff))
    assert independent_max_abs <= FROZEN_ATOL + FROZEN_RTOL * float(np.max(np.abs(trans_scores)))
    
    # Check D: Declared Exact-Zero Projection Convention Difference
    # Transparent maps zero to +1 (all 1 bits in packed byte = 0xFF = 255)
    # Author maps zero to -1 (all 0 bits in packed byte = 0x00 = 0)
    zero_trans = npz["zero_transparent_inlier_sign_bytes"]
    zero_auth = npz["zero_author_inlier_sign_bytes"]
    assert np.all(zero_trans == 255), "Transparent quantizer did not encode exact zero as +1 (all bits set)"
    assert np.all(zero_auth == 0), "Author CUDA kernel did not encode exact zero as -1 (all bits clear)"
    assert result["comparisons"]["constructed_zero_projection"]["differing_bits_per_byte"] == 8
    assert result["comparisons"]["constructed_zero_projection"]["expected_declared_difference"] is True
    
    # Check E: Typed array hashes
    for name in npz.files:
        expected_array_hash = result["arrays"][name]["sha256"]
        assert sha256_array(name, npz[name]) == expected_array_hash


def test_author_cuda_adapter_append_only_refusal(
    author_adapter,
    author_checkout_path: Path,
    dev_run_output_root: Path,
):
    """Author adapter must refuse to overwrite preexisting evidence artifacts."""
    unique_run_id = f"author_refusal_{uuid.uuid4().hex[:12]}"
    output_dir = dev_run_output_root / unique_run_id
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # First invocation succeeds
    author_adapter.run_author_qjl_differential(
        checkout=author_checkout_path,
        output=output_dir,
        device="cuda:0",
    )
    
    # Second invocation on the same directory must refuse
    with pytest.raises((FileExistsError, ValueError)):
        author_adapter.run_author_qjl_differential(
            checkout=author_checkout_path,
            output=output_dir,
            device="cuda:0",
        )


def test_author_cuda_adapter_gate_integration(
    author_adapter,
    author_checkout_path: Path,
    dev_run_output_root: Path,
):
    """Adapter result converts faithfully to a passing public GateResult."""
    unique_run_id = f"author_gate_{uuid.uuid4().hex[:12]}"
    output_dir = dev_run_output_root / unique_run_id
    output_dir.mkdir(parents=True, exist_ok=True)
    
    result = author_adapter.run_author_qjl_differential(
        checkout=author_checkout_path,
        output=output_dir,
        device="cuda:0",
    )
    
    gate = author_code_differential_gate(result)
    assert gate.name == "author_code_differential"
    assert gate.passed is True
    assert gate.status == "passed"
    assert gate.threshold == {"atol": FROZEN_ATOL, "rtol": FROZEN_RTOL}
    assert gate.observed["inlier_sign_bytes_equal"] is True
    assert gate.observed["outlier_norms_exact_zero"] is True
