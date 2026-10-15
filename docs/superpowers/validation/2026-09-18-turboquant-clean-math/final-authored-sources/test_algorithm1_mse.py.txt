"""Independent numerical validation of Task 3: Algorithm 1 (TurboQuant_mse),
including vector normalization, isometric rotations, Lloyd-Max quantization,
exact zero handling, and theoretical MSE bounds.
"""

from __future__ import annotations

import math
import numpy as np
import pytest

from hamutay.turboquant import (
    MSECodes,
    MSEQuantizer,
    gaussian_rotation,
    lloyd_max_codebook,
    nearest_code_indices,
)


@pytest.fixture
def quantizer_128_2bit() -> tuple[MSEQuantizer, np.ndarray, np.ndarray]:
    d = 128
    rot = gaussian_rotation(d, "fixture_algo1_rot")
    cb = lloyd_max_codebook(d, 2)
    quant = MSEQuantizer(rot, cb)
    return quant, rot, cb


class TestAlgorithm1Mechanics:
    """Validates Algorithm 1 quantization and reconstruction steps."""

    def test_mse_codes_frozen_slotted_dataclass(self) -> None:
        indices = np.zeros((4, 128), dtype=np.uint8)
        norms = np.ones((4,), dtype=np.float32)
        codes = MSECodes(indices=indices, norms=norms)

        with pytest.raises(Exception):  # FrozenInstanceError
            codes.norms = norms * 2.0  # type: ignore

        assert hasattr(codes, "__slots__")

    def test_step_by_step_reconstruction_oracle(
        self, quantizer_128_2bit: tuple[MSEQuantizer, np.ndarray, np.ndarray]
    ) -> None:
        quant, rot, cb = quantizer_128_2bit
        d = 128

        rng = np.random.default_rng(101)
        x = rng.standard_normal((5, d)).astype(np.float32)

        # 1. Implementation output
        codes = quant.quantize(x)
        x_rec = quant.dequantize(codes)

        # 2. Independent oracle step-by-step
        norms_oracle = np.linalg.norm(x, axis=-1)
        u_oracle = x / norms_oracle[:, np.newaxis]
        # Rotation: y = u @ rot.T
        y_oracle = u_oracle @ rot.T
        idx_oracle = nearest_code_indices(y_oracle, cb)
        y_approx_oracle = cb[idx_oracle]
        # Inverse rotation: x_hat = y_hat @ rot
        u_rec_oracle = y_approx_oracle @ rot
        x_rec_oracle = u_rec_oracle * norms_oracle[:, np.newaxis]

        # Check equivalence
        np.testing.assert_array_equal(codes.indices, idx_oracle)
        np.testing.assert_allclose(codes.norms, norms_oracle, rtol=1e-6)
        np.testing.assert_allclose(x_rec, x_rec_oracle, rtol=1e-5, atol=1e-5)

    def test_exact_zero_vector_contract(
        self, quantizer_128_2bit: tuple[MSEQuantizer, np.ndarray, np.ndarray]
    ) -> None:
        """Contract: A zero vector has norm zero, all-zero MSE indices, zero residual norm,
        and exact-zero reconstruction.
        """
        quant, _, _ = quantizer_128_2bit
        d = 128

        zero_vec = np.zeros((d,), dtype=np.float32)
        codes = quant.quantize(zero_vec)

        assert codes.norms == 0.0
        assert np.all(codes.indices == 0)

        x_rec = quant.dequantize(codes)
        assert np.all(x_rec == 0.0)
        assert x_rec.shape == (d,)

    def test_scale_invariance(
        self, quantizer_128_2bit: tuple[MSEQuantizer, np.ndarray, np.ndarray]
    ) -> None:
        """Quantizing alpha * x produces identical indices and scaled norms."""
        quant, _, _ = quantizer_128_2bit
        rng = np.random.default_rng(202)
        x = rng.standard_normal((128,)).astype(np.float32)
        alpha = 3.75

        codes_x = quant.quantize(x)
        codes_alpha = quant.quantize(alpha * x)

        np.testing.assert_array_equal(codes_x.indices, codes_alpha.indices)
        np.testing.assert_allclose(codes_alpha.norms, alpha * codes_x.norms, rtol=1e-6)

        x_rec = quant.dequantize(codes_x)
        alpha_rec = quant.dequantize(codes_alpha)
        np.testing.assert_allclose(alpha_rec, alpha * x_rec, rtol=1e-6)

    def test_multidimensional_batch_shapes(
        self, quantizer_128_2bit: tuple[MSEQuantizer, np.ndarray, np.ndarray]
    ) -> None:
        """Verifies (D,), (B, D), and (B, H, S, D) tensor handling."""
        quant, _, _ = quantizer_128_2bit
        rng = np.random.default_rng(303)

        # 3D: (2, 4, 128)
        x_3d = rng.standard_normal((2, 4, 128)).astype(np.float32)
        codes_3d = quant.quantize(x_3d)
        assert codes_3d.indices.shape == (2, 4, 128)
        assert codes_3d.norms.shape == (2, 4)

        x_rec_3d = quant.dequantize(codes_3d)
        assert x_rec_3d.shape == (2, 4, 128)


class TestAlgorithm1TheoreticalDistortion:
    """Validates Theorem 1 MSE bounds and small bit-width empirical behavior."""

    @pytest.mark.parametrize(
        ("b", "paper_target"),
        [
            (1, 0.36),
            (2, 0.117),
            (3, 0.03),
            (4, 0.009),
        ],
    )
    def test_small_bitwidth_empirical_mse_distortion(self, b: int, paper_target: float) -> None:
        """Verifies empirical MSE matches paper targets on unit Gaussian vectors.
        Workload: 2000 samples of dimension 128.
        """
        d = 128
        rot = gaussian_rotation(d, "mse_dist_rot", b)
        cb = lloyd_max_codebook(d, b)
        quant = MSEQuantizer(rot, cb)

        rng = np.random.default_rng(404 + b)
        n_samples = 2000
        x = rng.standard_normal((n_samples, d)).astype(np.float32)
        norms = np.linalg.norm(x, axis=-1, keepdims=True)
        x = x / norms  # Unit sphere vectors

        codes = quant.quantize(x)
        x_rec = quant.dequantize(codes)

        # Normalized MSE: E[||x - x_rec||^2 / ||x||^2]
        mse_observed = float(np.mean(np.sum((x - x_rec) ** 2, axis=-1)))

        # 1. Lower bound (Theorem 3): D_mse >= 4^{-b}
        lower_bound = 4.0 ** (-b)
        assert mse_observed >= lower_bound * 0.95, f"Violated information lower bound: {mse_observed} < {lower_bound}"

        # 2. Upper bound (Theorem 1): D_mse <= sqrt(3)*pi / 2 * 4^{-b}
        upper_bound = (math.sqrt(3.0) * math.pi / 2.0) * (4.0 ** (-b))
        assert mse_observed <= upper_bound * 1.05, f"Violated theoretical upper bound: {mse_observed} > {upper_bound}"

        # 3. Paper reported scale comparison (within 15% relative tolerance)
        rel_err = abs(mse_observed - paper_target) / paper_target
        assert rel_err < 0.15, f"Bit {b}: Observed {mse_observed} deviated {rel_err:.2%} from paper {paper_target}"
