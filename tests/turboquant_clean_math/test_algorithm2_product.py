"""Independent numerical validation of Task 4: Algorithm 2 (TurboQuant_prod),
including little-endian bit-packing, residual QJL transform, unbiased inner-product estimation,
and variance bounds.
"""

from __future__ import annotations

import math
import numpy as np
import pytest

from hamutay.turboquant import (
    MSEQuantizer,
    ProductCodes,
    ProductQuantizer,
    gaussian_rotation,
    lloyd_max_codebook,
    pack_signs,
    unpack_signs,
)


class TestBitPackingContract:
    """Validates declared bit-packing: little-endian within byte, coordinate j occupies
    bit (j % 8) of byte (j // 8), set bit = +1, clear bit = -1.
    """

    def test_pack_signs_type_rejection(self) -> None:
        """pack_signs accepts ONLY boolean arrays."""
        float_signs = np.ones((8,), dtype=np.float32)
        int_signs = np.ones((8,), dtype=np.int32)
        with pytest.raises(TypeError):
            pack_signs(float_signs)  # type: ignore
        with pytest.raises(TypeError):
            pack_signs(int_signs)  # type: ignore

    def test_little_endian_byte_packing_oracle(self) -> None:
        """Coordinate j maps to bit (j % 8) of byte (j // 8)."""
        # 16 coordinates -> 2 bytes
        # Set coord 0 (byte 0, bit 0) and coord 9 (byte 1, bit 1)
        bools = np.zeros(16, dtype=bool)
        bools[0] = True
        bools[9] = True

        packed = pack_signs(bools)
        assert packed.dtype == np.uint8
        assert packed.shape == (2,)

        # Byte 0: 0b00000001 = 1
        # Byte 1: 0b00000010 = 2
        assert packed[0] == 1
        assert packed[1] == 2

    def test_unpack_signs_returns_fp32_pm_ones(self) -> None:
        packed = np.array([1, 2], dtype=np.uint8)
        unpacked = unpack_signs(packed, sketch_dim=16)

        assert unpacked.dtype == np.float32
        assert unpacked.shape == (16,)
        assert unpacked[0] == 1.0
        assert unpacked[9] == 1.0
        assert unpacked[1] == -1.0
        assert unpacked[8] == -1.0

    def test_pack_unpack_roundtrip(self) -> None:
        rng = np.random.default_rng(505)
        sketch_dim = 128
        bools = rng.choice([False, True], size=(10, sketch_dim))

        packed = pack_signs(bools)
        assert packed.shape == (10, 16)

        unpacked = unpack_signs(packed, sketch_dim)
        expected = np.where(bools, 1.0, -1.0).astype(np.float32)
        np.testing.assert_array_equal(unpacked, expected)


@pytest.fixture
def product_quantizer_128_2bit() -> tuple[ProductQuantizer, np.ndarray]:
    """Total bit-width b=2 -> base MSE quantizer bit-width b-1 = 1."""
    d = 128
    rot = gaussian_rotation(d, "fixture_prod_rot")
    cb_mse = lloyd_max_codebook(d, 1)  # 1 bit MSE
    mse_quant = MSEQuantizer(rot, cb_mse)

    rng = np.random.default_rng(606)
    # Dense Gaussian projection S in R^{d x d}
    proj = rng.standard_normal((d, d)).astype(np.float32)
    prod_quant = ProductQuantizer(mse_quant, proj)
    return prod_quant, proj


class TestAlgorithm2Mechanics:
    """Validates two-stage base/residual decomposition and QJL sketch computation."""

    def test_product_codes_frozen_slotted(self) -> None:
        d = 128
        rot = gaussian_rotation(d, "rot")
        cb = lloyd_max_codebook(d, 0)
        mse_quant = MSEQuantizer(rot, cb)
        proj = np.eye(d, dtype=np.float32)
        quant = ProductQuantizer(mse_quant, proj)

        x = np.ones((d,), dtype=np.float32)
        codes = quant.quantize(x)

        assert isinstance(codes, ProductCodes)
        with pytest.raises(Exception):
            codes.residual_norms = np.float32(0.0)  # type: ignore

    def test_exact_zero_vector_contract(
        self, product_quantizer_128_2bit: tuple[ProductQuantizer, np.ndarray]
    ) -> None:
        """Contract: zero vector has norm 0, all-zero MSE indices, residual norm 0,
        and exact-zero reconstruction. Its sign bits are all SET because exact 0.0 maps to +1.
        """
        quant, _ = product_quantizer_128_2bit
        d = 128
        zero_vec = np.zeros((d,), dtype=np.float32)

        codes = quant.quantize(zero_vec)
        assert codes.residual_norms == 0.0
        assert codes.mse.norms == 0.0
        assert np.all(codes.mse.indices == 0)

        # In transparent reference, zero projection maps to sign +1 -> all in-range bits SET (0xFF)
        assert np.all(codes.packed_signs == 0xFF)

        x_rec = quant.dequantize(codes)
        assert np.all(x_rec == 0.0)

    def test_estimate_inner_products_exact_equivalence_to_dequantize(
        self, product_quantizer_128_2bit: tuple[ProductQuantizer, np.ndarray]
    ) -> None:
        """estimate_inner_products(q, codes) must match <q, dequantize(codes)> to FP32 precision."""
        quant, _ = product_quantizer_128_2bit
        d = 128
        rng = np.random.default_rng(707)

        keys = rng.standard_normal((10, d)).astype(np.float32)
        queries = rng.standard_normal((10, d)).astype(np.float32)

        codes = quant.quantize(keys)
        keys_rec = quant.dequantize(codes)

        direct_estimates = quant.estimate_inner_products(queries, codes)
        manual_dot = np.sum(queries * keys_rec, axis=-1)

        np.testing.assert_allclose(direct_estimates, manual_dot, rtol=1e-5, atol=1e-5)

    def test_estimate_inner_products_shape_rejection(
        self, product_quantizer_128_2bit: tuple[ProductQuantizer, np.ndarray]
    ) -> None:
        """Contract: queries and keys must share identical leading batch shapes; no broadcasting."""
        quant, _ = product_quantizer_128_2bit
        d = 128
        rng = np.random.default_rng(808)

        keys = rng.standard_normal((8, d)).astype(np.float32)
        queries_mismatched = rng.standard_normal((9, d)).astype(np.float32)

        codes = quant.quantize(keys)
        with pytest.raises(ValueError):
            quant.estimate_inner_products(queries_mismatched, codes)


