from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import subprocess

import numpy as np
import pytest
import torch


_CHECKOUT_ENVIRONMENT = "QJL_AUTHOR_CHECKOUT"
_CUDA_HOME = Path("/usr/local/cuda-12.8")
_NVCC = _CUDA_HOME / "bin" / "nvcc"


def _load_oracle_module():
    path = (
        Path(__file__).resolve().parents[2] / "scripts/turboquant/author_qjl_oracle.py"
    )
    spec = importlib.util.spec_from_file_location("hamutay_author_qjl_oracle", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _author_checkout_or_skip() -> Path:
    if not torch.cuda.is_available():
        pytest.skip(
            "author QJL differential requires CUDA availability",
            allow_module_level=True,
        )
    checkout_value = os.environ.get(_CHECKOUT_ENVIRONMENT)
    if not checkout_value:
        pytest.skip(
            "author QJL differential requires QJL_AUTHOR_CHECKOUT",
            allow_module_level=True,
        )
    checkout = Path(checkout_value)
    if not checkout.is_dir():
        pytest.skip(
            "QJL_AUTHOR_CHECKOUT must name an existing checkout directory",
            allow_module_level=True,
        )
    if not _NVCC.is_file():
        pytest.skip(
            "author QJL differential requires /usr/local/cuda-12.8/bin/nvcc",
            allow_module_level=True,
        )

    selected_cuda_home = os.environ.get("CUDA_HOME")
    if selected_cuda_home is None or Path(selected_cuda_home).resolve() != _CUDA_HOME:
        pytest.skip(
            "author QJL differential requires CUDA_HOME=/usr/local/cuda-12.8",
            allow_module_level=True,
        )
    selected_nvcc = shutil.which("nvcc")
    if selected_nvcc is None or Path(selected_nvcc).resolve() != _NVCC:
        pytest.skip(
            "author QJL differential requires /usr/local/cuda-12.8/bin first on PATH",
            allow_module_level=True,
        )
    completed = subprocess.run(
        [str(_NVCC), "--version"], check=True, capture_output=True, text=True
    )
    match = re.search(r"release\s+(\d+\.\d+)", completed.stdout)
    if match is None or match.group(1) != "12.8":
        pytest.skip(
            "selected nvcc must report CUDA release 12.8", allow_module_level=True
        )
    if torch.version.cuda != "12.8":
        pytest.skip(
            "PyTorch must report torch.version.cuda == 12.8",
            allow_module_level=True,
        )
    return checkout


_AUTHOR_CHECKOUT = _author_checkout_or_skip()


def test_author_qjl_matches_transparent_reference_and_records_evidence(tmp_path):
    run_author_qjl_differential = _load_oracle_module().run_author_qjl_differential

    output = tmp_path / "author-qjl"
    result = run_author_qjl_differential(
        checkout=_AUTHOR_CHECKOUT, output=output, device="cuda:0"
    )

    assert result["schema"] == "hamutay.turboquant.author-qjl.v1"
    assert result["status"] == "passed"
    assert result["gate"] == {
        "name": "author_code_differential",
        "passed": True,
        "observed": {
            "inlier_sign_bytes_equal": True,
            "max_absolute_score_error": result["comparisons"]["scores"][
                "max_absolute_error"
            ],
            "max_relative_score_error": result["comparisons"]["scores"][
                "max_relative_error"
            ],
            "outlier_norms_exact_zero": True,
        },
        "threshold": {"atol": 1e-5, "rtol": 1e-4},
        "detail": (
            "Pinned author QJL FP32 packed inlier signs and scores agree with "
            "the transparent paper-literal reference; the dummy outlier channel "
            "is exact zero."
        ),
    }
    assert result["upstream"]["commit"] == ("648b3641f96b6e95e091217220b94e4739fd4d82")
    assert result["upstream"]["clean"] is True
    assert result["extensions"] == {
        "quant": "hamutay_qjl_quant_648b3641",
        "score": "hamutay_qjl_score_648b3641",
    }
    assert result["batch"] == {
        "dimension": 128,
        "key_shape": [1, 1, 1, 32, 128],
        "outlier_index_shape": [1, 1, 1, 1],
        "outlier_sketch_dim": 8,
        "query_shape": [1, 1, 1, 128],
    }
    assert result["conventions"] == {
        "author_exact_zero_sign": "negative",
        "bit_packing": "little-endian within each byte",
        "score_projection_layout": "S.T contiguous",
        "transparent_exact_zero_sign": "positive",
        "quant_projection_layout": "S",
        "query_sketch": "query @ S.T",
    }
    assert result["comparisons"]["generic_projection_has_no_exact_zero"] is True
    assert result["comparisons"]["inlier_sign_bytes_equal"] is True
    assert result["comparisons"]["dummy_outlier_norms_exact_zero"] is True
    assert result["comparisons"]["scores"]["within_tolerance"] is True

    json_path = output / "author_qjl_differential.json"
    npz_path = output / "author_qjl_differential.npz"
    assert json_path.read_bytes() == (
        json.dumps(
            result,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
        + b"\n"
    )
    with np.load(npz_path, allow_pickle=False) as evidence:
        assert set(evidence.files) == {
            "author_inlier_sign_bytes",
            "author_outlier_norms",
            "author_scores",
            "key_norms",
            "keys",
            "outlier_indices",
            "projection",
            "queries",
            "query_sketch",
            "transparent_inlier_sign_bytes",
            "transparent_scores",
            "zero_author_inlier_sign_bytes",
            "zero_projection",
            "zero_transparent_inlier_sign_bytes",
        }
        assert evidence["keys"].shape == (1, 1, 1, 32, 128)
        assert evidence["queries"].shape == (1, 1, 1, 128)
        assert evidence["keys"].dtype == np.float32
        assert evidence["queries"].dtype == np.float32
        assert np.all(evidence["keys"][..., 127] == np.float32(0.0))
        assert np.all(evidence["queries"][..., 127] == np.float32(0.0))
        assert np.all(evidence["author_outlier_norms"] == np.float32(0.0))
        np.testing.assert_array_equal(
            evidence["author_inlier_sign_bytes"],
            evidence["transparent_inlier_sign_bytes"],
        )
        np.testing.assert_allclose(
            evidence["author_scores"],
            evidence["transparent_scores"],
            atol=1e-5,
            rtol=1e-4,
        )


def test_author_qjl_exact_zero_projection_has_declared_one_bit_difference(tmp_path):
    run_author_qjl_differential = _load_oracle_module().run_author_qjl_differential

    output = tmp_path / "author-qjl-zero"
    result = run_author_qjl_differential(
        checkout=_AUTHOR_CHECKOUT, output=output, device="cuda:0"
    )

    convention = result["comparisons"]["constructed_zero_projection"]
    assert convention == {
        "author_byte": 0,
        "differing_bits_per_byte": 8,
        "expected_declared_difference": True,
        "transparent_byte": 255,
    }
    with np.load(output / "author_qjl_differential.npz", allow_pickle=False) as data:
        assert np.all(data["zero_author_inlier_sign_bytes"] == np.uint8(0))
        assert np.all(data["zero_transparent_inlier_sign_bytes"] == np.uint8(255))
