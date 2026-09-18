"""Tests for Task 7: Pinned Author-QJL CUDA Differential and Adapter."""

from __future__ import annotations

import os
from pathlib import Path
import pytest
import torch

try:
    from hamutay.turboquant import (
        verify_pinned_checkout,
        preflight_author_qjl,
        run_author_qjl_differential,
    )
except ImportError:
    # Public adapter functions exported from submodules if not top-level
    try:
        from hamutay.turboquant.author_qjl import (
            verify_pinned_checkout,
            preflight_author_qjl,
            run_author_qjl_differential,
        )
    except ImportError:
        import importlib.util
        oracle_path = Path("scripts/turboquant/author_qjl_oracle.py")
        if oracle_path.exists():
            spec = importlib.util.spec_from_file_location("author_qjl_oracle", oracle_path)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            verify_pinned_checkout = mod.verify_pinned_checkout
            preflight_author_qjl = mod.preflight_author_qjl
            run_author_qjl_differential = mod.run_author_qjl_differential
        else:
            raise


PINNED_COMMIT = "648b3641f96b6e95e091217220b94e4739fd4d82"
PINNED_FILE_HASHES = {
    "LICENSE": "c71d239df91726fc519c6eb72d318ec65820627232b2f796219e87dcf35d0ab4",
    "qjl_kernel/csrc/qjl_quant_kernel.cu": "d03b2fd86504554f48da48df2740d73a0cc2d1d8a28c22698da20c9ee801aefd",
    "qjl_kernel/csrc/qjl_score_kernel.cu": "848398bb6b140433aa10f4ccea16eb680ec215cb148956f09e46bbbdabdc030c",
    "models/llama3_utils_qjl.py": "725b6777b752e30b583b6834e258a849c01679c4e3c007f3b4c62212393f34c2",
}


def test_verify_pinned_checkout_hash_and_clean_checks(tmp_path: Path) -> None:
    """Verify verify_pinned_checkout validates commit, file hashes, and clean status."""
    # A non-existent directory must raise an error
    with pytest.raises((ValueError, FileNotFoundError, RuntimeError)):
        verify_pinned_checkout(tmp_path / "nonexistent_checkout")

    # A mock checkout with tampered file hash must fail
    mock_checkout = tmp_path / "mock_checkout"
    mock_checkout.mkdir()
    (mock_checkout / "LICENSE").write_text("tampered license content")
    with pytest.raises((ValueError, RuntimeError)):
        verify_pinned_checkout(mock_checkout)


def test_preflight_author_qjl_device_and_cuda_checks(tmp_path: Path) -> None:
    """Verify preflight_author_qjl rejects unsupported device names and checks toolchain."""
    # Device must be exactly 'cuda:0'
    for invalid_device in ["cuda:1", "cpu", "cuda"]:
        with pytest.raises((ValueError, RuntimeError)):
            preflight_author_qjl(checkout=tmp_path, device=invalid_device)


@pytest.mark.skipif(
    not os.environ.get("QJL_AUTHOR_CHECKOUT") or not torch.cuda.is_available(),
    reason="Live author CUDA differential requires external QJL_AUTHOR_CHECKOUT and CUDA hardware",
)
def test_author_qjl_differential_live_execution(
    author_checkout_path: Path,
    tmp_path: Path,
) -> None:
    """Verify actual differential execution against pinned author CUDA kernel within FP32 tolerance."""
    assert author_checkout_path is not None
    output_dir = tmp_path / "author_diff_output"
    output_dir.mkdir(parents=True, exist_ok=True)

    # 1. Pinned checkout verification
    checkout_info = verify_pinned_checkout(author_checkout_path)
    assert checkout_info.get("commit") == PINNED_COMMIT

    # 2. Preflight verification
    preflight_info = preflight_author_qjl(checkout=author_checkout_path, device="cuda:0")
    assert preflight_info.get("status") == "passed"

    # 3. Live differential run
    result = run_author_qjl_differential(
        checkout=author_checkout_path,
        output=output_dir,
        device="cuda:0",
    )
    assert result.get("status") == "passed"

    # 4. Artifact integrity and schema
    json_path = output_dir / "author_qjl_differential.json"
    npz_path = output_dir / "author_qjl_differential.npz"
    assert json_path.exists()
    assert npz_path.exists()

    import json
    diff_data = json.loads(json_path.read_text(encoding="utf-8"))
    assert diff_data.get("schema") == "hamutay.turboquant.author-qjl.v1"

    # 5. Enforce registered FP32 tolerances: absolute <= 1e-5, relative <= 1e-4
    max_abs_err = diff_data["max_absolute_error"]
    max_rel_err = diff_data["max_relative_error"]
    assert max_abs_err <= 1e-5, f"Absolute error {max_abs_err} exceeded 1e-5 tolerance"
    assert max_rel_err <= 1e-4, f"Relative error {max_rel_err} exceeded 1e-4 tolerance"

    # 6. Append-only refusal check: running again on same output directory must be refused
    with pytest.raises((FileExistsError, RuntimeError)):
        run_author_qjl_differential(
            checkout=author_checkout_path,
            output=output_dir,
            device="cuda:0",
        )
