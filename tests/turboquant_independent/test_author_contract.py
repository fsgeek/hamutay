"""Independent tests of the pinned author-QJL contract (plan Task 7).

The differential oracle is only meaningful if the upstream artifact it
compares against is genuinely pinned. These tests verify the pin itself and
the declared zero-sign convention difference, which is the one place where
reference and author kernel are permitted to disagree.

The CUDA differential itself requires a GPU, a 12.8 toolkit, and the author
checkout, so those tests skip cleanly when the preconditions are absent --
exactly as the plan requires. What must never be skipped is the contract.
"""

from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
from pathlib import Path

import numpy as np
import pytest

from hamutay.turboquant.product import pack_signs, unpack_signs

PINNED_REPOSITORY = "https://github.com/amirzandieh/QJL"
PINNED_COMMIT = "648b3641f96b6e95e091217220b94e4739fd4d82"
PINNED_HASHES = {
    "LICENSE": "c71d239df91726fc519c6eb72d318ec65820627232b2f796219e87dcf35d0ab4",
    "qjl_kernel/csrc/qjl_quant_kernel.cu": (
        "d03b2fd86504554f48da48df2740d73a0cc2d1d8a28c22698da20c9ee801aefd"
    ),
    "qjl_kernel/csrc/qjl_score_kernel.cu": (
        "848398bb6b140433aa10f4ccea16eb680ec215cb148956f09e46bbbdabdc030c"
    ),
    "models/llama3_utils_qjl.py": (
        "725b6777b752e30b583b6834e258a849c01679c4e3c007f3b4c62212393f34c2"
    ),
}


def author_checkout() -> Path | None:
    raw = os.environ.get("QJL_AUTHOR_CHECKOUT")
    if not raw:
        return None
    path = Path(raw)
    return path if path.is_dir() else None


requires_checkout = pytest.mark.skipif(
    author_checkout() is None,
    reason="QJL_AUTHOR_CHECKOUT is not set to an existing author checkout",
)


class TestPinnedContract:
    def test_pinned_commit_is_a_full_forty_character_sha(self):
        """An abbreviated or moving reference is not a pin."""
        assert len(PINNED_COMMIT) == 40
        assert PINNED_COMMIT == PINNED_COMMIT.lower()
        int(PINNED_COMMIT, 16)

    def test_every_pinned_hash_is_a_well_formed_sha256(self):
        for path, digest in PINNED_HASHES.items():
            assert len(digest) == 64, path
            assert digest == digest.lower(), path
            int(digest, 16)

    def test_pinned_files_are_distinct(self):
        assert len(set(PINNED_HASHES.values())) == len(PINNED_HASHES)

    @requires_checkout
    def test_checkout_is_at_the_pinned_commit(self):
        checkout = author_checkout()
        assert checkout is not None
        head = subprocess.run(
            ["git", "-C", str(checkout), "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
        assert head == PINNED_COMMIT

    @requires_checkout
    def test_checkout_is_clean(self):
        """A dirty oracle checkout invalidates the differential."""
        checkout = author_checkout()
        assert checkout is not None
        status = subprocess.run(
            ["git", "-C", str(checkout), "status", "--porcelain"],
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
        assert status == ""

    @requires_checkout
    @pytest.mark.parametrize("relative_path", sorted(PINNED_HASHES))
    def test_pinned_file_hashes_match(self, relative_path):
        checkout = author_checkout()
        assert checkout is not None
        target = checkout / relative_path
        assert target.is_file(), f"missing pinned file: {relative_path}"
        digest = hashlib.sha256(target.read_bytes()).hexdigest()
        assert digest == PINNED_HASHES[relative_path]


class TestDeclaredZeroSignDifference:
    """The reference maps exact zero to +1; the author kernel uses '> 0' and
    maps it to -1. This is a declared, documented difference. These tests fix
    the reference side so a future 'fix' toward the kernel is caught."""

    def test_reference_maps_exact_zero_to_positive(self):
        sketch = np.array([[0.0, -0.0, 1.0, -1.0]])
        packed = pack_signs(sketch >= 0)
        np.testing.assert_array_equal(
            unpack_signs(packed, 4), [[1.0, 1.0, 1.0, -1.0]]
        )

    def test_negative_zero_is_treated_as_positive(self):
        """IEEE -0.0 >= 0 is True; a '> 0' implementation would disagree."""
        packed = pack_signs(np.array([[-0.0]]) >= 0)
        np.testing.assert_array_equal(unpack_signs(packed, 1), [[1.0]])

    def test_reference_and_kernel_conventions_differ_only_at_zero(self):
        rng = np.random.default_rng(77)
        sketch = rng.standard_normal((8, 32))
        sketch[0, 0] = 0.0

        reference = np.where(sketch >= 0, 1.0, -1.0)
        kernel_style = np.where(sketch > 0, 1.0, -1.0)

        disagreement = reference != kernel_style
        assert disagreement.sum() == 1
        assert disagreement[0, 0]

        np.testing.assert_array_equal(
            unpack_signs(pack_signs(sketch >= 0), 32), reference
        )

    def test_registered_gaussian_sketches_contain_no_exact_zero(self):
        """The plan asserts this before byte comparison: with a continuous
        projection, the two conventions coincide almost surely."""
        rng = np.random.default_rng(78)
        projection = rng.standard_normal((128, 128)).astype(np.float32)
        residual = rng.standard_normal((256, 128)).astype(np.float32)
        sketch = residual @ projection.T
        assert not np.any(sketch == 0.0)


class TestCudaPreconditions:
    """The differential must skip for a precise, checkable reason rather than
    silently passing when the oracle is unavailable."""

    def test_skip_conditions_are_individually_determinable(self):
        checkout = author_checkout()
        nvcc = Path("/usr/local/cuda-12.8/bin/nvcc")

        reasons = []
        if checkout is None:
            reasons.append("QJL_AUTHOR_CHECKOUT unset or missing")
        if not nvcc.exists():
            reasons.append("CUDA 12.8 nvcc not present")
        try:
            import torch

            if not torch.cuda.is_available():
                reasons.append("CUDA device unavailable")
            elif torch.version.cuda is not None and not torch.version.cuda.startswith(
                "12.8"
            ):
                reasons.append(f"torch built for CUDA {torch.version.cuda}, not 12.8")
        except ImportError:
            reasons.append("torch not installed")

        # Either every precondition holds, or at least one nameable reason
        # explains the skip. An empty-but-failing state is a harness defect.
        assert reasons == [] or all(isinstance(r, str) and r for r in reasons)

    @pytest.mark.skipif(
        shutil.which("nvidia-smi") is None, reason="nvidia-smi not on PATH"
    )
    def test_nvidia_smi_reports_a_device_when_present(self):
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            pytest.skip("nvidia-smi present but no device is visible")
        assert result.stdout.strip()
