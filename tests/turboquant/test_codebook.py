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
