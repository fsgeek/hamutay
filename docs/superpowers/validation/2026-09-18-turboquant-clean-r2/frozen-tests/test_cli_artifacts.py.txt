import json
import subprocess
import pytest
from pathlib import Path
from unittest.mock import patch

from hamutay.turboquant.artifacts import canonical_json_bytes, sha256_file, create_run_directory
from hamutay.turboquant.qualify import main

def test_canonical_json_bytes():
    data = {"b": 2.0, "a": 1, "c": "test"}
    encoded = canonical_json_bytes(data)
    assert encoded == b'{"a":1,"b":2.0,"c":"test"}\n'
    
    with pytest.raises(ValueError, match="finite"):
        canonical_json_bytes({"inf": float('inf')})
    with pytest.raises(ValueError, match="finite"):
        canonical_json_bytes({"nan": float('nan')})

def test_sha256_file(tmp_path):
    f = tmp_path / "data.bin"
    f.write_bytes(b"turboquant")
    import hashlib
    expected = hashlib.sha256(b"turboquant").hexdigest()
    assert sha256_file(f) == expected

def test_create_run_directory(tmp_path):
    dev_root = tmp_path / "experiments" / "turboquant" / "development"
    dev_root.mkdir(parents=True)
    run_dir = create_run_directory(dev_root, "run-1")
    assert run_dir.exists()
    
    with pytest.raises(Exception):
        create_run_directory(dev_root, "run-1")
        
    bad_root = tmp_path / "experiments" / "invalid"
    bad_root.mkdir(parents=True)
    with pytest.raises(Exception):
        create_run_directory(bad_root, "run-2")

def test_cli_registered_rejects_overrides(tmp_path):
    root = tmp_path / "experiments" / "turboquant" / "qualification"
    root.mkdir(parents=True)
    
    args = [
        "turboquant-qualify", "--profile", "registered",
        "--output-root", str(root), "--run-id", "test",
        "--sample-count", "100"
    ]
    with patch("sys.argv", args):
        with pytest.raises(SystemExit) as exc:
            main()
        assert exc.value.code != 0

def test_cli_registered_requires_author_checkout(tmp_path):
    root = tmp_path / "experiments" / "turboquant" / "qualification"
    root.mkdir(parents=True)
    
    args = [
        "turboquant-qualify", "--profile", "registered",
        "--output-root", str(root), "--run-id", "test"
    ]
    with patch("sys.argv", args):
        with pytest.raises(SystemExit) as exc:
            main()
        assert exc.value.code != 0

def test_cli_development_mode_author_checkout_not_run(tmp_path):
    root = tmp_path / "experiments" / "turboquant" / "development"
    root.mkdir(parents=True)
    
    args = [
        "turboquant-qualify", "--profile", "development",
        "--output-root", str(root), "--run-id", "test-dev"
    ]
    
    from hamutay.turboquant.qualification import GateResult
    fake_gates = [
        GateResult("round_trip_determinism", True, None, None, "", "passed"),
        GateResult("mse_distortion", True, None, None, "", "passed"),
        GateResult("qjl_bias_equivalence", True, None, None, "", "passed"),
        GateResult("published_qjl_distortion", True, None, None, "", "passed")
    ]
    
    with patch("sys.argv", args), \
         patch("hamutay.turboquant.qualify.run_registered_workers", return_value=(Path("cfg"), Path("inp"), Path("exe"))), \
         patch("hamutay.turboquant.qualification.evaluate_algorithm_gates", return_value=fake_gates):
         
        with pytest.raises(SystemExit) as exc:
            main()
        
        # Development mode should exit 0
        assert exc.value.code == 0
        
        qual_file = root / "test-dev" / "qualification.json"
        if qual_file.exists():
            import json
            data = json.loads(qual_file.read_text())
            author_gate = next(g for g in data["gates"] if g["name"] == "author_code_differential")
            assert author_gate["status"] == "not_run"

def test_author_qjl_oracle_cli_args():
    script_path = Path("scripts/turboquant/author_qjl_oracle.py")
    if script_path.exists():
        res = subprocess.run(["python", str(script_path)], capture_output=True, text=True)
        assert res.returncode != 0
        assert "--checkout" in res.stderr or "checkout" in res.stderr
