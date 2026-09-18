"""Independent validation of process determinism, canonical records, and artifact integrity.

Validates complete inventories, three fresh process execution records, determinism payloads and stream hashes,
recomputes declared metric and payload hashes, canonical JSON byte representation, immutable run inputs,
and cross-record consistency.

Transport Signing Identity:
    Tony Mason; hamutay@wamason.com; 01193FA2631C8AE8E4DF266E216D3C9B920813A1
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import numpy as np
import pytest

from hamutay.turboquant.artifacts import (
    canonical_json_bytes,
    sha256_array,
    sha256_file,
)


REQUIRED_RUN_ARTIFACTS = (
    "manifest.json",
    "resolved_inputs.npz",
    "execution-0.json",
    "execution-1.json",
    "execution-2.json",
    "qualification.json",
    "run.log",
)
REQUIRED_RESOLVED_INPUT_ARRAYS = (
    "rotation",
    "paper_projection",
    "sensitivity_projection",
    "codebook_bits_1",
    "codebook_bits_2",
    "codebook_bits_3",
    "codebook_bits_4",
)
REQUIRED_STREAM_PREFIXES = (
    "synthetic.keys",
    "synthetic.queries",
    "algorithm_1.bits_1.codes",
    "algorithm_1.bits_1.norms",
    "algorithm_1.bits_1.reconstruction",
    "algorithm_2.paper.bits_1.signs",
    "algorithm_2.paper.bits_1.residual_norms",
    "algorithm_2.paper.bits_1.reconstruction",
)


def test_required_artifacts_inventory_completeness(shared_dev_run_with_author: Path):
    """All required artifacts must be present; omission of any artifact fails validation immediately."""
    for artifact_name in REQUIRED_RUN_ARTIFACTS:
        path = shared_dev_run_with_author / artifact_name
        assert path.is_file(), f"Required artifact missing from run inventory: {artifact_name}"


def test_three_fresh_process_execution_records(shared_dev_run_with_author: Path):
    """Validates that three distinct worker processes executed and recorded determinism payloads."""
    exec_paths = [shared_dev_run_with_author / f"execution-{i}.json" for i in range(3)]
    records = []
    for p in exec_paths:
        with open(p, "r", encoding="utf-8") as f:
            records.append(json.load(f))
            
    for r in records:
        assert r["schema"] == "hamutay.turboquant.execution.v1"
        assert r["status"] == "passed"
        
    pids = [r["provenance"]["pid"] for r in records]
    parent_pids = [r["provenance"]["parent_pid"] for r in records]
    assert len(set(pids)) == 3, f"Worker processes must have distinct PIDs: {pids}"
    assert len(set(parent_pids)) == 1, f"Worker processes must share launching parent PID: {parent_pids}"
    
    config_hashes = [r["configuration_sha256"] for r in records]
    input_hashes = [r["resolved_inputs_sha256"] for r in records]
    assert len(set(config_hashes)) == 1
    assert len(set(input_hashes)) == 1
    
    npz_path = shared_dev_run_with_author / "resolved_inputs.npz"
    assert sha256_file(npz_path) == input_hashes[0]


def test_execution_records_semantic_determinism_and_recomputed_hashes(shared_dev_run_with_author: Path):
    """Recomputes metric hashes and payload hashes; verifies stream inventories and agreement."""
    records = []
    for i in range(3):
        with open(shared_dev_run_with_author / f"execution-{i}.json", "r", encoding="utf-8") as f:
            records.append(json.load(f))
            
    payloads = [r["determinism_payload"] for r in records]
    payload_hashes = [r["determinism_payload_sha256"] for r in records]
    
    # Recompute payload_sha256 from canonical JSON bytes of payload
    for p, h in zip(payloads, payload_hashes):
        recomputed_payload_hash = hashlib.sha256(canonical_json_bytes(p)).hexdigest()
        assert recomputed_payload_hash == h, "Recomputed determinism payload hash does not match declared hash"
        
    assert len(set(payload_hashes)) == 1, f"Determinism payload mismatch across workers: {payload_hashes}"
    
    # Recompute metric_sha256 from canonical JSON bytes of metrics list
    for p in payloads:
        metrics_list = p["metrics"]
        assert isinstance(metrics_list, list) and len(metrics_list) > 0
        recomputed_metric_hash = hashlib.sha256(canonical_json_bytes(metrics_list)).hexdigest()
        assert recomputed_metric_hash == p["metric_sha256"], "Recomputed metric hash mismatch"
        
    metric_hashes = [p["metric_sha256"] for p in payloads]
    assert len(set(metric_hashes)) == 1
    
    stream_hashes = [p["stream_sha256"] for p in payloads]
    assert len(set(json.dumps(s, sort_keys=True) for s in stream_hashes)) == 1
    
    # Inventory check of required stream prefixes
    streams = stream_hashes[0]
    for prefix in REQUIRED_STREAM_PREFIXES:
        assert prefix in streams, f"Required stream key missing from worker payload: {prefix}"


def test_canonical_records_content_comparison_rule(shared_dev_run_with_author: Path):
    """Workers differ ONLY by execution_index and provenance.pid; all other content matches."""
    records = []
    for i in range(3):
        with open(shared_dev_run_with_author / f"execution-{i}.json", "r", encoding="utf-8") as f:
            records.append(json.load(f))
            
    normalized = []
    for r in records:
        r_copy = json.loads(json.dumps(r))
        del r_copy["execution_index"]
        del r_copy["provenance"]["pid"]
        normalized.append(canonical_json_bytes(r_copy))
        
    assert normalized[0] == normalized[1] == normalized[2], (
        "Worker records differ beyond execution_index and provenance.pid"
    )


def test_canonical_json_bytes_specification():
    """canonical_json_bytes must be compact, key-sorted, newline-terminated, and reject non-finites."""
    test_obj = {"z": 1, "a": [2, 3], "m": {"b": "hello", "a": True}}
    c_bytes = canonical_json_bytes(test_obj)
    
    assert c_bytes.endswith(b"\n")
    assert b": " not in c_bytes
    assert b", " not in c_bytes
    assert c_bytes.index(b'"a"') < c_bytes.index(b'"m"') < c_bytes.index(b'"z"')
    
    with pytest.raises(ValueError):
        canonical_json_bytes({"invalid": float("nan")})
    with pytest.raises(ValueError):
        canonical_json_bytes({"invalid": float("inf")})


def test_immutable_run_inputs_integrity_and_geometry(shared_dev_run_with_author: Path):
    """Validates resolved inputs NPZ arrays: orthogonal rotation, projections, and codebooks."""
    npz_path = shared_dev_run_with_author / "resolved_inputs.npz"
    npz = np.load(npz_path)
    
    # Verify inventory completeness of required arrays
    for key in REQUIRED_RESOLVED_INPUT_ARRAYS:
        assert key in npz, f"Required array {key} missing from resolved_inputs.npz"
    
    rotation = npz["rotation"]
    assert rotation.dtype == np.float32
    assert rotation.shape == (128, 128)
    rot_64 = rotation.astype(np.float64)
    ident = rot_64 @ rot_64.T
    assert np.allclose(ident, np.eye(128), atol=1e-5), "Rotation matrix is not orthogonal"
    
    paper_proj = npz["paper_projection"]
    sens_proj = npz["sensitivity_projection"]
    assert paper_proj.shape == (128, 128)
    assert sens_proj.shape == (128, 128)
    
    for b in (1, 2, 3, 4):
        cb_key = f"codebook_bits_{b}"
        cb = npz[cb_key]
        assert cb.dtype == np.float32
        assert cb.ndim == 1
        assert len(cb) == 2 ** b
        assert np.all(np.diff(cb) > 0), f"Codebook {cb_key} is not strictly increasing"


def test_manifest_and_qualification_artifact_hashes(shared_dev_run_with_author: Path):
    """Manifest and qualification artifact maps must strictly bind all run files without self-references."""
    with open(shared_dev_run_with_author / "manifest.json", "r", encoding="utf-8") as f:
        manifest = json.load(f)
    with open(shared_dev_run_with_author / "qualification.json", "r", encoding="utf-8") as f:
        qualification = json.load(f)
        
    m_artifacts = manifest["artifact_sha256"]
    q_artifacts = qualification["artifact_sha256"]
    
    # Check inventory completeness in artifact maps
    for fname in ("resolved_inputs.npz", "execution-0.json", "execution-1.json", "execution-2.json", "run.log"):
        assert fname in m_artifacts, f"File {fname} missing from manifest artifact map"
        assert fname in q_artifacts, f"File {fname} missing from qualification artifact map"
        
    # Recompute and verify file hashes
    for fname, exp_hash in m_artifacts.items():
        actual_hash = sha256_file(shared_dev_run_with_author / fname)
        assert actual_hash == exp_hash
        assert q_artifacts[fname] == exp_hash
        
    assert "manifest.json" not in m_artifacts
    assert "qualification.json" not in m_artifacts
    assert "qualification.json" not in q_artifacts
    assert "manifest.json" in q_artifacts
    
    manifest_actual_hash = sha256_file(shared_dev_run_with_author / "manifest.json")
    assert q_artifacts["manifest.json"] == manifest_actual_hash
    
    # Verify recomputation of configuration_sha256 in manifest
    exp_cfg_hash = hashlib.sha256(canonical_json_bytes(manifest["configuration"])).hexdigest()
    assert manifest["configuration_sha256"] == exp_cfg_hash
    
    # Recompute array hashes in manifest resolved_inputs map
    npz = np.load(shared_dev_run_with_author / "resolved_inputs.npz")
    for name in npz.files:
        assert name in manifest["resolved_inputs"]["array_sha256"]
        exp_arr_hash = manifest["resolved_inputs"]["array_sha256"][name]
        assert sha256_array(name, npz[name]) == exp_arr_hash


def test_typed_array_hash_wire_format():
    """Independently verifies array-stream wire format calculation and object dtype rejection."""
    label = "test_tensor"
    arr = np.arange(24, dtype=np.float32).reshape(2, 3, 4)
    
    # Independent manual wire format computation
    header = b"hamutay.turboquant.array-stream.v1\x00"
    label_bytes = label.encode("utf-8")
    label_chunk = len(label_bytes).to_bytes(8, byteorder="big", signed=False) + label_bytes
    
    dtype_str = arr.dtype.str.encode("ascii")
    dtype_chunk = len(dtype_str).to_bytes(8, byteorder="big", signed=False) + dtype_str
    
    rank_chunk = arr.ndim.to_bytes(8, byteorder="big", signed=False)
    shape_chunk = b"".join(dim.to_bytes(8, byteorder="big", signed=False) for dim in arr.shape)
    data_chunk = arr.tobytes(order="C")
    
    wire_bytes = header + label_chunk + dtype_chunk + rank_chunk + shape_chunk + data_chunk
    expected_sha256 = hashlib.sha256(wire_bytes).hexdigest()
    
    assert sha256_array(label, arr) == expected_sha256
    
    # Rejection of object dtypes
    obj_arr = np.array(["a", "b"], dtype=object)
    with pytest.raises((ValueError, TypeError)):
        sha256_array("obj_test", obj_arr)
