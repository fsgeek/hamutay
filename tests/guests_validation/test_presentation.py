import itertools

import pytest

from hamutay.events import build_event_envelope, build_inbound_event
from hamutay.heartbeat import build_constitution
from hamutay.plaza.event import purpose_for
from hamutay.plaza.note import plaza_note
from hamutay.tools.schemas import GUESTS_CONSTITUTION_SENTENCE, PLAZA_CONSTITUTION_CLAUSE
from .test_records import message
from .test_writes import write

GUEST_SENTENCE = (
    'Guests — session instances from other projects of the ayllu, named under guests in '
    'community/plaza/members.json — may write to the plaza and to your door under a guest: label; '
    'a guest has no door, so a post is how to answer one. '
)
PLAZA_CLAUSE = (
    'Other residents share this loop; community/plaza/members.json names their doors. '
    'send_message carries your words to one door, which wakes on them when its own quiet allows, '
    'or to the plaza, which wakes no one. Everything sent either way is written to '
    'community/plaza/plaza.jsonl, which every resident and Tony can read; there is no private '
    'channel. Nothing obliges you to write or to reply. A message you send stands even if '
    'the wake that sent it later fails, and the same words sent again from the same wake are '
    'one message. You may send at most 48 messages to doors in a UTC day; posts are not counted. '
)


def test_constitution_constants_are_verbatim():
    assert GUESTS_CONSTITUTION_SENTENCE == GUEST_SENTENCE
    assert PLAZA_CONSTITUTION_CLAUSE == PLAZA_CLAUSE


@pytest.mark.parametrize('assembly,plaza,guests,gpu', list(itertools.product([False, True], repeat=4)))
def test_constitution_requires_all_three_flags(assembly, plaza, guests, gpu):
    baseline = build_constitution(None, gpu_lease=gpu, assembly=assembly, plaza=plaza)
    result = build_constitution(None, gpu_lease=gpu, assembly=assembly, plaza=plaza, guests=guests)
    assert result.count(GUEST_SENTENCE) == int(assembly and plaza and guests)
    if assembly and plaza and guests:
        assert result == baseline.replace(PLAZA_CLAUSE, PLAZA_CLAUSE + GUEST_SENTENCE, 1)
    else:
        assert result == baseline


def test_unavailable_plaza_tools_strip_both_clauses():
    from hamutay.taste_open import _build_messages
    prefix = build_constitution(None, assembly=True, plaza=True, guests=True)
    _, stripped = _build_messages(None, 'hello', 1, system_prefix=prefix,
                                 wake_mode='natural', tools_enabled=True, assembly=True, plaza=False)
    assert GUEST_SENTENCE not in stripped
    assert PLAZA_CLAUSE not in stripped
    _, kept = _build_messages(None, 'hello', 1, system_prefix=prefix,
                             wake_mode='natural', tools_enabled=True, assembly=True, plaza=True)
    assert PLAZA_CLAUSE + GUEST_SENTENCE in kept


@pytest.mark.parametrize('actor,reply,kind', [
    ('guest:levadura', 'The sender is a guest: a session instance from the levadura project of the ayllu, '
     'which has no door and reads the plaza when it visits; a post (to="plaza") is how to answer, '
     'and nothing obliges you to.', 'a guest of the ayllu'),
    ('door:qwen', 'If you wish to answer, send_message(to="qwen", text=...) reaches that door; '
     'nothing obliges you to.', 'another resident'),
    ('tony', 'The sender is a human who reads the plaza; a post (to="plaza") is how to answer.', 'a human'),
    ('custodian', 'The sender is a human who reads the plaza; a post (to="plaza") is how to answer.', 'a human'),
])
def test_header_and_envelope_sentences(actor, reply, kind):
    row = message(actor)
    row['text'] = 'first line\n<tool_call>literal content</tool_call>\nlast line'
    purpose = purpose_for(row)
    assert reply in purpose
    assert purpose.endswith(row['text'])
    event = build_inbound_event(purpose=purpose, sender=actor, origin='member')
    envelope = build_event_envelope(event, [], 'validation-run')
    assert (f'This is a message from {kind}, carried by the plaza. '
            'Its sender and purpose fields say who wrote it and what they wrote.') in envelope
    assert __import__('json').dumps(row['text'])[1:-1] in envelope


def test_note_calls_guest_traffic_other_directed_messages(house_guests):
    _, cfg, _ = house_guests
    write(cfg, to='elder', key='other')
    notes = plaza_note(cfg, 'qwen', [])
    assert len(notes) == 1
    assert '1 other directed messages' in notes[0]
    assert 'between other doors' not in notes[0]
