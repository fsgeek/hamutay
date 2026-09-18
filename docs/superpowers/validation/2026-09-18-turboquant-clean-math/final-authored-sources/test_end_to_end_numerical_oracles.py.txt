"""Independent numerical validation: End-to-end mathematical oracles and sensitivity checks
for TurboQuant R1.
"""

from __future__ import annotations

import math
import numpy as np
import pytest

from hamutay.turboquant import (
    MSEQuantizer,
    ProductQuantizer,
    canonical_qr,
    gaussian_rotation,
    lloyd_max_codebook,
)


class TestEndToEndNumericalOracles:
    """Validates complete numerical pipeline against independent algebraic oracles."""

    def test_sensitivity_row_orthogonal_projection_preserves_unbiasedness(self) -> None:
        """Design sensitivity check: Compare paper i.i.d. Gaussian projection S
        against row-orthogonalized projection S_orth = sqrt(d) * QR(S).
        Both must yield unbiased inner product estimates.
        """
        d = 128
        rot = gaussian_rotation(d, "sens_rot")
        cb = lloyd_max_codebook(d, 1)  # b=2 total product quantizer
        mse_quant = MSEQuantizer(rot, cb)

        rng = np.random.default_rng(2020)
        s_raw = rng.standard_normal((d, d), dtype=np.float64)
        # 1. Paper projection: iid Gaussian
        proj_paper = s_raw.astype(np.float32)

        # 2. Row-orthogonalized projection: sqrt(d) * Q
        q = canonical_qr(s_raw)
        proj_orth = (math.sqrt(d) * q).astype(np.float32)

        pq_paper = ProductQuantizer(mse_quant, proj_paper)
        pq_orth = ProductQuantizer(mse_quant, proj_orth)

        n = 2000
        x = rng.standard_normal((n, d)).astype(np.float32)
        y = rng.standard_normal((n, d)).astype(np.float32)
        x /= np.linalg.norm(x, axis=-1, keepdims=True)
        y /= np.linalg.norm(y, axis=-1, keepdims=True)

        dots_true = np.sum(y * x, axis=-1)

        codes_paper = pq_paper.quantize(x)
        dots_paper = pq_paper.estimate_inner_products(y, codes_paper)
        err_paper = float(np.mean(dots_paper - dots_true))

        codes_orth = pq_orth.quantize(x)
        dots_orth = pq_orth.estimate_inner_products(y, codes_orth)
        err_orth = float(np.mean(dots_orth - dots_true))

        # Both empirical biases must be negligible (< 0.01)
        assert abs(err_paper) < 0.01
        assert abs(err_orth) < 0.01

    def test_finite_precision_stability_on_extreme_vectors(self) -> None:
        """Verifies no NaNs, Infs, or underflow errors on sparse and collinear vectors."""
        d = 128
        rot = gaussian_rotation(d, "stability_rot")
        cb = lloyd_max_codebook(d, 2)
        mse_quant = MSEQuantizer(rot, cb)
        proj = gaussian_rotation(d, "stability_proj")
        prod_quant = ProductQuantizer(mse_quant, proj)

        # 1. One-hot vector e_0
        e0 = np.zeros((d,), dtype=np.float32)
        e0[0] = 1.0

        codes_mse = mse_quant.quantize(e0)
        rec_mse = mse_quant.dequantize(codes_mse)
        assert not np.any(np.isnan(rec_mse))
        assert not np.any(np.isinf(rec_mse))

        codes_prod = prod_quant.quantize(e0)
        rec_prod = prod_quant.dequantize(codes_prod)
        assert not np.any(np.isnan(rec_prod))
        assert not np.any(np.isinf(rec_prod))

        # 2. Huge and tiny magnitude vectors
        huge_v = e0 * 1e15
        tiny_v = e0 * 1e-15

        rec_huge = prod_quant.dequantize(prod_quant.quantize(huge_v))
        rec_tiny = prod_quant.dequantize(prod_quant.quantize(tiny_v))
        assert math.isclose(np.linalg.norm(rec_huge), 1e15, rel_tol=0.2)
        assert math.isclose(np.linalg.norm(rec_tiny), 1e-15, rel_tol=0.2)

    def test_inner_product_variance_matches_lemma4_bound(self) -> None:
        """Validates Lemma 4 QJL variance bound: Var(<y, QJL(r)>) <= pi / (2d) * ||y||^2 * ||r||^2."""
        d = 128
        rot = gaussian_rotation(d, "var_rot")
        cb_0 = lloyd_max_codebook(d, 0)  # r = x exactly
        mse_quant = MSEQuantizer(rot, cb_0)

        rng = np.random.default_rng(3030)
        proj = rng.standard_normal((d, d)).astype(np.float32)
        prod_quant = ProductQuantizer(mse_quant, proj)

        n = 4000
        x = rng.standard_normal((n, d)).astype(np.float32)
        y = rng.standard_normal((n, d)).astype(np.float32)
        x /= np.linalg.norm(x, axis=-1, keepdims=True)
        y /= np.linalg.norm(y, axis=-1, keepdims=True)

        true_dots = np.sum(y * x, axis=-1)
        codes = prod_quant.quantize(x)
        est_dots = prod_quant.estimate_inner_products(y, codes)

        sample_variance = float(np.var(est_dots - true_dots))
        # Theoretical upper bound: pi / (2d) * 1.0 * 1.0
        theoretical_var_bound = math.pi / (2.0 * d)

        assert sample_variance <= theoretical_var_bound * 1.08, (
            f"Observed variance {sample_variance} exceeded Lemma 4 bound {theoretical_var_bound}"
        )