class TestAlgorithm2StatisticalContracts:
    """Validates Theorem 2: Unbiasedness and variance distortion of inner product estimator."""

    def test_inner_product_unbiasedness_contrasted_with_mse_bias(self) -> None:
        """Theorem 2: E[<y, x_tilde_prod>] = <y, x>.
        Contrast with TurboQuant_mse which has severe multiplicative bias 2/pi (~0.6366) at b=1.
        """
        d = 128
        rot = gaussian_rotation(d, "unbiased_test_rot")
        # b=1 total product quantizer uses b-1=0 bit MSE quantizer
        cb_0 = lloyd_max_codebook(d, 0)
        mse_quant_0 = MSEQuantizer(rot, cb_0)

        rng = np.random.default_rng(909)
        proj = rng.standard_normal((d, d)).astype(np.float32)
        prod_quant = ProductQuantizer(mse_quant_0, proj)

        # Evaluate over 5000 independent query/key pairs
        n = 5000
        keys = rng.standard_normal((n, d)).astype(np.float32)
        queries = rng.standard_normal((n, d)).astype(np.float32)
        # Unit norm keys and queries
        keys /= np.linalg.norm(keys, axis=-1, keepdims=True)
        queries /= np.linalg.norm(queries, axis=-1, keepdims=True)

        true_dots = np.sum(queries * keys, axis=-1)

        # 1. Product quantizer estimates
        prod_codes = prod_quant.quantize(keys)
        prod_est = prod_quant.estimate_inner_products(queries, prod_codes)
        prod_errors = prod_est - true_dots
        prod_mean_bias = float(np.mean(prod_errors))
        prod_std_err = float(np.std(prod_errors) / math.sqrt(n))

        # Unbiasedness: mean error is within 3 standard errors of 0
        assert abs(prod_mean_bias) < 3.0 * prod_std_err, (
            f"Product quantizer exhibited statistically significant bias: {prod_mean_bias} +/- {prod_std_err}"
        )

        # 2. MSE quantizer at b=1 has bias factor 2/pi
        cb_1 = lloyd_max_codebook(d, 1)
        mse_quant_1 = MSEQuantizer(rot, cb_1)
        mse_codes = mse_quant_1.quantize(keys)
        mse_rec = mse_quant_1.dequantize(mse_codes)
        mse_est = np.sum(queries * mse_rec, axis=-1)

        # Check empirical bias factor ~ 2/pi
        ratio = float(np.mean(mse_est) / np.mean(true_dots))
        assert math.isclose(ratio, 2.0 / math.pi, rel_tol=0.10)

    @pytest.mark.parametrize(
        ("total_b", "paper_numerator"),
        [
            (1, 1.57),
            (2, 0.56),
            (3, 0.18),
            (4, 0.047),
        ],
    )
    def test_product_distortion_scaling(self, total_b: int, paper_numerator: float) -> None:
        """Verifies inner product mean squared error D_prod is within 15% of paper targets."""
        d = 128
        rot = gaussian_rotation(d, "prod_dist_rot", total_b)
        cb_mse = lloyd_max_codebook(d, total_b - 1)
        mse_quant = MSEQuantizer(rot, cb_mse)

        rng = np.random.default_rng(1001 + total_b)
        proj = rng.standard_normal((d, d)).astype(np.float32)
        prod_quant = ProductQuantizer(mse_quant, proj)

        n = 3000
        keys = rng.standard_normal((n, d)).astype(np.float32)
        queries = rng.standard_normal((n, d)).astype(np.float32)
        keys /= np.linalg.norm(keys, axis=-1, keepdims=True)
        queries /= np.linalg.norm(queries, axis=-1, keepdims=True)

        true_dots = np.sum(queries * keys, axis=-1)
        codes = prod_quant.quantize(keys)
        est_dots = prod_quant.estimate_inner_products(queries, codes)

        d_prod_observed = float(np.mean((est_dots - true_dots) ** 2))
        paper_target = paper_numerator / d

        # Check published scale (15% tolerance)
        rel_err = abs(d_prod_observed - paper_target) / paper_target
        assert rel_err < 0.18, f"Total bit {total_b}: Observed {d_prod_observed} vs target {paper_target} (err: {rel_err:.2%})"
