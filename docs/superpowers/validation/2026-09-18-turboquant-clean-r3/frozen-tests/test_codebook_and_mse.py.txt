"""Tests for Task 2 (Spherical Lloyd-Max Codebooks) & Task 3 (Algorithm 1 MSE Quantizer)."""

from __future__ import annotations

import math
import numpy as np
import pytest
from scipy import integrate

from hamutay.turboquant import (
    sphere_coordinate_density,
    lloyd_max_codebook,
    nearest_code_indices,
    MSECodes,
    MSEQuantizer,
    gaussian_rotation,
)


def _independent_density_oracle(x: float, dimension: int) -> float:
    """Analytic oracle for Lemma 1 sphere coordinate density."""
    if abs(x) >= 1.0:
        return 0.0
    d = float(dimension)
    log_c = (
        math.lgamma(d / 2.0)
        - 0.5 * math.log(math.pi)
        - math.lgamma((d - 1.0) / 2.0)
    )
    c = math.exp(log_c)
    return c * ((1.0 - x * x) ** ((d - 3.0) / 2.0))


def test_sphere_coordinate_density_against_analytic_oracle() -> None:
    """Verify sphere_coordinate_density matches independent density formula and integrates to 1."""
    d = 128
    test_points = [-0.9, -0.5, -0.1, 0.0, 0.05, 0.3, 0.8]

    for pt in test_points:
        expected = _independent_density_oracle(pt, d)
        observed = sphere_coordinate_density(pt, d)
        assert abs(observed - expected) < 1e-12, f"Density mismatch at x={pt}"

    # Verify symmetry
    assert sphere_coordinate_density(0.25, d) == sphere_coordinate_density(-0.25, d)

    # Numerical integration to verify unit probability mass
    integral, _ = integrate.quad(lambda x: sphere_coordinate_density(x, d), -1.0, 1.0)
    assert abs(integral - 1.0) < 1e-7


def test_lloyd_max_codebook_structure_and_symmetry() -> None:
    """Verify codebook construction shape, dtype, monotonicity, and anti-symmetry."""
    d = 128
    for bits in [1, 2, 3, 4]:
        codebook = lloyd_max_codebook(d, bits)
        assert codebook.dtype == np.float32
        assert codebook.shape == (2**bits,)

        # Monotonically increasing
        assert np.all(np.diff(codebook) > 0), f"Codebook for {bits} bits is not strictly increasing"

        # Centroids within [-1, 1]
        assert -1.0 <= codebook[0] and codebook[-1] <= 1.0

        # Exact anti-symmetry c_i == -c_{2^b - 1 - i}
        assert np.allclose(codebook, -codebook[::-1], atol=1e-6)


def test_lloyd_max_codebook_1bit_closed_form() -> None:
    """Verify 1-bit codebook at d=128 matches asymptotic centroid ±sqrt(2 / (pi * d))."""
    d = 128
    codebook = lloyd_max_codebook(d, 1)
    asymptotic_val = math.sqrt(2.0 / (math.pi * d))
    # Codebook should be within 1% of asymptotic normal value for d=128
    assert abs(codebook[1] - asymptotic_val) / asymptotic_val < 0.01
    assert abs(codebook[0] - (-asymptotic_val)) / asymptotic_val < 0.01


def test_nearest_code_indices_exact_midpoint_tie_breaking() -> None:
    """Verify nearest_code_indices breaks exact midpoint ties strictly to the LOWER centroid."""
    codebook = np.array([-0.8, -0.2, 0.2, 0.8], dtype=np.float32)

    # Exact midpoints between consecutive centroids
    midpoints = (codebook[:-1] + codebook[1:]) / 2.0  # [-0.5, 0.0, 0.5]
    indices = nearest_code_indices(midpoints, codebook)

    # Must resolve to lower centroid indices: 0, 1, 2
    assert np.array_equal(indices, np.array([0, 1, 2], dtype=np.uint8))

    # Points infinitesimally above midpoint must resolve to higher centroid
    above_midpoints = midpoints + 1e-6
    indices_above = nearest_code_indices(above_midpoints, codebook)
    assert np.array_equal(indices_above, np.array([1, 2, 3], dtype=np.uint8))

    # Points infinitesimally below midpoint must resolve to lower centroid
    below_midpoints = midpoints - 1e-6
    indices_below = nearest_code_indices(below_midpoints, codebook)
    assert np.array_equal(indices_below, np.array([0, 1, 2], dtype=np.uint8))


def test_mse_codes_slotted_frozen_structure() -> None:
    """Verify MSECodes is a frozen slotted dataclass with declared types."""
    indices = np.zeros((4, 128), dtype=np.uint8)
    norms = np.ones((4,), dtype=np.float32)
    codes = MSECodes(indices=indices, norms=norms)

    assert hasattr(MSECodes, "__slots__")
    with pytest.raises((AttributeError, TypeError)):
        codes.indices = np.ones_like(indices)  # Frozen mutation refusal

    with pytest.raises((AttributeError, TypeError)):
        codes.arbitrary_attribute = 42  # Slotted refusal


def test_mse_quantizer_zero_vector_contract() -> None:
    """Verify zero vector quantizes to zero norm, zero indices, and exact zero reconstruction."""
    d = 128
    rot = gaussian_rotation(d, "test_rot")
    cb = lloyd_max_codebook(d, 2)
    quantizer = MSEQuantizer(rotation=rot, codebook=cb)

    zero_vecs = np.zeros((5, d), dtype=np.float32)
    codes = quantizer.quantize(zero_vecs)

    assert np.all(codes.norms == 0.0)
    assert np.all(codes.indices == 0)
    assert codes.indices.dtype == np.uint8

    reconstructed = quantizer.dequantize(codes)
    assert reconstructed.shape == zero_vecs.shape
    assert reconstructed.dtype == np.float32
    assert np.array_equal(reconstructed, np.zeros_like(zero_vecs))


def test_mse_quantizer_scale_invariance_and_norms() -> None:
    """Verify quantization norm tracks vector scaling while code indices remain invariant."""
    d = 128
    rot = gaussian_rotation(d, "test_rot_scale")
    cb = lloyd_max_codebook(d, 2)
    quantizer = MSEQuantizer(rotation=rot, codebook=cb)

    rng = np.random.default_rng(123)
    base_vec = rng.standard_normal((3, d)).astype(np.float32)
    scaled_vec = base_vec * 7.5

    codes_base = quantizer.quantize(base_vec)
    codes_scaled = quantizer.quantize(scaled_vec)

    assert np.array_equal(codes_base.indices, codes_scaled.indices)
    assert np.allclose(codes_scaled.norms, codes_base.norms * 7.5, rtol=1e-6)


def test_mse_quantizer_batch_shapes() -> None:
    """Verify MSEQuantizer handles arbitrary multi-dimensional leading batch shapes."""
    d = 128
    rot = gaussian_rotation(d, "test_rot_batch")
    cb = lloyd_max_codebook(d, 2)
    quantizer = MSEQuantizer(rotation=rot, codebook=cb)

    # 4D tensor e.g., (batch, heads, seq, dim)
    shape = (2, 4, 16, d)
    data = np.random.randn(*shape).astype(np.float32)

    codes = quantizer.quantize(data)
    assert codes.indices.shape == shape
    assert codes.norms.shape == shape[:-1]

    recon = quantizer.dequantize(codes)
    assert recon.shape == shape
    assert recon.dtype == np.float32
