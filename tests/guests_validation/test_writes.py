from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
import json

import pytest

from hamutay.assembly.binding import load_members
from hamutay.plaza.read import read_rows
from hamutay.plaza.records import validate_plaza
from hamutay.plaza.send import SendRefused, send
from .conftest import cli, records, write_members

NOW = datetime(2026, 9, 29, 23, 59, tzinfo=timezone.utc)


def write(cfg, *, actor='guest:levadura', via='cli', to='elder', text='hello', key=None, now=NOW):
    return send(cfg, actor=actor, via=via, to=to, text=text, key=key, now=now)


def test_removed_label_history_valid_but_next_send_and_retry_refused(house_guests):
    root, cfg, _ = house_guests
    first = write(cfg, key='held')
    before = cfg.plaza.read_bytes()
    write_members(root, plaza=True, guests=[])
    current = load_members(root)
    for via in ('cli', 'mcp'):
        for key in ('held', 'new'):
            with pytest.raises(SendRefused, match='not admitted'):
                write(current, via=via, key=key)
    rows = records(current)
    validate_plaza(rows, list(range(1, len(rows) + 1)))
    assert read_rows(current)[0]['message_id'] == first['message_id']
    assert cfg.plaza.read_bytes() == before


def test_shared_cap_duplicate_48_posts_rollover_humans_and_second_label(house_guests):
    root, _, _ = house_guests
    write_members(root, plaza=True, guests=['levadura', 'yupi'])
    cfg = load_members(root)
    for n in range(48):
        last = write(cfg, via=('cli', 'mcp')[n % 2], key=f'cap-{n}')
    before = cfg.plaza.read_bytes()
    retry = write(load_members(root), via='cli', key='cap-47')
    assert retry['duplicate_of_seq'] == last['seq']
    assert cfg.plaza.read_bytes() == before
    for via in ('cli', 'mcp'):
        with pytest.raises(SendRefused) as exc:
            write(cfg, via=via, key='49')
        assert '2026-09-30' in str(exc.value)
    for n in range(50):
        assert write(cfg, to='plaza', key=f'post-{n}')['sent']
        assert write(cfg, actor='tony', key=f'human-{n}')['sent']
    assert write(cfg, actor='guest:yupi', key='cap-0')['sent']
    # Same local date, next UTC day: rollover must use UTC, not local date.
    next_day = datetime.fromisoformat('2026-09-29T17:01:00-07:00')
    assert write(cfg, now=next_day, key='49')['sent']


def test_concurrent_transports_share_last_slot(house_guests):
    _, cfg, _ = house_guests
    for n in range(47):
        write(cfg, key=str(n))
    from threading import Barrier
    gate = Barrier(2)
    def contender(via):
        gate.wait()
        try:
            return write(cfg, via=via, key=via)
        except SendRefused as exc:
            return str(exc)
    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(contender, ['cli', 'mcp']))
    assert sum(isinstance(x, dict) and x.get('sent') is True for x in outcomes) == 1
    assert len(read_rows(cfg)) == 48


def test_token_content_canonicalization_and_transport_retry(house_guests):
    _, cfg, _ = house_guests
    first = write(cfg, key='stable')
    before = cfg.plaza.read_bytes()
    second = write(cfg, via='mcp', to='door:elder', key='stable')
    assert second['message_id'] == first['message_id']
    assert second['duplicate_of_seq'] == first['seq']
    for changes in ({'text': 'hello '}, {'to': 'fable'}, {'to': 'plaza'}):
        with pytest.raises(SendRefused, match='token reused for different content'):
            write(cfg, key='stable', **changes)
    assert cfg.plaza.read_bytes() == before


def test_no_token_always_new_and_same_token_namespaced(house_guests):
    root, _, _ = house_guests
    write_members(root, plaza=True, guests=['levadura', 'yupi'])
    cfg = load_members(root)
    results = [write(cfg, to='plaza', via=v) for v in ('cli', 'mcp', 'cli')]
    results += [write(cfg, actor=a, key='shared', to='plaza')
                for a in ('guest:levadura', 'guest:yupi', 'tony')]
    assert len({r['message_id'] for r in results}) == 6
    assert len(read_rows(cfg)) == 6
    assert all(not member.events.exists() for member in cfg.members.values())


def test_cli_new_process_retry_and_read_use_shared_rows(house_guests, tmp_path):
    root, cfg, _ = house_guests
    text = tmp_path / 'input.txt'
    text.write_text('verbatim guest\ntext')
    args = ['send', '--by', 'guest:levadura', '--to', 'plaza', '--text-file', str(text), '--key', 'restart']
    first = cli(root, *args)
    assert first.returncode == 0, first.stderr
    before = cfg.plaza.read_bytes()
    retry = cli(root, *args)
    assert retry.returncode == 0, retry.stderr
    assert 'duplicate_of_seq' in retry.stdout
    assert cfg.plaza.read_bytes() == before
    out = cli(root, 'read', '--since-seq', '1', '--through-seq', '1')
    assert out.returncode == 0, out.stderr
    assert [json.loads(line) for line in out.stdout.splitlines()] == read_rows(cfg, since_seq=1, through_seq=1)


def test_read_bounds_empty_and_delivery_truth(house_guests):
    _, cfg, _ = house_guests
    assert read_rows(cfg) == []
    a = write(cfg, to='plaza', key='post')
    b = write(cfg, key='directed')
    c = write(cfg, to='plaza', key='post2')
    rows = read_rows(cfg, since_seq=a['seq'], through_seq=b['seq'])
    assert [r['seq'] for r in rows] == [a['seq'], b['seq']]
    assert rows[0]['truth'] == {'state': 'post'}
    assert rows[1]['truth']['state'] == 'landed'
    for field in ('message_id', 'from', 'via', 'to', 'text', 'sent_at'):
        assert field in rows[0]
    assert read_rows(cfg, since_seq=c['seq'] + 1) == []
    assert read_rows(cfg, since_seq=c['seq'], through_seq=a['seq']) == []
    assert [r['seq'] for r in read_rows(cfg, posts_only=True)] == [a['seq'], c['seq']]


def test_directed_record_carries_loaded_digest_and_posts_have_no_delivery(house_guests):
    root, cfg, _ = house_guests
    write(cfg, key='provenance')
    write(cfg, to='plaza', key='no-delivery')
    messages = [r for r in records(cfg) if r['record_type'] == 'message']
    assert messages[0]['delivery']['members_digest'] == cfg.digest
    assert messages[0]['delivery']['events_path'] == str(cfg.members['elder'].events)
    assert messages[1]['delivery'] is None
    stored = [json.loads(line) for line in cfg.members['elder'].events.read_text().splitlines()]
    event_id = messages[0]['delivery']['event_id']
    # Event record format is the public event-store format: match the inbound
    # record carrying purpose, not any later status rows for the same id.
    events = [r for r in stored if r.get('event_id') == event_id and 'purpose' in r]
    assert len(events) == 1
    assert events[0]['origin'] == 'member'
    assert events[0]['sender'] == 'guest:levadura'
    assert events[0]['defer_to_declared_quiet'] is True
    assert events[0].get('expires_at') is None
