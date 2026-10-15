from __future__ import annotations

import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import struct
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


def _independent_array_sha256(name: str, values: np.ndarray) -> str:
    array = np.ascontiguousarray(values)
    digest = hashlib.sha256(b"hamutay.turboquant.array-stream.v1\x00")
    for field in (name.encode("utf-8"), array.dtype.str.encode("ascii")):
        digest.update(struct.pack(">Q", len(field)))
        digest.update(field)
    digest.update(struct.pack(">Q", array.ndim))
    for extent in array.shape:
        digest.update(struct.pack(">Q", extent))
    digest.update(array.tobytes(order="C"))
    return digest.hexdigest()


def _independent_unpack_little_endian(packed: np.ndarray, count: int) -> np.ndarray:
    bits = np.unpackbits(packed, axis=-1, count=count, bitorder="little")
    return np.where(bits == 1, np.float32(1.0), np.float32(-1.0))


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
    assert result["environment"]["default_cuda"] == "/usr/local/cuda"
    assert result["environment"]["default_cuda_resolved"] == ("/usr/local/cuda-13.2")
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
            "author_outlier_signs",
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
        for name in evidence.files:
            array = evidence[name]
            assert result["arrays"][name] == {
                "dtype": array.dtype.str,
                "shape": list(array.shape),
                "sha256": _independent_array_sha256(name, array),
                "values": array.tolist(),
            }

        keys = evidence["keys"]
        queries = evidence["queries"]
        projection = evidence["projection"]
        outlier_index = int(evidence["outlier_indices"].reshape(-1)[0])
        independently_projected = np.ascontiguousarray(
            keys @ projection.T, dtype=np.float32
        )
        assert not np.any(independently_projected == np.float32(0.0))
        independent_query_sketch = np.ascontiguousarray(
            queries @ projection.T, dtype=np.float32
        )
        independent_inlier_bytes = np.packbits(
            independently_projected >= np.float32(0.0),
            axis=-1,
            bitorder="little",
        )
        independent_outlier_projection = (
            keys[..., outlier_index, np.newaxis] * projection[:8, outlier_index]
        )
        independent_outlier_bytes = np.packbits(
            independent_outlier_projection > np.float32(0.0),
            axis=-1,
            bitorder="little",
        )
        np.testing.assert_array_equal(
            evidence["query_sketch"], independent_query_sketch
        )
        np.testing.assert_array_equal(
            evidence["transparent_inlier_sign_bytes"], independent_inlier_bytes
        )
        np.testing.assert_array_equal(
            evidence["author_inlier_sign_bytes"], independent_inlier_bytes
        )
        np.testing.assert_array_equal(
            evidence["author_outlier_signs"], independent_outlier_bytes
        )

        query_outlier_sketch = (
            queries[..., outlier_index, np.newaxis] * projection[:, outlier_index]
        )
        query_residual_sketch = np.ascontiguousarray(
            independent_query_sketch - query_outlier_sketch, dtype=np.float32
        )
        inlier_signs = _independent_unpack_little_endian(
            evidence["author_inlier_sign_bytes"], 128
        )
        outlier_signs = _independent_unpack_little_endian(
            evidence["author_outlier_signs"], 8
        )
        inlier_norms = np.sqrt(
            evidence["key_norms"] * evidence["key_norms"]
            - evidence["author_outlier_norms"] * evidence["author_outlier_norms"]
        ).astype(np.float32)
        inlier_sum = np.sum(
            inlier_signs * query_residual_sketch[..., np.newaxis, :],
            axis=-1,
            dtype=np.float32,
        )
        outlier_sum = np.sum(
            outlier_signs * query_outlier_sketch[..., np.newaxis, :8],
            axis=-1,
            dtype=np.float32,
        )
        independent_literal_scores = (
            np.float32(np.sqrt(np.pi / 2.0) / 128.0) * inlier_norms * inlier_sum
            + np.float32(np.sqrt(np.pi / 2.0) / 8.0)
            * evidence["author_outlier_norms"]
            * outlier_sum
        ).reshape(1, 1, 32, 1)
        np.testing.assert_array_equal(
            evidence["transparent_scores"], independent_literal_scores
        )
        np.testing.assert_allclose(
            evidence["author_scores"],
            independent_literal_scores,
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


def _comparison_arrays(author_score: np.float32) -> dict[str, np.ndarray]:
    return {
        "author_inlier_sign_bytes": np.array([255], dtype=np.uint8),
        "transparent_inlier_sign_bytes": np.array([255], dtype=np.uint8),
        "author_outlier_norms": np.array([0.0], dtype=np.float32),
        "author_scores": np.array([author_score], dtype=np.float32),
        "transparent_scores": np.array([1.0], dtype=np.float32),
        "zero_author_inlier_sign_bytes": np.array([0], dtype=np.uint8),
        "zero_transparent_inlier_sign_bytes": np.array([255], dtype=np.uint8),
    }


def test_tolerance_boundary_and_gate_detail_report_actual_conditions():
    oracle = _load_oracle_module()
    assert hasattr(oracle, "_gate_detail")

    within, within_passed = oracle._comparison_record(
        _comparison_arrays(np.float32(1.0001099))
    )
    outside = _comparison_arrays(np.float32(1.00011))
    outside["author_inlier_sign_bytes"][0] = np.uint8(0)
    outside["author_outlier_norms"][0] = np.float32(1.0)
    beyond, beyond_passed = oracle._comparison_record(outside)

    assert within_passed is True
    assert "agree" in oracle._gate_detail(within)
    assert beyond_passed is False
    failure_detail = oracle._gate_detail(beyond)
    assert "packed inlier sign bytes differ" in failure_detail
    assert "dummy outlier norms are not exact zero" in failure_detail
    assert "scores exceed" in failure_detail
    assert "agree" not in failure_detail


class _FiniteMismatchQuantExtension:
    def qjl_quant_float_float(self, keys, _indices, projection, outlier_sketch_dim):
        packed_shape = (*keys.shape[:-1], projection.shape[0] // 8)
        outlier_shape = (*keys.shape[:-1], outlier_sketch_dim // 8)
        return (
            torch.zeros(packed_shape, dtype=torch.uint8),
            torch.full(outlier_shape, 165, dtype=torch.uint8),
            torch.ones(keys.shape[:-1], dtype=torch.float32),
        )


class _FiniteMismatchScoreExtension:
    def qjl_score_cuda_float_float(
        self,
        inlier_signs,
        outlier_signs,
        _key_norms,
        _outlier_norms,
        _outlier_indices,
        query_sketch,
        _queries,
        score_projection,
    ):
        batch, heads, groups_of_keys, groups, _ = inlier_signs.shape
        return (
            outlier_signs[..., 0]
            .reshape(batch, heads, groups_of_keys * groups, 1)
            .to(dtype=torch.float32)
            + query_sketch[..., 0].reshape(batch, heads, 1, 1)
            + score_projection[0, 1]
        )


def test_forced_finite_mismatch_is_canonical_failed_oracle_and_nonzero_cli(
    monkeypatch, tmp_path
):
    oracle = _load_oracle_module()
    monkeypatch.setattr(
        oracle,
        "preflight_author_qjl",
        lambda **_kwargs: {"environment": {}, "upstream": {}},
    )
    monkeypatch.setattr(
        oracle,
        "_build_extensions",
        lambda _checkout: (
            _FiniteMismatchQuantExtension(),
            _FiniteMismatchScoreExtension(),
        ),
    )
    monkeypatch.setattr(
        oracle, "_to_device", lambda values, _device: torch.from_numpy(values)
    )
    monkeypatch.setattr(oracle.torch.cuda, "synchronize", lambda _device: None)
    output = tmp_path / "finite-mismatch"

    result = oracle.run_author_qjl_differential(
        checkout=_AUTHOR_CHECKOUT, output=output, device="cuda:0"
    )

    persisted = json.loads((output / "author_qjl_differential.json").read_text())
    assert persisted == result
    assert result["status"] == "failed"
    assert result["gate"]["passed"] is False
    assert "error" not in result
    assert np.isfinite(result["comparisons"]["scores"]["max_absolute_error"])
    with np.load(output / "author_qjl_differential.npz", allow_pickle=False) as data:
        expected_score = (
            data["author_outlier_signs"][..., 0].reshape(1, 1, 32, 1).astype(np.float32)
            + data["query_sketch"][..., 0].reshape(1, 1, 1, 1)
            + data["projection"][1, 0]
        )
        np.testing.assert_array_equal(data["author_scores"], expected_score)
    monkeypatch.setattr(oracle, "run_author_qjl_differential", lambda **_kwargs: result)
    assert (
        oracle.main(
            ["--checkout", str(_AUTHOR_CHECKOUT), "--output", str(tmp_path / "cli")]
        )
        == 1
    )


@pytest.mark.parametrize(
    ("fault", "message"),
    [
        ("commit", "checkout commit mismatch"),
        ("origin", "origin mismatch"),
        ("hash", "SHA-256 mismatch for LICENSE"),
        ("symlink", "not a regular file: LICENSE"),
    ],
)
def test_checkout_pin_faults_stop_before_cached_extension_load(
    fault, message, monkeypatch, tmp_path
):
    oracle = _load_oracle_module()
    checkout = tmp_path / "checkout"
    checkout.mkdir()
    if fault == "hash":
        (checkout / "LICENSE").write_text("wrong license", encoding="utf-8")
    elif fault == "symlink":
        target = tmp_path / "license-target"
        target.write_text("not the pinned file", encoding="utf-8")
        (checkout / "LICENSE").symlink_to(target)

    def fake_run_text(*command, cwd=None):
        del cwd
        if command[1:] == ("rev-parse", "HEAD"):
            return "0" * 40 if fault == "commit" else oracle.UPSTREAM_COMMIT
        if command[1:] == (
            "status",
            "--porcelain=v1",
            "--untracked-files=all",
        ):
            return ""
        if command[1:] == ("remote", "get-url", "origin"):
            return (
                "https://example.invalid/QJL"
                if fault == "origin"
                else (oracle.UPSTREAM_REPOSITORY)
            )
        raise AssertionError(f"unexpected command: {command}")

    monkeypatch.setattr(oracle, "_run_text", fake_run_text)
    monkeypatch.setattr(oracle, "_validate_compiler_and_device", lambda _device: {})
    monkeypatch.setattr(
        oracle,
        "_build_extensions",
        lambda _checkout: (_ for _ in ()).throw(
            AssertionError("cached extension load must not run")
        ),
    )

    with pytest.raises(ValueError, match=message):
        oracle.run_author_qjl_differential(
            checkout=checkout, output=tmp_path / "output", device="cuda:0"
        )


@pytest.mark.parametrize(
    "fault", ["selected_compiler", "default_cuda", "absent_default_cuda"]
)
def test_toolchain_faults_stop_before_cached_extension_load(
    fault, monkeypatch, tmp_path
):
    oracle = _load_oracle_module()
    monkeypatch.setenv("CUDA_HOME", "/usr/local/cuda-12.8")
    monkeypatch.setattr(
        oracle,
        "_build_extensions",
        lambda _checkout: (_ for _ in ()).throw(
            AssertionError("cached extension load must not run")
        ),
    )
    expected = "first on PATH"
    if fault == "selected_compiler":
        monkeypatch.setattr(oracle.shutil, "which", lambda _name: "/usr/bin/nvcc")
    elif fault == "default_cuda":
        wrong_default = tmp_path / "cuda"
        wrong_target = tmp_path / "cuda-99.9"
        wrong_target.mkdir()
        wrong_default.symlink_to(wrong_target, target_is_directory=True)
        monkeypatch.setattr(oracle, "DEFAULT_CUDA", wrong_default, raising=False)
        expected = "default /usr/local/cuda"
    else:
        monkeypatch.setattr(
            oracle, "DEFAULT_CUDA", tmp_path / "missing-cuda", raising=False
        )
        expected = "default /usr/local/cuda"

    with pytest.raises(RuntimeError, match=expected):
        oracle.run_author_qjl_differential(
            checkout=_AUTHOR_CHECKOUT,
            output=tmp_path / "output",
            device="cuda:0",
        )
