"""Independent tests for the conventions the design specification pins.

These target the exact places where a plausible implementation goes wrong:
seed wire format (padding, separator, truncation, endianness), the QR sign
fix (which sign convention, and what happens at an exact zero pivot), bit
packing endianness, and the zero-sign rule.
"""

from __future__ import annotations

import hashlib

import numpy as np
import pytest

from hamutay.turboquant.rotation import canonical_qr, gaussian_rotation
from hamutay.turboquant.seeding import STUDY_SEED_HEX, derive_seed, rng_for

from .conftest import (
    MODEL_REVISION,
    REGISTERED_DIMENSION,
    reference_derive_seed,
)


class TestStudySeed:
    def test_study_seed_is_the_registered_128_bit_value(self):
        """The spec fixes this exact seed; a typo silently rerandomizes the study."""
        assert STUDY_SEED_HEX == "0b311d5d4eceaf773efde389305a1b5a"
        assert len(STUDY_SEED_HEX) == 32
        assert STUDY_SEED_HEX == STUDY_SEED_HEX.lower()
        int(STUDY_SEED_HEX, 16)

    def test_derive_seed_matches_independent_wire_format(self):
        fields = (MODEL_REVISION, "tq_prod", 7, "k", 3, "projection")
        assert derive_seed(*fields) == reference_derive_seed(*fields)

    def test_derive_seed_is_big_endian_over_first_sixteen_bytes(self):
        """Little-endian or a full 32-byte read both produce a different stream."""
        fields = ("algorithm_1", 0, "v", 0, "rotation")
        wire = "|".join((STUDY_SEED_HEX, *(str(f) for f in fields)))
        digest = hashlib.sha256(wire.encode("utf-8")).digest()
        observed = derive_seed(*fields)

        assert observed == int.from_bytes(digest[:16], "big")
        assert observed != int.from_bytes(digest[:16], "little")
        assert observed != int.from_bytes(digest, "big")
        assert observed < 2**128

    def test_integer_fields_are_unpadded_base_ten(self):
        """Zero-padding a layer index would change every derived object."""
        assert derive_seed("layer", 7) == reference_derive_seed("layer", "7")
        assert derive_seed("layer", 7) != reference_derive_seed("layer", "07")
        assert derive_seed("layer", 10) != reference_derive_seed("layer", "010")

    def test_field_separator_is_unambiguous(self):
        """'a|b' as one field must not collide with ('a', 'b') as two."""
        with pytest.raises(ValueError):
            derive_seed("a|b")

    def test_distinct_purposes_give_distinct_streams(self):
        """Rotation and projection for the same layer must not share a stream."""
        rotation_seed = derive_seed("algorithm_1", 0, "k", 0, "rotation")
        projection_seed = derive_seed("algorithm_1", 0, "k", 0, "projection")
        assert rotation_seed != projection_seed

        first = rng_for("algorithm_1", 0, "k", 0, "rotation").standard_normal(64)
        second = rng_for("algorithm_1", 0, "k", 0, "projection").standard_normal(64)
        assert not np.allclose(first, second)

    def test_rng_for_is_a_fresh_generator_each_call(self):
        """A cached module-global generator would make draws order-dependent."""
        first = rng_for("purpose", 1).standard_normal(16)
        second = rng_for("purpose", 1).standard_normal(16)
        np.testing.assert_array_equal(first, second)

    def test_invalid_study_seed_is_rejected(self):
        for bad in ("0X" + STUDY_SEED_HEX[2:], STUDY_SEED_HEX.upper(), "abc", ""):
            with pytest.raises(ValueError):
                derive_seed("x", study_seed_hex=bad)


