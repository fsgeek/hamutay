import numpy as np
import pytest
import hashlib
from hamutay.turboquant.seeding import STUDY_SEED_HEX, derive_seed, rng_for
from hamutay.turboquant.rotation import canonical_qr, gaussian_rotation

def test_study_seed():
    assert STUDY_SEED_HEX == "0b311d5d4eceaf773efde389305a1b5a"

def test_derive_seed():
    s1 = derive_seed("layer", 1)
    assert isinstance(s1, int)
    
    # Requirement: SHA-256 over the UTF-8 string formed by joining the study seed and the given fields with `|`, taking the first 16 bytes as an unsigned big-endian integer.
    s = "0b311d5d4eceaf773efde389305a1b5a|test|123"
    h = hashlib.sha256(s.encode('utf-8')).digest()
    expected = int.from_bytes(h[:16], 'big')
    assert derive_seed("test", 123) == expected

def test_rng_for():
    rng1 = rng_for("test_stream")
    rng2 = rng_for("test_stream")
    assert rng1.random() == rng2.random()

def test_canonical_qr():
    A = np.random.randn(10, 10).astype(np.float64)
    Q_c = canonical_qr(A)
    assert Q_c.shape == (10, 10)
    assert Q_c.dtype == np.float64
    np.testing.assert_allclose(Q_c @ Q_c.T, np.eye(10), atol=1e-10)
    
    # Requirement: Diagonal of R must be non-negative
    R_c = Q_c.T @ A
    assert np.all(np.diag(R_c) >= 0), "Diagonal of R must be non-negative"

def test_gaussian_rotation():
    rot = gaussian_rotation(128, "rot")
    assert rot.shape == (128, 128)
    assert rot.dtype == np.float32
    np.testing.assert_allclose(rot @ rot.T, np.eye(128, dtype=np.float32), atol=1e-4)
