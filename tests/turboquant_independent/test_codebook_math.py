"""Independent tests of the frozen Lloyd-Max codebooks (paper Algorithm 1 setup).

The central check is a genuine cross-validation: the analytic FP64 distortion
of the *implementation's own* codebook, computed by quadrature written here,
against the empirically measured distortion of the implementation's quantizer
on random Gaussian vectors, and against the paper's published table.

A codebook that is merely self-consistent (analytic == empirical) but wrong
fails the paper comparison; a codebook that hits the paper table by hard-coding
fails the analytic comparison against its own centroids.
"""

from __future__ import annotations

import numpy as np
import pytest
from scipy.integrate import quad

from hamutay.turboquant.codebook import (
    lloyd_max_codebook,
    nearest_code_indices,
    sphere_coordinate_density,
)

from .conftest import (
    ANALYTIC_MSE_DISTORTION,
    PAPER_MSE_DISTORTION,
    REGISTERED_DIMENSION,
    reference_analytic_distortion,
    reference_cell_boundaries,
    reference_sphere_density,
)


class TestSphereCoordinateDensity:
    def test_density_matches_independent_lemma_1_implementation(self):
        grid = np.linspace(-0.999, 0.999, 401)
        observed = np.asarray(
            [float(sphere_coordinate_density(float(x), REGISTERED_DIMENSION))
             for x in grid]
        )
        expected = reference_sphere_density(grid, REGISTERED_DIMENSION)
        np.testing.assert_allclose(observed, expected, rtol=1e-10, atol=1e-12)

    @pytest.mark.parametrize("dimension", [3, 8, 128])
    def test_density_integrates_to_one(self, dimension):
        integral, _ = quad(
            lambda x: float(sphere_coordinate_density(float(x), dimension)),
            -1.0,
            1.0,
            epsabs=1e-14,
            epsrel=1e-13,
            limit=200,
        )
        assert abs(integral - 1.0) < 1e-10

    def test_density_is_symmetric_and_vanishes_outside_the_ball(self):
        for x in (0.1, 0.5, 0.9):
            left = float(sphere_coordinate_density(-x, REGISTERED_DIMENSION))
            right = float(sphere_coordinate_density(x, REGISTERED_DIMENSION))
            assert abs(left - right) < 1e-12
        for outside in (-1.5, -1.0000001, 1.0000001, 2.0):
            assert float(
                sphere_coordinate_density(outside, REGISTERED_DIMENSION)
            ) == 0.0

    def test_density_second_moment_is_one_over_dimension(self):
        """A rotated unit vector has coordinate variance 1/d; catches a bad constant."""
        moment, _ = quad(
            lambda x: x * x * float(
                sphere_coordinate_density(float(x), REGISTERED_DIMENSION)
            ),
            -1.0,
            1.0,
            epsabs=1e-14,
            epsrel=1e-13,
            limit=200,
        )
        assert abs(moment - 1.0 / REGISTERED_DIMENSION) < 1e-12

    def test_density_is_not_the_gaussian_limit(self):
        """The paper uses the exact Beta density, not its N(0, 1/d) limit."""
        low_dimension = 4
        exact = float(sphere_coordinate_density(0.9, low_dimension))
        gaussian = np.sqrt(low_dimension / (2 * np.pi)) * np.exp(
            -low_dimension * 0.81 / 2
        )
        assert abs(exact - gaussian) > 1e-3


