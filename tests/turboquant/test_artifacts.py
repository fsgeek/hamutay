import hashlib
import struct

import numpy as np
import pytest

from hamutay.turboquant.artifacts import (
    ArrayStreamHasher,
    canonical_json_bytes,
    create_run_directory,
    sha256_file,
)


def test_canonical_json_is_sorted_compact_and_newline_terminated():
    encoded = canonical_json_bytes({"z": 1, "a": [2, 3]})

    assert encoded == b'{"a":[2,3],"z":1}\n'


def test_run_directory_refuses_overwrite(tmp_path):
    created = create_run_directory(tmp_path, "registered-001")

    assert created.is_dir()
    with pytest.raises(FileExistsError):
        create_run_directory(tmp_path, "registered-001")


def test_canonical_json_preserves_utf8_and_refuses_nonfinite_values():
    assert canonical_json_bytes({"glyph": "ñ"}) == b'{"glyph":"\xc3\xb1"}\n'
    with pytest.raises(ValueError):
        canonical_json_bytes({"invalid": float("nan")})


def test_sha256_file_hashes_exact_bytes(tmp_path):
    artifact = tmp_path / "artifact.bin"
    artifact.write_bytes(b"TurboQuant\x00evidence\n")

    assert sha256_file(artifact) == hashlib.sha256(artifact.read_bytes()).hexdigest()


def test_array_stream_hash_frames_label_dtype_shape_and_c_order_bytes():
    values = np.array([[1.0, -2.0]], dtype=np.float32)
    expected = hashlib.sha256(b"hamutay.turboquant.array-stream.v1\x00")
    for field in (b"checkpoint", values.dtype.str.encode("ascii")):
        expected.update(struct.pack(">Q", len(field)))
        expected.update(field)
    expected.update(struct.pack(">Q", 2))
    expected.update(struct.pack(">Q", 1))
    expected.update(struct.pack(">Q", 2))
    expected.update(values.tobytes(order="C"))

    observed = ArrayStreamHasher()
    observed.update("checkpoint", values)

    assert observed.hexdigest() == expected.hexdigest()


def test_array_stream_hash_changes_with_dtype_or_shape():
    base = ArrayStreamHasher()
    base.update("codes", np.array([[1, 2]], dtype=np.uint8))
    different_dtype = ArrayStreamHasher()
    different_dtype.update("codes", np.array([[1, 2]], dtype=np.uint16))
    different_shape = ArrayStreamHasher()
    different_shape.update("codes", np.array([1, 2], dtype=np.uint8))

    assert (
        len(
            {base.hexdigest(), different_dtype.hexdigest(), different_shape.hexdigest()}
        )
        == 3
    )


@pytest.mark.parametrize("run_id", ["", ".", "..", "nested/run", "nested\\run"])
def test_run_directory_rejects_ambiguous_names(tmp_path, run_id):
    with pytest.raises(ValueError):
        create_run_directory(tmp_path, run_id)