class TestCanonicalQR:
    def test_diagonal_of_r_is_nonnegative_and_factor_is_orthogonal(self):
        rng = np.random.default_rng(11)
        for size in (2, 5, 16):
            matrix = rng.standard_normal((size, size))
            q = canonical_qr(matrix)
            r = q.T @ matrix
            np.testing.assert_allclose(q.T @ q, np.eye(size), atol=1e-12)
            assert np.all(np.diag(r) >= -1e-15)
            np.testing.assert_allclose(q @ r, matrix, atol=1e-10)

    def test_sign_fix_actually_flips_a_negative_pivot(self):
        """A no-op 'canonicalization' passes an orthogonality test but not this."""
        matrix = np.array([[-1.0, 0.0], [0.0, -1.0]], dtype=np.float64)
        q = canonical_qr(matrix)
        r = q.T @ matrix
        assert np.all(np.diag(r) >= 0.0)
        np.testing.assert_allclose(np.abs(q), np.eye(2), atol=1e-12)

    def test_zero_pivot_is_assigned_positive_sign(self):
        """Spec: 'with zero assigned sign +1'. np.sign(0) == 0 would zero a column."""
        matrix = np.array([[0.0, 1.0], [0.0, 0.0]], dtype=np.float64)
        q = canonical_qr(matrix)
        np.testing.assert_allclose(q.T @ q, np.eye(2), atol=1e-12)
        assert np.all(np.linalg.norm(q, axis=0) > 0.5)
        assert abs(abs(np.linalg.det(q)) - 1.0) < 1e-12

    def test_canonical_qr_is_deterministic_for_fixed_input(self):
        matrix = np.arange(1.0, 17.0).reshape(4, 4)
        np.testing.assert_array_equal(canonical_qr(matrix), canonical_qr(matrix))


class TestGaussianRotation:
    def test_registered_rotation_is_orthogonal_in_fp32(self):
        rotation = gaussian_rotation(
            REGISTERED_DIMENSION, "algorithm_1", 0, "v", 0, "rotation"
        )
        assert rotation.dtype == np.float32
        assert rotation.shape == (REGISTERED_DIMENSION, REGISTERED_DIMENSION)
        identity = np.eye(REGISTERED_DIMENSION)
        np.testing.assert_allclose(
            rotation.astype(np.float64) @ rotation.astype(np.float64).T,
            identity,
            atol=2e-5,
        )
        np.testing.assert_allclose(
            rotation.astype(np.float64).T @ rotation.astype(np.float64),
            identity,
            atol=2e-5,
        )

    def test_rotation_preserves_vector_norm(self):
        """The property the quantizer actually depends on."""
        rotation = gaussian_rotation(64, "algorithm_1", 1, "k", 2, "rotation").astype(
            np.float64
        )
        rng = np.random.default_rng(5)
        vectors = rng.standard_normal((32, 64))
        rotated = vectors @ rotation.T
        np.testing.assert_allclose(
            np.linalg.norm(rotated, axis=-1),
            np.linalg.norm(vectors, axis=-1),
            rtol=1e-5,
        )

    def test_rotation_is_reproducible_and_seed_field_sensitive(self):
        base = gaussian_rotation(32, "algorithm_1", 0, "k", 0, "rotation")
        np.testing.assert_array_equal(
            base, gaussian_rotation(32, "algorithm_1", 0, "k", 0, "rotation")
        )
        for changed in (
            ("algorithm_1", 1, "k", 0, "rotation"),
            ("algorithm_1", 0, "v", 0, "rotation"),
            ("algorithm_1", 0, "k", 1, "rotation"),
            ("algorithm_2", 0, "k", 0, "rotation"),
        ):
            assert not np.array_equal(base, gaussian_rotation(32, *changed))

    def test_rotation_is_not_a_trivial_or_permutation_matrix(self):
        """Catches a stub that returns an identity-like matrix."""
        rotation = gaussian_rotation(
            REGISTERED_DIMENSION, "algorithm_1", 0, "k", 0, "rotation"
        )
        assert not np.allclose(rotation, np.eye(REGISTERED_DIMENSION), atol=1e-3)
        nonzero_per_row = np.sum(np.abs(rotation) > 1e-6, axis=1)
        assert np.all(nonzero_per_row > 1)

    def test_rotation_is_c_contiguous_and_owns_its_memory(self):
        rotation = gaussian_rotation(16, "algorithm_1", 0, "k", 0, "rotation")
        assert rotation.flags["C_CONTIGUOUS"]
        # Added 2026-08-28: the name promised owndata and never checked it.
        assert rotation.flags["OWNDATA"]

    def test_invalid_dimension_is_rejected(self):
        for bad in (0, -1):
            with pytest.raises(ValueError):
                gaussian_rotation(bad, "algorithm_1", 0, "k", 0, "rotation")
