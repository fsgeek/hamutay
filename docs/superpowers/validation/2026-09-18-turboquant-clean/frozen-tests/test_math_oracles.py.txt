import pytest
import numpy as np
import scipy.integrate
from hamutay.turboquant.seeding import derive_seed
from hamutay.turboquant.rotation import canonical_qr
from hamutay.turboquant.codebook import sphere_coordinate_density, lloyd_max_codebook
from hamutay.turboquant.qualification import analytic_codebook_distortion
from hamutay.turboquant.product import pack_signs, unpack_signs

def test_derive_seed_determinism():
    seed1 = derive_seed("test_field", 42)
    seed2 = derive_seed("test_field", 42)
    assert seed1 == seed2
    assert isinstance(seed1, int)
    seed3 = derive_seed("test_field", 43)
    assert seed1 != seed3

def test_sphere_coordinate_density_integration():
    dimension = 128
    result, error = scipy.integrate.quad(lambda x: sphere_coordinate_density(x, dimension), -1, 1)
    assert result == pytest.approx(1.0, abs=1e-5)

def test_analytic_codebook_distortion_frozen_values():
    frozen_targets = {
        1: 0.36088859,
        2: 0.11600007,
        3: 0.03396593,
        4: 0.00931479
    }
    dimension = 128
    for bits, target in frozen_targets.items():
        codebook = lloyd_max_codebook(dimension, bits)
        distortion = analytic_codebook_distortion(codebook, dimension)
        assert distortion == pytest.approx(target, rel=1e-5)

def test_pack_unpack_signs_general():
    sketch_dim = 128
    rng = np.random.default_rng(42)
    signs = rng.choice([-1, 1], size=sketch_dim).astype(np.int8)
    packed = pack_signs(signs)
    unpacked = unpack_signs(packed, sketch_dim)
    np.testing.assert_array_equal(unpacked, signs)

def test_canonical_qr_orthogonality():
    mat = np.random.default_rng(100).standard_normal((10, 10))
    q = canonical_qr(mat)
    np.testing.assert_allclose(q.T @ q, np.eye(10), atol=1e-7)
