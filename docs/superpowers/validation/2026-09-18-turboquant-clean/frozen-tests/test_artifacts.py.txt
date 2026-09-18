import pytest
from hamutay.turboquant.artifacts import canonical_json_bytes, sha256_file

def test_canonical_json_bytes():
    obj = {"b": 2, "a": 1, "c": "test\u1234"}
    b = canonical_json_bytes(obj)
    assert b.endswith(b"\n")
    assert b == b'{"a":1,"b":2,"c":"test\xe1\x88\xb4"}\n'

def test_canonical_json_rejects_nonfinite():
    with pytest.raises(Exception):
        canonical_json_bytes({"a": float("inf")})
    with pytest.raises(Exception):
        canonical_json_bytes({"a": float("nan")})

def test_sha256_file(tmp_path):
    p = tmp_path / "test.txt"
    p.write_text("hello world")
    h = sha256_file(p)
    assert h == "b94d27b9934d3e08a52e52d7da7dabfac484efe37a5380ee9088f7ace2efcde9"
