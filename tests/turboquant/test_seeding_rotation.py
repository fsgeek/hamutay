import hashlib

import numpy as np

from hamutay.turboquant.rotation import canonical_qr, gaussian_rotation
from hamutay.turboquant.seeding import STUDY_SEED_HEX, derive_seed


def test_derive_seed_uses_registered_wire_format():
    fields = (
        "0e9e39f249a16976918f6564b8830bc894c89659",
        "tq_prod",
        7,
        "k",
        3,
        "projection",
    )
    wire = "|".join((STUDY_SEED_HEX, *(str(field) for field in fields)))
    expected = int.from_bytes(hashlib.sha256(wire.encode()).digest()[:16], "big")
    assert derive_seed(*fields) == expected


def test_canonical_qr_has_nonnegative_diagonal_and_is_orthogonal():
    matrix = np.array([[1.0, 2.0], [3.0, 4.0]], dtype=np.float64)
    rotation = canonical_qr(matrix)
    signed_r = rotation.T @ matrix
    np.testing.assert_allclose(rotation.T @ rotation, np.eye(2), atol=1e-14)
    assert np.all(np.diag(signed_r) >= 0.0)


def test_gaussian_rotation_is_repeatable_fp32():
    first = gaussian_rotation(128, "algorithm_1", 0, "v", 0, "rotation")
    second = gaussian_rotation(128, "algorithm_1", 0, "v", 0, "rotation")
    assert first.dtype == np.float32
    assert np.array_equal(first, second)
    np.testing.assert_allclose(first @ first.T, np.eye(128), atol=2e-5)
