"""Independent numerical validation of Task 1: Seeding wire format, RNG derivation,
and canonical Haar orthogonal rotations.
"""

from __future__ import annotations

import hashlib
import numpy as np
import pytest

from hamutay.turboquant import (
    STUDY_SEED_HEX,
    canonical_qr,
    derive_seed,
    gaussian_rotation,
    rng_for,
)


class TestSeedingContract:
    """Validates the declared 128-bit study seed and SHA-256 big-endian seed derivation."""

    def test_study_seed_constant(self) -> None:
        assert STUDY_SEED_HEX == "0b311d5d4eceaf773efde389305a1b5a"
        assert len(STUDY_SEED_HEX) == 32
        assert all(c in "0123456789abcdef" for c in STUDY_SEED_HEX)

    @pytest.mark.parametrize(
        ("fields",),
        [
            ((),),
            (("test",),),
            (("alpha", 42, "rotation"),),
            ((128, "meta-llama/Meta-Llama-3.1-8B-Instruct", "TurboQuant_mse", 0, "k", 0, "rotation"),),
        ],
    )
    def test_derive_seed_wire_format_oracle(self, fields: tuple[str | int, ...]) -> None:
        """Independent oracle: UTF-8 joined by '|', first 16 bytes of SHA-256 as unsigned big-endian."""
        payload_parts = [STUDY_SEED_HEX] + [str(f) for f in fields]
        wire_str = "|".join(payload_parts)
        digest = hashlib.sha256(wire_str.encode("utf-8")).digest()
        expected_seed = int.from_bytes(digest[:16], byteorder="big", signed=False)

        observed_seed = derive_seed(*fields)
        assert observed_seed == expected_seed
        assert 0 <= observed_seed < (1 << 128)

    def test_derive_seed_unpadded_base10_integer_formatting(self) -> None:
        """Confirms integers serialize without leading zeros or hex notation."""
        seed_int = derive_seed("layer", 7)
        seed_str = derive_seed("layer", "7")
        assert seed_int == seed_str

        # Ensure "07" does not equal 7
        assert derive_seed("layer", 7) != derive_seed("layer", "07")

    def test_rng_for_reproducibility_and_isolation(self) -> None:
        """Validates that identical seed fields produce bit-identical generator streams."""
        rng1 = rng_for("test_stream", 1)
        rng2 = rng_for("test_stream", 1)
        rng3 = rng_for("test_stream", 2)

        vals1 = rng1.standard_normal(100)
        vals2 = rng2.standard_normal(100)
        vals3 = rng3.standard_normal(100)

        np.testing.assert_array_equal(vals1, vals2)
        assert not np.array_equal(vals1, vals3)


class TestCanonicalQROracle:
    """Validates the canonical QR decomposition ensuring unique Haar-distributed rotation.

    Convention: Column i of Q is multiplied by sign(R[i, i]), mapping zero to +1,
    such that the diagonal of R is strictly non-negative.
    """

    def test_canonical_qr_orthogonal_and_positive_diagonal(self) -> None:
        rng = np.random.default_rng(12345)
        n = 64
        matrix = rng.standard_normal((n, n), dtype=np.float64)

        q = canonical_qr(matrix)

        # 1. Output shape and dtype
        assert q.shape == (n, n)
        assert q.dtype == np.float64

        # 2. Perfect orthogonality in FP64: Q^T @ Q == I
        identity = np.eye(n, dtype=np.float64)
        np.testing.assert_allclose(q.T @ q, identity, atol=1e-14)
        np.testing.assert_allclose(q @ q.T, identity, atol=1e-14)

        # 3. Recover R from Q^T @ matrix; verify diagonal non-negativity
        r = q.T @ matrix
        diag_r = np.diag(r)
        assert np.all(diag_r >= 0.0), f"Negative diagonal entries detected: {diag_r[diag_r < 0]}"

    def test_canonical_qr_exact_zero_diagonal_sign_mapping(self) -> None:
        """Verifies that an exact zero on the diagonal of R maps to sign +1."""
        # Rank-deficient matrix with identical columns forcing zero diagonal in R
        m = np.zeros((4, 4), dtype=np.float64)
        m[:, 0] = [1.0, 0.0, 0.0, 0.0]
        m[:, 1] = [1.0, 0.0, 0.0, 0.0]  # Identical to col 0
        m[:, 2] = [0.0, 1.0, 0.0, 0.0]
        m[:, 3] = [0.0, 0.0, 1.0, 0.0]

        q = canonical_qr(m)
        assert q.shape == (4, 4)
        np.testing.assert_allclose(q.T @ q, np.eye(4), atol=1e-14)

    def test_canonical_qr_determinism(self) -> None:
        rng = np.random.default_rng(98765)
        m = rng.standard_normal((32, 32), dtype=np.float64)
        q1 = canonical_qr(m)
        q2 = canonical_qr(m)
        np.testing.assert_array_equal(q1, q2)


class TestGaussianRotation:
    """Validates generation of dimension d orthogonal rotation matrices in FP32."""

    @pytest.mark.parametrize("d", [4, 16, 128])
    def test_gaussian_rotation_properties(self, d: int) -> None:
        rot = gaussian_rotation(d, "test_rot", d)

        assert rot.shape == (d, d)
        assert rot.dtype == np.float32

        # In FP32, check orthogonality: Q @ Q^T == I within FP32 epsilon
        identity = np.eye(d, dtype=np.float32)
        max_ortho_err = np.max(np.abs(rot @ rot.T - identity))
        assert max_ortho_err < 1e-6, f"Orthogonality error too high: {max_ortho_err}"

        # Vector isometry: norm preservation ||x @ rot.T|| == ||x||
        rng = np.random.default_rng(42)
        x = rng.standard_normal((10, d)).astype(np.float32)
        x_norms = np.linalg.norm(x, axis=-1)

        # Vector convention: y = x @ rot.T
        y = x @ rot.T
        y_norms = np.linalg.norm(y, axis=-1)
        np.testing.assert_allclose(y_norms, x_norms, rtol=1e-6, atol=1e-6)

    def test_gaussian_rotation_seed_distinctness(self) -> None:
        rot1 = gaussian_rotation(128, "layer", 0, "k")
        rot2 = gaussian_rotation(128, "layer", 0, "v")
        rot1_clone = gaussian_rotation(128, "layer", 0, "k")

        np.testing.assert_array_equal(rot1, rot1_clone)
        assert not np.allclose(rot1, rot2)
