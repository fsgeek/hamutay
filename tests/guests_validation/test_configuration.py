import hashlib
import io
import json
import os
from pathlib import Path

import pytest

from hamutay.assembly.binding import MembersMalformed, bind, load_members
from hamutay.heartbeat import guests_flag
from .conftest import write_members


@pytest.mark.parametrize('labels,expected', [(None, None), ([], ()), (['levadura', 'yupi'], ('levadura', 'yupi'))])
def test_absent_empty_and_populated_are_distinct_and_snapshot_unchanged(tmp_path, labels, expected):
    path = write_members(tmp_path, plaza=True)
    before = load_members(tmp_path).snapshot()
    write_members(tmp_path, plaza=True, guests=labels)
    cfg = load_members(tmp_path)
    assert cfg.guests == expected
    assert cfg.snapshot() == before
    binding, note = bind(tmp_path, cfg.members['qwen'].session, cfg.members['qwen'].events,
                         open_snapshots=[before])
    assert binding is not None, note
    assert guests_flag(binding) is (labels is not None)
    if labels is not None:
        assert f'guests {len(labels)}' in note
    assert cfg.digest == hashlib.sha256(path.read_bytes()).hexdigest()


@pytest.mark.parametrize('labels', ['levadura', None, {}, [1], ['ab', 'ab'], ['Ab'], ['ab\n'], ['a'], ['a' * 33]])
def test_invalid_guests_key_fails_closed(tmp_path, labels):
    path = write_members(tmp_path, plaza=True)
    body = json.loads(path.read_text())
    body['guests'] = labels
    path.write_text(json.dumps(body))
    with pytest.raises(MembersMalformed):
        load_members(tmp_path)


def test_flag_requires_binding_and_plaza(house_unplaza):
    assert guests_flag(None) is False
    root, _, _ = house_unplaza
    write_members(root, plaza=False, guests=[])
    cfg = load_members(root)
    binding, _ = bind(root, cfg.members['qwen'].session, cfg.members['qwen'].events)
    assert guests_flag(binding) is False


def test_digest_describes_parsed_bytes_during_atomic_replacement(tmp_path, monkeypatch):
    """Replace after the first read, regardless of read_text versus read_bytes.

    The filesystem seam simulates a concurrent configuration install, without
    patching any binding implementation helper or predicting its read strategy.
    """
    path = write_members(tmp_path, plaza=True, guests=['levadura'])
    original = path.read_bytes()
    replacement = path.with_name('replacement.json')
    body = json.loads(original)
    body['guests'] = ['yupi']
    replacement.write_text(json.dumps(body))
    real_open = io.open
    replaced = []

    class Reader:
        def __init__(self, wrapped):
            self.wrapped = wrapped
        def __enter__(self):
            self.wrapped.__enter__()
            return self
        def __exit__(self, *args):
            return self.wrapped.__exit__(*args)
        def __getattr__(self, name):
            return getattr(self.wrapped, name)
        def read(self, *args, **kwargs):
            data = self.wrapped.read(*args, **kwargs)
            if not replaced:
                os.replace(replacement, path)
                replaced.append(True)
            return data

    def intercept(file, *args, **kwargs):
        handle = real_open(file, *args, **kwargs)
        if isinstance(file, (str, os.PathLike)) and Path(file) == path and not replaced:
            return Reader(handle)
        return handle

    monkeypatch.setattr(io, 'open', intercept)
    cfg = load_members(tmp_path)
    assert replaced, 'The controlled replacement must actually occur during loading'
    assert cfg.guests == ('levadura',)
    assert cfg.digest == hashlib.sha256(original).hexdigest()
    assert load_members(tmp_path).guests == ('yupi',)
