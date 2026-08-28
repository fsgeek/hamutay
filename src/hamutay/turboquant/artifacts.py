"""Canonical and append-only artifact primitives for TurboQuant evidence."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import struct
import tempfile
from typing import BinaryIO

import numpy as np


def canonical_json_bytes(value: object) -> bytes:
    """Serialize JSON canonically for stable content hashing."""
    encoded = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )
    return encoded.encode("utf-8") + b"\n"


def sha256_file(path: Path) -> str:
    """Return the lowercase SHA-256 digest of one regular file."""
    resolved = Path(path)
    digest = hashlib.sha256()
    with resolved.open("rb") as artifact:
        for chunk in iter(lambda: artifact.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def create_run_directory(root: Path, run_id: str) -> Path:
    """Create one new run directory and refuse ambiguous reuse."""
    if (
        not isinstance(run_id, str)
        or not run_id
        or Path(run_id).name != run_id
        or run_id in {".", ".."}
        or "/" in run_id
        or "\\" in run_id
        or run_id[0]
        not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
        or any(
            character
            not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._-"
            for character in run_id
        )
    ):
        raise ValueError(
            "run_id must start with an ASCII alphanumeric character and contain "
            "only ASCII alphanumerics, '.', '_', or '-'"
        )
    resolved_root = Path(root)
    resolved_root.mkdir(parents=True, exist_ok=True)
    run_directory = resolved_root / run_id
    run_directory.mkdir()
    return run_directory


def _fsync_directory(directory: Path) -> None:
    descriptor = os.open(directory, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def atomic_write_bytes(path: Path, content: bytes, *, replace: bool = False) -> None:
    """Publish flushed bytes atomically, refusing replacement by default."""
    destination = Path(path)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{destination.name}.", suffix=".tmp", dir=destination.parent
    )
    temporary = Path(temporary_name)
    try:
        artifact = os.fdopen(descriptor, "wb")
        descriptor = -1
        with artifact:
            artifact.write(content)
            artifact.flush()
            os.fsync(artifact.fileno())
        if replace:
            os.replace(temporary, destination)
        else:
            os.link(temporary, destination)
            temporary.unlink()
        _fsync_directory(destination.parent)
    finally:
        if descriptor >= 0:
            os.close(descriptor)
        temporary.unlink(missing_ok=True)


def atomic_write_json(path: Path, value: object, *, replace: bool = False) -> None:
    """Publish one canonical JSON artifact atomically."""
    atomic_write_bytes(path, canonical_json_bytes(value), replace=replace)


def atomic_savez(path: Path, arrays: dict[str, np.ndarray]) -> None:
    """Publish an uncompressed NPZ atomically without replacing an artifact."""
    destination = Path(path)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{destination.name}.", suffix=".tmp", dir=destination.parent
    )
    temporary = Path(temporary_name)
    try:
        artifact = os.fdopen(descriptor, "wb")
        descriptor = -1
        with artifact:
            np.savez(artifact, **arrays)
            artifact.flush()
            os.fsync(artifact.fileno())
        os.link(temporary, destination)
        temporary.unlink()
        _fsync_directory(destination.parent)
    finally:
        if descriptor >= 0:
            os.close(descriptor)
        temporary.unlink(missing_ok=True)


def read_canonical_json(path: Path) -> object:
    """Read JSON only when its bytes already obey the canonical wire format."""
    raw = Path(path).read_bytes()
    value = json.loads(raw)
    if raw != canonical_json_bytes(value):
        raise ValueError(f"{path} is not canonical JSON")
    return value


def _update_length_prefixed(digest: BinaryIO, value: bytes) -> None:
    digest.update(struct.pack(">Q", len(value)))
    digest.update(value)


class ArrayStreamHasher:
    """Hash typed, shaped, C-order array batches with unambiguous framing."""

    def __init__(self) -> None:
        self._digest = hashlib.sha256(b"hamutay.turboquant.array-stream.v1\x00")

    def update(self, label: str, values: np.ndarray) -> None:
        if not isinstance(label, str) or not label:
            raise ValueError("array hash labels must be nonempty strings")
        array = np.asarray(values)
        if array.dtype.hasobject:
            raise ValueError("object arrays cannot enter evidence hashes")
        contiguous = np.ascontiguousarray(array)
        _update_length_prefixed(self._digest, label.encode("utf-8"))
        _update_length_prefixed(self._digest, contiguous.dtype.str.encode("ascii"))
        self._digest.update(struct.pack(">Q", contiguous.ndim))
        for extent in contiguous.shape:
            self._digest.update(struct.pack(">Q", extent))
        self._digest.update(contiguous.tobytes(order="C"))

    def hexdigest(self) -> str:
        return self._digest.hexdigest()


def sha256_array(name: str, values: np.ndarray) -> str:
    """Hash one array under the same framed dtype/shape/C-order contract."""
    digest = ArrayStreamHasher()
    digest.update(name, values)
    return digest.hexdigest()
