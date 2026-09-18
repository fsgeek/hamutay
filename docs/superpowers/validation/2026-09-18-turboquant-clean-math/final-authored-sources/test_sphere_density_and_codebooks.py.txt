"""Independent numerical validation of Task 2: Lemma 1 sphere-coordinate distribution,
Lloyd-Max scalar codebooks, and exact FP64 midpoint tie-breaking.
"""

from __future__ import annotations

import math
import numpy as np
import pytest
from scipy.integrate import quad
from scipy.special import gammaln

from hamutay.turboquant import (
    lloyd_max_codebook,
    nearest_code_indices,
    sphere_coordinate_density,
)


def independent_sphere_density_fp64(x: float, d: int) -> float:
    """Exact mathematical oracle for Lemma 1:
    f_X(x) = Gamma(d/2) / (sqrt(pi) * Gamma((d-1)/2)) * (1 - x^2)^((d-3)/2) on [-1, 1].
    """
    if abs(x) >= 1.0:
        return 0.0
    log_c = gammaln(d / 2.0) - 0.5 * math.log(math.pi) - gammaln((d - 1.0) / 2.0)
    c = math.exp(log_c)
    return c * ((1.0 - x * x) ** ((d - 3.0) / 2.0))


class TestSphereCoordinateDensity:
    """Validates the continuous coordinate probability density of random vectors on S^{d-1}."""

    @pytest.mark.parametrize("d", [4, 8, 16, 64, 128])
    def test_density_evaluation_against_independent_oracle(self, d: int) -> None:
        grid = np.linspace(-0.99, 0.99, 50, dtype=np.float64)
        for x_val in grid:
            expected = independent_sphere_density_fp64(x_val, d)
            observed = sphere_coordinate_density(x_val, d)
            assert math.isclose(observed, expected, rel_tol=1e-7, abs_tol=1e-12)

    @pytest.mark.parametrize("d", [4, 16, 128])
    def test_density_normalizes_to_one(self, d: int) -> None:
        """Total probability over [-1, 1] must equal 1.0."""
        area, _ = quad(lambda x: sphere_coordinate_density(x, d), -1.0, 1.0, epsabs=1e-12, epsrel=1e-10)
        assert math.isclose(area, 1.0, rel_tol=1e-8)

    @pytest.mark.parametrize("d", [8, 32, 128])
    def test_density_variance_equals_reciprocal_dimension(self, d: int) -> None:
        """Crucial sphere property: E[X_j^2] = 1/d by symmetry on S^{d-1}."""
        var, _ = quad(lambda x: (x**2) * sphere_coordinate_density(x, d), -1.0, 1.0, epsabs=1e-12, epsrel=1e-10)
        expected_var = 1.0 / d
        assert math.isclose(var, expected_var, rel_tol=1e-7)

    def test_density_symmetry_and_support_boundaries(self) -> None:
        d = 128
        assert sphere_coordinate_density(0.05, d) == sphere_coordinate_density(-0.05, d)
        # Outside [-1, 1] support
        assert sphere_coordinate_density(1.0001, d) == 0.0
        assert sphere_coordinate_density(-1.5, d) == 0.0

    def test_density_vectorized_array_input(self) -> None:
        xs = np.array([-0.5, 0.0, 0.5], dtype=np.float64)
        out = sphere_coordinate_density(xs, 128)
        assert isinstance(out, np.ndarray)
        assert out.shape == (3,)
        assert math.isclose(out[0], out[2], rel_tol=1e-12)


