"""Tests for Task 1: Seeding, Study Seed, and Canonical Rotations."""

from __future__ import annotations

import hashlib
import numpy as np
import pytest

from hamutay.turboquant import (
    STUDY_SEED_HEX,
    derive_seed,
    rng_for,
    canonical_qr,
    gaussian_rotation,
)


def _independent_seed_oracle(*fields: str | int, study_seed_hex: str = STUDY_SEED_HEX) -> int:
    """Independent oracle computing the sub-seed wire format."""
    serialized_fields = [str(f) for f in fields]
    token = "|".join([study_seed_hex] + serialized_fields)
    hasher = hashlib.sha256(token.encode("utf-8"))
    raw_digest = hasher.digest()
    return int.from_bytes(raw_digest[:16], byteorder="big", signed=False)


def test_study_seed_constant_value() -> None:
    """Verify the study seed hex matches the immutable contract."""
    assert STUDY_SEED_HEX == "0b311d5d4eceaf773efde389305a1b5a"
    assert isinstance(STUDY_SEED_HEX, str)
    assert len(STUDY_SEED_HEX) == 32


def test_derive_seed_wire_format_against_oracle() -> None:
    """Verify derive_seed matches independent SHA-256 big-endian uint128 oracle."""
    test_cases = [
        ("model_rev", 0, "K", 0, "purpose"),
        ("corpus_pages",),
        ("layer", 31, "head", 7),
        (12345, 67890),
        ("",),
    ]
    for fields in test_cases:
        expected = _independent_seed_oracle(*fields)
        observed = derive_seed(*fields)
        assert observed == expected, f"Failed for fields={fields}: {observed} != {expected}"
        assert 0 <= observed < (1 << 128)


def test_derive_seed_custom_study_seed() -> None:
    """Verify derive_seed respects an explicitly passed study_seed_hex."""
    custom_seed = "00112233445566778899aabbccddeeff"
    expected = _independent_seed_oracle("test", 1, study_seed_hex=custom_seed)
    observed = derive_seed("test", 1, study_seed_hex=custom_seed)
    assert observed == expected


def test_rng_for_reproducibility_and_isolation() -> None:
    """Verify rng_for returns independent reproducible numpy Generators."""
    rng1 = rng_for("test_stream", 1)
    rng2 = rng_for("test_stream", 1)
    rng3 = rng_for("test_stream", 2)

    draw1 = rng1.standard_normal(100)
    draw2 = rng2.standard_normal(100)
    draw3 = rng3.standard_normal(100)

    assert np.array_equal(draw1, draw2), "Identical fields must produce identical streams"
    assert not np.array_equal(draw1, draw3), "Distinct fields must produce distinct streams"


def test_canonical_qr_properties() -> None:
    """Verify canonical_qr produces an orthogonal Q with nonnegative diagonal in R."""
    rng = np.random.default_rng(42)
    dim = 16

    for _ in range(5):
        matrix = rng.standard_normal((dim, dim), dtype=np.float64)
        q = canonical_qr(matrix)

        assert q.dtype == np.float64
        assert q.shape == (dim, dim)

        # Check orthogonality: Q^T Q == I
        identity = np.eye(dim, dtype=np.float64)
        assert np.allclose(q.T @ q, identity, atol=1e-14)
        assert np.allclose(q @ q.T, identity, atol=1e-14)

        # Reconstruct R = Q^T M and check diagonal non-negativity
        r = q.T @ matrix
        # Check upper triangularity
        lower_triangle = np.tril(r, k=-1)
        assert np.allclose(lower_triangle, 0.0, atol=1e-12)
        # Check diagonal elements >= 0
        diag_r = np.diag(r)
        assert np.all(diag_r >= -1e-15), f"Diagonal of R has negative values: {diag_r}"


def test_gaussian_rotation_properties() -> None:
    """Verify gaussian_rotation returns an FP32 orthogonal matrix generated from FP64 QR."""
    dim = 128
    rot1 = gaussian_rotation(dim, "layer", 0, "K", 0)
    rot2 = gaussian_rotation(dim, "layer", 0, "K", 0)
    rot_diff = gaussian_rotation(dim, "layer", 0, "V", 0)

    assert rot1.dtype == np.float32
    assert rot1.shape == (dim, dim)

    # Determinism
    assert np.array_equal(rot1, rot2), "gaussian_rotation must be deterministic for identical seeds"
    assert not np.array_equal(rot1, rot_diff), "Different roles must produce different rotations"

    # Orthogonality in FP32
    identity = np.eye(dim, dtype=np.float32)
    assert np.allclose(rot1 @ rot1.T, identity, atol=1e-6)
    assert np.allclose(rot1.T @ rot1, identity, atol=1e-6)