class TestCodebookStructure:
    @pytest.mark.parametrize("bits", [1, 2, 3, 4])
    def test_codebook_shape_dtype_and_ordering(self, bits):
        codebook = lloyd_max_codebook(REGISTERED_DIMENSION, bits)
        assert codebook.dtype == np.float32
        assert codebook.shape == (2**bits,)
        assert np.all(np.diff(codebook) > 0)
        assert np.all(np.abs(codebook) < 1.0)

    @pytest.mark.parametrize("bits", [1, 2, 3, 4])
    def test_codebook_is_symmetric_about_zero(self, bits):
        codebook = lloyd_max_codebook(REGISTERED_DIMENSION, bits)
        np.testing.assert_allclose(codebook, -codebook[::-1], atol=2e-7)

    def test_zero_bit_codebook_is_the_single_zero_centroid(self):
        """Required by the b-1 bit convention: a 1-bit product quantizer."""
        codebook = lloyd_max_codebook(REGISTERED_DIMENSION, 0)
        assert codebook.shape == (1,)
        assert float(codebook[0]) == 0.0

    def test_codebook_is_deterministic(self):
        first = lloyd_max_codebook(REGISTERED_DIMENSION, 4)
        second = lloyd_max_codebook(REGISTERED_DIMENSION, 4)
        np.testing.assert_array_equal(first, second)

    def test_one_bit_centroid_matches_conditional_mean(self):
        """Centroid must be E[x | x > 0] under the exact density, not the
        Gaussian closed form sqrt(2/(pi*d)), which differs in the 3rd digit."""
        codebook = lloyd_max_codebook(REGISTERED_DIMENSION, 1)
        mass, _ = quad(
            lambda x: reference_sphere_density(np.float64(x), REGISTERED_DIMENSION),
            0.0,
            1.0,
            epsabs=1e-14,
            epsrel=1e-13,
            limit=200,
        )
        moment, _ = quad(
            lambda x: x
            * reference_sphere_density(np.float64(x), REGISTERED_DIMENSION),
            0.0,
            1.0,
            epsabs=1e-14,
            epsrel=1e-13,
            limit=200,
        )
        expected = moment / mass
        assert abs(float(codebook[1]) - expected) < 1e-6
        assert abs(float(codebook[0]) + expected) < 1e-6

    @pytest.mark.parametrize("bits", [1, 2, 3, 4])
    def test_centroids_are_lloyd_max_stationary(self, bits):
        """Each centroid equals the conditional mean of its own cell.

        This is the defining fixed-point condition. A codebook built from
        equal-probability quantiles (a plausible shortcut) fails it.
        """
        codebook = lloyd_max_codebook(REGISTERED_DIMENSION, bits).astype(np.float64)
        boundaries = reference_cell_boundaries(codebook)
        for index, centroid in enumerate(codebook):
            low, high = boundaries[index], boundaries[index + 1]
            mass, _ = quad(
                lambda x: reference_sphere_density(
                    np.float64(x), REGISTERED_DIMENSION
                ),
                low,
                high,
                epsabs=1e-14,
                epsrel=1e-13,
                limit=200,
            )
            moment, _ = quad(
                lambda x: x
                * reference_sphere_density(np.float64(x), REGISTERED_DIMENSION),
                low,
                high,
                epsabs=1e-14,
                epsrel=1e-13,
                limit=200,
            )
            assert mass > 0.0
            assert abs(centroid - moment / mass) < 1e-6


