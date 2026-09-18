import numpy as np
import pytest
from hamutay.turboquant.codebook import (
    sphere_coordinate_density,
    lloyd_max_codebook,
    nearest_code_indices
)

def test_sphere_coordinate_density():
    d = sphere_coordinate_density(0.5, 128)
    assert isinstance(d, float)
    assert d > 0.0

def test_sphere_coordinate_density_array():
    arr = np.array([-0.5, 0.5])
    d = sphere_coordinate_density(arr, 128)
    assert isinstance(d, np.ndarray)
    assert d.shape == (2,)

def test_lloyd_max_codebook():
    cb = lloyd_max_codebook(128, 1)
    assert cb.shape == (2,)
    assert cb.dtype == np.float32
    assert cb[0] < cb[1]

def test_nearest_code_indices_validation():
    # empty
    with pytest.raises(Exception):
        nearest_code_indices(np.array([0.0], dtype=np.float32), np.array([], dtype=np.float32))
    # 2D
    with pytest.raises(Exception):
        nearest_code_indices(np.array([0.0], dtype=np.float32), np.array([[-1.0, 1.0]], dtype=np.float32))
    # not strictly increasing
    with pytest.raises(Exception):
        nearest_code_indices(np.array([0.0], dtype=np.float32), np.array([1.0, -1.0], dtype=np.float32))
    # >256 centroids
    with pytest.raises(Exception):
        nearest_code_indices(np.array([0.0], dtype=np.float32), np.arange(257, dtype=np.float32))

def test_nearest_code_indices_midpoint_tiebreaker():
    cb = np.array([-1.0, 1.0], dtype=np.float32)
    vals = np.array([-0.5, 0.0, 0.5], dtype=np.float32)
    
    # Midpoints calculated in FP64, tie resolves to lower centroid
    idx = nearest_code_indices(vals, cb)
    assert idx.dtype == np.uint8
    np.testing.assert_array_equal(idx, np.array([0, 0, 1], dtype=np.uint8))
