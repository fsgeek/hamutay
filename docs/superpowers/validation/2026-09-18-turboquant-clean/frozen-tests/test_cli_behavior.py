import subprocess
import pytest
import json

def run_cli(*args):
    return subprocess.run(["turboquant-qualify", *args], capture_output=True, text=True)

def test_cli_development_mode_success(dev_output_root, run_id):
    res = run_cli(
        "--profile", "development",
        "--output-root", str(dev_output_root),
        "--run-id", run_id
    )
    assert res.returncode == 0, f"Development mode failed: {res.stderr}\nStdout: {res.stdout}"
    
    run_dir = dev_output_root / run_id
    assert run_dir.exists()
    
    qual_file = run_dir / "qualification.json"
    assert qual_file.exists()
    
    with open(qual_file) as f:
        data = json.load(f)
    
    gates = data.get("gates", [])
    author_gate = next((g for g in gates if g["name"] == "author_code_differential"), None)
    if author_gate:
        assert author_gate["status"] == "not_run"

def test_cli_registered_mode_refusal_missing_checkout(reg_output_root, run_id):
    res = run_cli(
        "--profile", "registered",
        "--output-root", str(reg_output_root),
        "--run-id", run_id
    )
    assert res.returncode != 0

def test_cli_namespace_refusal(reg_output_root, dev_output_root, run_id):
    res1 = run_cli(
        "--profile", "development",
        "--output-root", str(reg_output_root),
        "--run-id", run_id
    )
    assert res1.returncode != 0
    
    res2 = run_cli(
        "--profile", "registered",
        "--output-root", str(dev_output_root),
        "--run-id", run_id,
        "--author-qjl-checkout", "/dummy"
    )
    assert res2.returncode != 0

def test_cli_refuse_existing_directory(dev_output_root, run_id):
    run_dir = dev_output_root / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    
    res = run_cli(
        "--profile", "development",
        "--output-root", str(dev_output_root),
        "--run-id", run_id
    )
    assert res.returncode != 0

@pytest.mark.slow
def test_cli_registered_mode_success(reg_output_root, run_id, author_qjl_checkout):
    res = run_cli(
        "--profile", "registered",
        "--output-root", str(reg_output_root),
        "--run-id", run_id,
        "--author-qjl-checkout", str(author_qjl_checkout)
    )
    assert res.returncode == 0, f"Registered mode failed: {res.stderr}"
    
    run_dir = reg_output_root / run_id
    qual_file = run_dir / "qualification.json"
    assert qual_file.exists()
    
    with open(qual_file) as f:
        data = json.load(f)
    
    gates = data.get("gates", [])
    assert len(gates) == 5
    for gate in gates:
        assert gate["passed"] is True
        assert gate["status"] == "passed"
    
    expected_files = [
        "manifest.json", 
        "resolved_inputs.npz", 
        "execution-0.json", 
        "execution-1.json", 
        "execution-2.json", 
        "qualification.json", 
        "run.log"
    ]
    for fname in expected_files:
        assert (run_dir / fname).exists()
