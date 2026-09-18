import hashlib
import numpy as np
import pytest
from scipy.special import gamma

from hamutay.turboquant.seeding import STUDY_SEED_HEX, derive_seed, rng_for
from hamutay.turboquant.rotation import canonical_qr, gaussian_rotation
from hamutay.turboquant.codebook import sphere_coordinate_density, lloyd_max_codebook, nearest_code_indices

def test_study_seed_constant():
    assert STUDY_SEED_HEX == "0b311d5d4eceaf773efde389305a1b5a"

def test_derive_seed_behavior():
    # Verify exact hashing formulation: SHA-256 over | joined fields, taking first 16 bytes
    joined = f"{STUDY_SEED_HEX}|layer|12|key".encode('utf-8')
    expected_hash = hashlib.sha256(joined).digest()
    expected_int = int.from_bytes(expected_hash[:16], byteorder='big', signed=False)
    
    assert derive_seed("layer", 12, "key") == expected_int
    assert derive_seed("layer", 12, "key", study_seed_hex=STUDY_SEED_HEX) == expected_int

def test_rng_for_determinism():
    rng_a1 = rng_for("A", 1)
    rng_a2 = rng_for("A", 1)
    rng_b = rng_for("B")
    
    assert isinstance(rng_a1, np.random.Generator)
    assert rng_a1.standard_normal() == rng_a2.standard_normal()
    assert rng_a1.standard_normal() != rng_b.standard_normal()

def test_canonical_qr_properties():
    rng = np.random.default_rng(42)
    matrix = rng.normal(size=(10, 10))
    q_canon = canonical_qr(matrix)
    
    # Check orthogonality
    np.testing.assert_allclose(q_canon.T @ q_canon, np.eye(10), atol=1e-10)
    
    # Check positive diagonal of R (R = Q.T @ matrix)
    r_canon = q_canon.T @ matrix
    diag_r = np.diag(r_canon)
    assert np.all(diag_r >= 0), "Diagonal of R must be non-negative"

def test_gaussian_rotation():
    dim = 128
    rot = gaussian_rotation(dim, "test")
    assert rot.shape == (dim, dim)
    assert rot.dtype == np.float32
    np.testing.assert_allclose(rot.astype(np.float64).T @ rot.astype(np.float64), np.eye(dim), atol=1e-5)

def test_sphere_coordinate_density():
    dim = 128
    x_vals = np.array([0.0, 0.5, 0.99])
    
    def oracle(x, d):
        coef = gamma(d/2) / (np.sqrt(np.pi) * gamma((d-1)/2))
        return coef * ((1 - x**2) ** ((d-3)/2))
    
    expected = oracle(x_vals, dim)
    actual = sphere_coordinate_density(x_vals, dim)
    np.testing.assert_allclose(actual, expected, atol=1e-10)

def test_lloyd_max_codebook():
    cb = lloyd_max_codebook(dimension=128, bits=1, tolerance=1e-5)
    assert cb.shape == (2,)
    assert cb.dtype == np.float32
    # 1-bit codebook must be perfectly symmetric
    np.testing.assert_allclose(cb[0], -cb[1], atol=1e-4)

def test_nearest_code_indices():
    cb = np.array([-0.5, 0.5], dtype=np.float32)
    vals = np.array([-0.8, 0.0, 0.6], dtype=np.float32)
    # 0.0 is an exact midpoint, resolves to lower centroid (index 0)
    expected = np.array([0, 0, 1], dtype=np.uint8)
    actual = nearest_code_indices(vals, cb)
    np.testing.assert_array_equal(actual, expected)