class TestLloydMaxCodebook:
    """Validates Lloyd-Max continuous 1D k-means codebook construction."""

    @pytest.mark.parametrize("bits", [0, 1, 2, 3, 4])
    def test_codebook_shapes_dtypes_and_monotonicity(self, bits: int) -> None:
        d = 128
        cb = lloyd_max_codebook(d, bits)

        assert cb.dtype == np.float32
        assert cb.shape == (2**bits,)
        # Strictly increasing
        if bits > 0:
            assert np.all(np.diff(cb) > 0.0)

    def test_zero_bit_codebook_boundary(self) -> None:
        """b=0 has 2^0 = 1 centroid at 0.0 (used by Algorithm 2 1-bit product quantizer)."""
        cb = lloyd_max_codebook(128, 0)
        assert cb.shape == (1,)
        assert cb[0] == 0.0

    def test_one_bit_codebook_exact_analytical_oracle(self) -> None:
        """For b=1, optimal centroids are +/- Gamma(d/2) / (sqrt(pi) * Gamma((d+1)/2))."""
        d = 128
        cb = lloyd_max_codebook(d, 1)
        assert cb.shape == (2,)

        # Exact positive centroid analytical formula
        log_pos = gammaln(d / 2.0) - 0.5 * math.log(math.pi) - gammaln((d + 1.0) / 2.0)
        c_star = math.exp(log_pos)

        np.testing.assert_allclose(cb[0], -c_star, rtol=1e-6)
        np.testing.assert_allclose(cb[1], c_star, rtol=1e-6)

    @pytest.mark.parametrize("bits", [1, 2, 3, 4])
    def test_codebook_exact_symmetry(self, bits: int) -> None:
        """Codebook must be strictly symmetric around origin: c_i == -c_{K-1-i}."""
        cb = lloyd_max_codebook(128, bits)
        k = 2**bits
        for i in range(k // 2):
            np.testing.assert_allclose(cb[i], -cb[k - 1 - i], atol=1e-7)

    @pytest.mark.parametrize("bits", [1, 2, 3])
    def test_codebook_lloyd_max_optimality_condition(self, bits: int) -> None:
        """Verifies each centroid equals the conditional expectation of its Voronoi cell."""
        d = 128
        cb = lloyd_max_codebook(d, bits)
        k = 2**bits

        # Cell midpoints in FP64
        cb_f64 = cb.astype(np.float64)
        midpoints = (cb_f64[:-1] + cb_f64[1:]) / 2.0
        boundaries = np.concatenate(([-1.0], midpoints, [1.0]))

        for i in range(k):
            low, high = boundaries[i], boundaries[i + 1]
            num, _ = quad(lambda x: x * independent_sphere_density_fp64(x, d), low, high, epsabs=1e-12)
            den, _ = quad(lambda x: independent_sphere_density_fp64(x, d), low, high, epsabs=1e-12)
            expected_centroid = num / den
            assert math.isclose(cb[i], expected_centroid, rel_tol=1e-4, abs_tol=1e-5)


class TestNearestCodeIndices:
    """Validates index assignment and exact FP64 midpoint tie-breaking convention."""

    def test_exact_midpoint_tie_breaking_convention(self) -> None:
        """Contract: exact midpoint tie resolves to the LOWER centroid.
        Midpoints MUST be calculated in FP64 from the actual centroid values.
        """
        # Define centroids where midpoint has exact representation in FP64
        codebook = np.array([-0.5, 0.5], dtype=np.float32)
        # Midpoint is exactly 0.0 in FP64
        exact_tie = np.array([0.0], dtype=np.float32)
        idx_tie = nearest_code_indices(exact_tie, codebook)
        assert idx_tie[0] == 0, "Exact midpoint tie must resolve to lower index (0)"

        # Epsilon above midpoint must resolve to index 1
        above_tie = np.array([1e-7], dtype=np.float32)
        assert nearest_code_indices(above_tie, codebook)[0] == 1

        # Epsilon below midpoint must resolve to index 0
        below_tie = np.array([-1e-7], dtype=np.float32)
        assert nearest_code_indices(below_tie, codebook)[0] == 0

    def test_fp64_midpoint_precision_prevents_false_ties(self) -> None:
        """Ensures rounded decimal or FP32 midpoint rounding does not distort boundary."""
        codebook = lloyd_max_codebook(128, 2)  # 4 centroids
        cb_f64 = codebook.astype(np.float64)
        midpoint_12 = (cb_f64[1] + cb_f64[2]) / 2.0  # Around 0.0 by symmetry

        val = np.array([midpoint_12], dtype=np.float32)
        idx = nearest_code_indices(val, codebook)
        assert idx[0] == 1, "Midpoint between c1 and c2 must resolve to lower centroid c1"

    def test_clipping_outside_codebook_extrema(self) -> None:
        codebook = np.array([-0.4, -0.1, 0.1, 0.4], dtype=np.float32)
        extrema = np.array([-10.0, -0.5, 0.5, 10.0], dtype=np.float32)
        indices = nearest_code_indices(extrema, codebook)
        np.testing.assert_array_equal(indices, np.array([0, 0, 3, 3], dtype=np.uint8))
