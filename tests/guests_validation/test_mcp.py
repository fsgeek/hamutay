import asyncio
import json

import pytest

from hamutay.assembly.binding import load_members
from hamutay.plaza.mcp import build_server, plaza_post_impl, plaza_read_impl, plaza_send_impl
from hamutay.plaza.read import read_rows
from .conftest import write_members


def refusal(result):
    assert isinstance(result, dict)
    assert not result.get('sent', False)
    assert any(isinstance(v, str) and v for v in result.values()), result


def test_mcp_admission_is_reloaded_for_every_call(house_guests):
    root, cfg, _ = house_guests
    first = plaza_post_impl(root, 'levadura', 'post', key='held')
    assert first['sent']
    assert plaza_send_impl(root, 'levadura', 'elder', 'directed', key='d')['sent']
    assert plaza_read_impl(root, 'levadura') == read_rows(cfg)
    write_members(root, plaza=True, guests=['yupi'])
    before = cfg.plaza.read_bytes()
    refusal(plaza_post_impl(root, 'levadura', 'post', key='held'))
    refusal(plaza_send_impl(root, 'levadura', 'elder', 'new', key='new'))
    assert cfg.plaza.read_bytes() == before
    # Admission controls writing; readable historical rows survive removal.
    assert plaza_read_impl(root, 'levadura') == read_rows(load_members(root))
    write_members(root, plaza=True, guests=['levadura'])
    assert plaza_post_impl(root, 'levadura', 'post', key='held')['duplicate_of_seq'] == first['seq']


@pytest.mark.parametrize('bad_house', ['disabled', 'malformed_members', 'malformed_ledger'])
def test_mcp_writes_return_refusals_but_reads_raise(house_guests, bad_house):
    root, cfg, _ = house_guests
    if bad_house == 'disabled':
        write_members(root, plaza=False, guests=['levadura'])
    elif bad_house == 'malformed_members':
        (root / 'community/plaza/members.json').write_text('{not json}\n')
    else:
        cfg.plaza.write_text('{"record_type":"unknown","seq":1}\n')
    refusal(plaza_post_impl(root, 'levadura', 'post'))
    refusal(plaza_send_impl(root, 'levadura', 'elder', 'directed'))
    with pytest.raises(Exception):
        plaza_read_impl(root, 'levadura')


def test_mcp_empty_and_inclusive_read(house_guests):
    root, _, _ = house_guests
    assert plaza_read_impl(root, 'levadura') == []
    a = plaza_post_impl(root, 'levadura', 'a')
    b = plaza_post_impl(root, 'levadura', 'b')
    rows = plaza_read_impl(root, 'levadura', since_seq=a['seq'], through_seq=b['seq'])
    assert [r['text'] for r in rows] == ['a', 'b']
    assert plaza_read_impl(root, 'levadura', since_seq=b['seq'] + 1) == []


def test_server_tools_cannot_choose_identity_and_restart_keeps_token(house_guests):
    root, cfg, _ = house_guests
    async def exercise():
        first = build_server(root, 'levadura')
        schemas = {tool.name: tool for tool in await first.list_tools()}
        assert set(schemas) == {'plaza_read', 'plaza_post', 'plaza_send'}
        for name, schema in schemas.items():
            fields = set(schema.inputSchema.get('properties', {}))
            assert not fields.intersection({'actor', 'label', 'guest', 'from', 'via', 'root', 'project_root', 'wake'})
            if name != 'plaza_read':
                assert 'key' in fields
        await first.call_tool('plaza_post', {'text': 'after restart', 'key': 'persisted'})
        before = cfg.plaza.read_bytes()
        restarted = build_server(root, 'levadura')
        await restarted.call_tool('plaza_post', {'text': 'after restart', 'key': 'persisted'})
        assert cfg.plaza.read_bytes() == before
        rows = read_rows(cfg)
        assert len(rows) == 1 and rows[0]['from'] == 'guest:levadura'
    asyncio.run(exercise())
