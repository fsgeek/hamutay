"""Stable seed derivation for reproducible TurboQuant experiments."""

import hashlib

import numpy as np

STUDY_SEED_HEX = "0b311d5d4eceaf773efde389305a1b5a"


def derive_seed(
    *fields: str | int,
    study_seed_hex: str = STUDY_SEED_HEX,
) -> int:
    """Derive a deterministic unsigned seed from the registered wire format."""
    if (
        not isinstance(study_seed_hex, str)
        or len(study_seed_hex) != 32
        or any(character not in "0123456789abcdef" for character in study_seed_hex)
    ):
        raise ValueError("study_seed_hex must be exactly 32 lowercase hexadecimal characters")

    serialized_fields: list[str] = []
    for field in fields:
        serialized = str(field)
        if "|" in serialized:
            raise ValueError("seed fields must not contain '|'")
        serialized_fields.append(serialized)

    wire = "|".join((study_seed_hex, *serialized_fields))
    return int.from_bytes(hashlib.sha256(wire.encode()).digest()[:16], "big")


def rng_for(*fields: str | int) -> np.random.Generator:
    """Return a fresh PCG64 generator seeded from ``fields``."""
    return np.random.Generator(np.random.PCG64(derive_seed(*fields)))
