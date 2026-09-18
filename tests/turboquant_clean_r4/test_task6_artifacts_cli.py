import os
import json
import uuid
import struct
import hashlib
import pytest
from pathlib import Path
import numpy as np

from hamutay.turboquant.artifacts import (
    canonical_json_bytes,
    sha256_array,
    sha256_file,
    ArrayStreamHasher,
    create_run_directory
)
from hamutay.turboquant.qualify import main, run_registered_workers

def test_canonical_json_bytes():
    b = canonical_json_bytes({"b": 2, "a": "ñ", "c": [1, 2.5]})
    assert b == b'{"a":"\xc3\xb1","b":2,"c":[1,2.5]}\n'
    
    with pytest.raises(Exception):
        canonical_json_bytes({"inf": float("inf")})

def test_array_stream_hasher_exact():
    arr = np.array([1.0, 2.0], dtype=np.float32)
    label = "my_array"
    
    h = hashlib.sha256(b"hamutay.turboquant.array-stream.v1\x00")
    lbl_bytes = label.encode("utf-8")
    h.update(struct.pack(">Q", len(lbl_bytes)))
    h.update(lbl_bytes)
    dtype_str = arr.dtype.str.encode("ascii")
    h.update(struct.pack(">Q", len(dtype_str)))
    h.update(dtype_str)
    h.update(struct.pack(">Q", arr.ndim))
    for dim in arr.shape:
        h.update(struct.pack(">Q", dim))
    h.update(arr.tobytes(order="C"))
    
    expected = h.hexdigest()
    assert sha256_array(label, arr) == expected
    
    hasher = ArrayStreamHasher()
    hasher.update(label, arr)
    assert hasher.hexdigest() == expected

def test_array_stream_hasher_rejections():
    arr = np.array(["a"], dtype=object)
    with pytest.raises(Exception):
        sha256_array("label", arr)
    
    valid = np.array([1.0], dtype=np.float32)
    with pytest.raises(Exception):
        sha256_array("", valid)

def test_sha256_file(tmp_path):
    p = tmp_path / "test.txt"
    p.write_bytes(b"hello world")
    h = sha256_file(p)
    assert isinstance(h, str)
    assert len(h) == 64

def test_create_run_directory_bounds(tmp_path):
    root = tmp_path / "root"
    with pytest.raises(Exception):
        create_run_directory(root, "_invalid")
    with pytest.raises(Exception):
        create_run_directory(root, "dir/name")
        
    d = create_run_directory(root, "run-1.2_3")
    assert d.exists()
    with pytest.raises(Exception):
        create_run_directory(root, "run-1.2_3")

def test_cli_namespace_enforcement(tmp_path):
    args = ["--profile", "development", "--output-root", str(tmp_path), "--run-id", "devrun"]
    with pytest.raises(SystemExit) as e:
        main(args)
    assert e.value.code != 0

def test_cli_development_mode_flow():
    out = Path("experiments") / "turboquant" / "development"
    run_id = f"dev_test_{uuid.uuid4().hex[:8]}"
    args = [
        "--profile", "development",
        "--output-root", str(out),
        "--run-id", run_id,
        "--dimension", "128",
        "--sample-count", "4",
        "--batch-size", "4",
        "--bootstrap-blocks", "2",
        "--bootstrap-resamples", "10",
        "--bits", "1"
    ]
    
    exit_code = main(args)
    assert exit_code == 0
    
    run_dir = out / run_id
    assert (run_dir / "manifest.json").exists()
    assert (run_dir / "resolved_inputs.npz").exists()
    assert (run_dir / "execution-0.json").exists()
    assert (run_dir / "execution-1.json").exists()
    assert (run_dir / "execution-2.json").exists()
    assert (run_dir / "qualification.json").exists()
    assert (run_dir / "run.log").exists()
    
    with open(run_dir / "qualification.json") as f:
        q = json.load(f)
        assert q["status"] in ("passed", "failed")
        assert q.get("author_code_differential") == "not_run"

def test_cli_development_with_author_checkout():
    checkout_str = os.environ.get("QJL_AUTHOR_CHECKOUT")
    if not checkout_str:
        pytest.skip("QJL_AUTHOR_CHECKOUT not set")
    
    out = Path("experiments") / "turboquant" / "development"
    run_id = f"dev_test_author_{uuid.uuid4().hex[:8]}"
    args = [
        "--profile", "development",
        "--output-root", str(out),
        "--run-id", run_id,
        "--dimension", "128",
        "--sample-count", "4",
        "--batch-size", "4",
        "--bootstrap-blocks", "2",
        "--bootstrap-resamples", "10",
        "--bits", "1",
        "--author-qjl-checkout", checkout_str
    ]
    exit_code = main(args)
    assert exit_code == 0
    
    qual = out / run_id / "qualification.json"
    assert qual.exists()
    
    with open(qual) as f:
        data = json.load(f)
        assert data["author_code_differential"] != "not_run"
        gates = data.get("gates", [])
        author_gate = next(g for g in gates if g["name"] == "author_code_differential")
        assert author_gate["status"] in ("passed", "failed")
        assert "observed" in author_gate
        assert "threshold" in author_gate

def test_cli_registered_rejects_overrides():
    checkout_str = os.environ.get("QJL_AUTHOR_CHECKOUT")
    if not checkout_str:
        pytest.skip("QJL_AUTHOR_CHECKOUT not set")
    out = Path("experiments") / "turboquant" / "qualification"
    run_id = f"reg_override_{uuid.uuid4().hex[:8]}"
    args = [
        "--profile", "registered",
        "--output-root", str(out),
        "--run-id", run_id,
        "--author-qjl-checkout", checkout_str,
        "--sample-count", "4"
    ]
    with pytest.raises(SystemExit) as e:
        main(args)
    assert e.value.code != 0

def test_run_registered_workers_missing_files(tmp_path):
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    with pytest.raises(Exception):
        run_registered_workers(run_dir, run_dir / "cfg.json", run_dir / "inputs.npz")