class TestAnalyticDistortion:
    @pytest.mark.parametrize("bits", [1, 2, 3, 4])
    def test_analytic_distortion_matches_registered_reference(self, bits):
        """Quadrature over the implementation's own codebook must reproduce the
        pre-registered FP64 values from the specification."""
        codebook = lloyd_max_codebook(REGISTERED_DIMENSION, bits)
        observed = reference_analytic_distortion(codebook, REGISTERED_DIMENSION)
        expected = ANALYTIC_MSE_DISTORTION[bits]
        assert abs(observed - expected) / expected < 5e-6

    @pytest.mark.parametrize("bits", [1, 2, 3, 4])
    def test_analytic_distortion_is_within_paper_tolerance(self, bits):
        codebook = lloyd_max_codebook(REGISTERED_DIMENSION, bits)
        observed = reference_analytic_distortion(codebook, REGISTERED_DIMENSION)
        paper = PAPER_MSE_DISTORTION[bits]
        assert abs(observed - paper) / paper <= 0.15

    def test_distortion_decreases_with_bit_width(self):
        values = [
            reference_analytic_distortion(
                lloyd_max_codebook(REGISTERED_DIMENSION, bits), REGISTERED_DIMENSION
            )
            for bits in (1, 2, 3, 4)
        ]
        assert values == sorted(values, reverse=True)

    @pytest.mark.parametrize("bits", [1, 2, 3])
    def test_empirical_distortion_agrees_with_analytic_value(self, bits):
        """Cross-validation: quantize real random vectors and compare the
        measured normalized MSE with the analytic prediction.

        Uses the implementation's codebook and index assignment, with the
        rotation replaced by an exact identity so this test isolates the
        scalar quantizer. Vectors are drawn on the sphere, so their rotated
        coordinates follow the registered density by construction.
        """
        codebook = lloyd_max_codebook(REGISTERED_DIMENSION, bits)
        rng = np.random.default_rng(20260827 + bits)
        sample_count = 20000
        raw = rng.standard_normal((sample_count, REGISTERED_DIMENSION))
        unit = raw / np.linalg.norm(raw, axis=-1, keepdims=True)

        indices = nearest_code_indices(unit.astype(np.float32), codebook)
        reconstructed = codebook[indices].astype(np.float64)

        # For a unit-norm vector the per-vector squared error already sums
        # over all d coordinates, so it is the normalized distortion directly;
        # the analytic value carries its own factor of d for the same reason.
        squared_error = np.sum((reconstructed - unit) ** 2, axis=-1)
        empirical = float(np.mean(squared_error))

        analytic = reference_analytic_distortion(codebook, REGISTERED_DIMENSION)
        standard_error = float(np.std(squared_error)) / np.sqrt(sample_count)
        assert abs(empirical - analytic) < max(6.0 * standard_error, 0.005 * analytic)


class TestNearestCodeIndices:
    def test_indices_are_uint8_and_within_range(self):
        codebook = lloyd_max_codebook(REGISTERED_DIMENSION, 4)
        rng = np.random.default_rng(3)
        values = rng.standard_normal((7, REGISTERED_DIMENSION)).astype(np.float32)
        indices = nearest_code_indices(values, codebook)
        assert indices.dtype == np.uint8
        assert indices.shape == values.shape
        assert int(indices.max()) < codebook.size

    def test_assignment_is_truly_nearest(self):
        """Compare against a brute-force argmin over all centroids."""
        codebook = lloyd_max_codebook(REGISTERED_DIMENSION, 3)
        rng = np.random.default_rng(4)
        values = (rng.standard_normal((200, 16)) * 0.1).astype(np.float32)
        indices = nearest_code_indices(values, codebook)
        distances = np.abs(
            values.astype(np.float64)[..., None] - codebook.astype(np.float64)
        )
        expected = np.argmin(distances, axis=-1)
        np.testing.assert_array_equal(indices.astype(np.int64), expected)

    def test_exact_midpoint_tie_selects_the_lower_centroid(self):
        """Spec pins 'side=left' semantics; the opposite choice is a silent
        one-index shift that changes packed codes and stream hashes."""
        codebook = np.array([-1.0, 1.0], dtype=np.float32)
        indices = nearest_code_indices(
            np.array([-0.1, 0.0, 0.1], dtype=np.float32), codebook
        )
        np.testing.assert_array_equal(indices, [0, 0, 1])

    def test_values_beyond_the_codebook_clamp_to_the_extremes(self):
        codebook = lloyd_max_codebook(REGISTERED_DIMENSION, 2)
        indices = nearest_code_indices(
            np.array([-50.0, 50.0], dtype=np.float32), codebook
        )
        assert int(indices[0]) == 0
        assert int(indices[1]) == codebook.size - 1

    def test_non_monotonic_codebook_is_rejected(self):
        bad = np.array([1.0, -1.0], dtype=np.float32)
        with pytest.raises(ValueError):
            nearest_code_indices(np.array([0.0], dtype=np.float32), bad)
