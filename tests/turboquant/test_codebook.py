import numpy as np
from scipy.integrate import quad

from hamutay.turboquant.codebook import (
    lloyd_max_codebook,
    nearest_code_indices,
    sphere_coordinate_density,
)


def test_sphere_coordinate_density_integrates_to_one():
    integral, _ = quad(lambda x: sphere_coordinate_density(x, 128), -1.0, 1.0)
    assert abs(integral - 1.0) < 1e-11


def test_one_bit_centroids_match_closed_form_scale():
    codebook = lloyd_max_codebook(128, 1)
    expected = np.sqrt(2.0 / (np.pi * 128.0))
    np.testing.assert_allclose(codebook, [-expected, expected], rtol=0.025)


def test_codebooks_are_symmetric_ordered_and_repeatable():
    first = lloyd_max_codebook(128, 4)
    second = lloyd_max_codebook(128, 4)
    assert first.dtype == np.float32
    assert np.array_equal(first, second)
    assert np.all(np.diff(first) > 0)
    np.testing.assert_allclose(first, -first[::-1], atol=2e-7)


def test_nearest_index_ties_choose_lower_centroid():
    codebook = np.array([-1.0, 1.0], dtype=np.float32)
    indices = nearest_code_indices(np.array([-0.1, 0.0, 0.1], np.float32), codebook)
    np.testing.assert_array_equal(indices, [0, 0, 1])


def test_nearest_index_large_centroids_avoid_overflow_and_tie_left():
    codebook = np.array([2.5e38, 3.0e38], dtype=np.float32)
    values = np.array([2.6e38, 2.75e38, 2.8e38, 2.9e38], dtype=np.float32)

    indices = nearest_code_indices(values, codebook)

    np.testing.assert_array_equal(indices, [0, 0, 1, 1])


def _scaled_scalar_distortion(dimension: int, bits: int) -> float:
    codebook = lloyd_max_codebook(dimension, bits)
    boundaries = np.concatenate(
        (
            [-1.0],
            (codebook[:-1].astype(np.float64) + codebook[1:].astype(np.float64)) / 2.0,
            [1.0],
        )
    )
    distortion = sum(
        quad(
            lambda x, centroid=float(centroid): (x - centroid) ** 2
            * sphere_coordinate_density(x, dimension),
            lower,
            upper,
            epsabs=1e-14,
            epsrel=1e-13,
            limit=200,
        )[0]
        for centroid, lower, upper in zip(codebook, boundaries[:-1], boundaries[1:], strict=True)
    )
    return dimension * distortion


def test_multilevel_codebooks_match_published_spherical_distortion_scale():
    distortions = np.array([_scaled_scalar_distortion(128, bits) for bits in range(1, 5)])

    np.testing.assert_allclose(
        distortions,
        [0.36088859, 0.11600007, 0.03396593, 0.00931479],
        rtol=2e-6,
        atol=2e-8,
    )
