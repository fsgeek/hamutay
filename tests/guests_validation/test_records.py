"""Section 2's validator oracle is independent of the writer."""
import hashlib
from uuid import NAMESPACE_URL, uuid4, uuid5

import pytest

from hamutay.assembly.ledger import LedgerMalformed
from hamutay.plaza.ids import GUEST_LABEL_RE, GUEST_RE, guest_key, guest_label, is_guest
from hamutay.plaza.records import reduce, validate_plaza

NS = uuid5(NAMESPACE_URL, 'hamutay:plaza')
STAMP = '2026-09-29T00:30:00+00:00'


def message(actor='guest:levadura', via='cli', wake=None, *, to='plaza'):
    mid = str(uuid4())
    text = 'independent specimen'
    key = str(uuid5(NS, 'guest:levadura\0operation'))
    if via == 'tool' and wake:
        key = str(uuid5(NS, f"{wake['event_id']}\0{to}\0{hashlib.sha256(text.encode()).hexdigest()}"))
    return dict(record_type='message', seq=1, created_at=STAMP, message_id=mid,
                idempotency_key=key, **{'from': actor}, via=via, to=to, text=text,
                sent_at=STAMP, wake=wake, delivery=None if to == 'plaza' else dict(
                    door='elder', events_path='/tmp/elder.events.jsonl',
                    event_id=str(uuid5(NS, f'{mid}\0door:elder')), members_digest='a' * 64))


def wake():
    return dict(cycle=1, record_id=str(uuid4()), event_id=str(uuid4()),
                run_id=str(uuid4()), started_at=STAMP)


@pytest.mark.parametrize('actor', ['door:qwen', 'tony', 'custodian', 'guest:levadura'])
@pytest.mark.parametrize('via', ['tool', 'cli', 'mcp'])
@pytest.mark.parametrize('has_wake', [False, True])
def test_complete_actor_transport_wake_matrix(actor, via, has_wake):
    row = message(actor, via, wake() if has_wake else None)
    valid = ((actor == 'door:qwen' and via == 'tool' and has_wake)
             or (actor in ('tony', 'custodian') and via == 'cli' and not has_wake)
             or (actor.startswith('guest:') and via in ('cli', 'mcp') and not has_wake))
    if valid:
        validate_plaza([row], [1])
    else:
        with pytest.raises(LedgerMalformed):
            validate_plaza([row], [1])


@pytest.mark.parametrize('label,valid', [('ab', True), ('a' * 32, True), ('a0-', True),
    ('Ab', False), ('ab\n', False), ('a', False), ('a' * 33, False),
    ('a_b', False), ('0a', False), ('', False)])
def test_exact_label_grammar(label, valid):
    actor = 'guest:' + label
    assert bool(GUEST_LABEL_RE.fullmatch(label)) is valid
    assert bool(GUEST_RE.fullmatch(actor)) is valid
    assert is_guest(actor) is valid
    if valid:
        assert guest_label(actor) == label
        validate_plaza([message(actor)], [1])
    else:
        with pytest.raises(LedgerMalformed):
            validate_plaza([message(actor)], [1])


def test_key_formula_is_label_scoped_and_not_human_cli():
    token = 'op:α/first'
    keys = [guest_key(label, token) for label in ('levadura', 'yupi')]
    assert keys == [str(uuid5(NS, f'guest:{label}\0{token}')) for label in ('levadura', 'yupi')]
    assert len(set(keys + [str(uuid5(NS, 'cli\0' + token))])) == 3


def test_reducer_counts_exact_actor_and_utc_date_not_transport_or_posts():
    rows = []
    for actor, via, to, stamp in [
        ('guest:levadura', 'cli', 'door:elder', '2026-09-28T17:30:00-07:00'),
        ('guest:levadura', 'mcp', 'door:elder', STAMP),
        ('guest:levadura', 'cli', 'plaza', STAMP),
        ('guest:yupi', 'mcp', 'door:elder', STAMP),
    ]:
        row = message(actor, via, to=to)
        row.update(seq=len(rows) + 1, sent_at=stamp, idempotency_key=str(uuid5(NS, str(len(rows)))))
        rows.append(row)
    validate_plaza(rows, list(range(1, 5)))
    from datetime import date
    view = reduce(rows)
    assert view.sent_today('guest:levadura', date(2026, 9, 29)) == 2
    assert view.sent_today('guest:levadura', date(2026, 9, 28)) == 0
    assert view.sent_today('guest:yupi', date(2026, 9, 29)) == 1
