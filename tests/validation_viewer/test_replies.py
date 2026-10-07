"""Tony's mail is the sole exception to the viewer's private-wake boundary."""

import json
from datetime import timedelta
from uuid import uuid4

import pytest

from hamutay.events import EVENT_TYPE_REFLECTION, EventStore, build_inbound_event
from hamutay.viewer import state

from .conftest import NOW, STAMP, event, write_jsonl
from .test_http import request
from .test_page import ParsedHTML, assert_no_active_payload, render


def outcome(eid, status="completed", **fields):
    # Real running/completed records carry event_id, not the pending sender.
    row = event(eid, status, **fields)
    for key in ("sender", "purpose", "created_at"):
        row.pop(key, None)
    return row


def replies_html(view):
    return render("refresh", view=view)["elements"]["replies"]["innerHTML"]


def surfaces(community):
    view = state.gather(community.root, NOW)
    code, _, body = request(community.root, "/api/state")
    assert code == 200
    api = json.loads(body)
    assert api["replies_to_you"] == view["replies_to_you"]
    rendered = render("refresh", view=view)["elements"]
    return view, (json.dumps(view), body.decode(), json.dumps(rendered))


def test_only_joined_tony_mail_can_surface_in_state_http_or_page(community):
    allowed = "MAIL-TO-TONY\nFull reply & <literal text>"
    hidden = [f"PRIVATE-REPLY-{n}" for n in range(7)]
    write_jsonl(community.events(), [
        event("mine", "pending", sender="tony", label="plaza:my-message"),
        outcome("mine", "running"),
        outcome("mine", response_text=allowed, context_results={"response_text": hidden[0]}),
        event("other", "pending", sender="guest:levadura", label="plaza:my-message"),
        outcome("other", response_text=hidden[1]),
        event("reflection", "pending", sender=None, event_type=EVENT_TYPE_REFLECTION,
              scheduled_by_cycle=1),
        outcome("reflection", event_type=EVENT_TYPE_REFLECTION, response_text=hidden[2]),
        # Neither a completed sender nor related run/result IDs authorize a reply.
        {**outcome("orphan", response_text=hidden[3]), "sender": "tony"},
        outcome("different-event", run_id="run-mine", result_record_id="mine",
                response_text=hidden[4]),
        {"record_type": "heartbeat_status", "event_id": "mine", "status": "completed",
         "response_text": hidden[5]},
        {"record_type": "quiet_declaration", "event_id": "mine", "status": "completed",
         "response_text": hidden[6]},
    ])
    view, serialized = surfaces(community)
    assert len(view["replies_to_you"]) == 1
    reply = view["replies_to_you"][0]
    assert reply == {"door": "qwen", "event_id": "mine", "sent_at": STAMP,
                     "plaza_message_id": "my-message", "status": "completed",
                     "not_before": None, "replied_at": STAMP, "reply": allowed}
    assert all(secret not in text for secret in hidden for text in serialized)
    assert allowed in ParsedHTML(replies_html(view)).text
    assert allowed not in json.dumps(view["doors"])
    assert '"response_text"' not in serialized[0]


@pytest.mark.parametrize("sender", ["guest:tony", "door:tony", "Tony", "TONY", "tony ", " tony", "other", None])
def test_pending_sender_must_match_tony_exactly(community, sender):
    secret = "PRIVATE-NON-TONY-REPLY"
    write_jsonl(community.events(), [event("not-mine", "pending", sender=sender),
                                    outcome("not-mine", response_text=secret)])
    view, serialized = surfaces(community)
    assert view["replies_to_you"] == []
    assert all(secret not in text for text in serialized)


@pytest.mark.parametrize("status", ["pending", "running", "failed", "expired", "suppressed"])
def test_noncompleted_tony_knocks_show_status_without_response(community, status):
    secret = "PRIVATE-UNCOMPLETED-RESPONSE"
    pending = event("mine", "pending", sender="tony", response_text=secret)
    rows = [pending]
    if status != "pending":
        rows.append(outcome("mine", status, response_text=secret, error_type="RuntimeError",
                            error="Private detail must not enter the mail row"))
    write_jsonl(community.events(), rows)
    view, serialized = surfaces(community)
    reply = view["replies_to_you"][0]
    assert reply["status"] == status
    assert "reply" not in reply and "replied_at" not in reply and "error" not in reply
    if status == "failed":
        assert reply["failed_at"] == STAMP
        assert reply["error_type"] == "RuntimeError"
    assert all(secret not in text for text in serialized)


def test_duplicate_pending_recovery_keeps_one_knock_and_original_mail_metadata(community):
    original = (NOW - timedelta(hours=2)).isoformat()
    write_jsonl(community.events(), [
        event("retry", "pending", sender="tony", created_at=original,
              label="plaza:original-message", not_before=STAMP),
        outcome("retry", "running"), outcome("retry", "failed"),
        event("retry", "pending", sender="tony", recovered_by="boot-recovery",
              label="plaza:original-message", not_before=STAMP),
        event("retry", "pending", sender="tony", detail={"compact_context": True}),
        outcome("retry", "running"), outcome("retry", response_text="Recovered mail"),
    ])
    view, _ = surfaces(community)
    assert len(view["replies_to_you"]) == 1
    reply = view["replies_to_you"][0]
    assert reply["sent_at"] == original
    assert reply["plaza_message_id"] == "original-message"
    assert reply["not_before"] == STAMP
    assert reply["status"] == "completed" and reply["reply"] == "Recovered mail"


def test_repending_a_completed_event_hides_its_old_response_until_completed_again(community):
    secret = "PRIVATE-PREVIOUS-ATTEMPT"
    write_jsonl(community.events(), [event("retry", "pending", sender="tony"),
                                    outcome("retry", response_text=secret),
                                    event("retry", "pending", sender="tony", recovered_by="recovery")])
    view, serialized = surfaces(community)
    assert view["replies_to_you"][0]["status"] == "pending"
    assert "reply" not in view["replies_to_you"][0]
    assert all(secret not in text for text in serialized)


def test_shared_event_ids_cannot_authorize_another_doors_response(community):
    eid = "shared-id"
    secret = "PRIVATE-ELDER-RESPONSE"
    write_jsonl(community.events("qwen"), [event(eid, "pending", sender="tony"),
                                         outcome(eid, response_text="Qwen mail")])
    write_jsonl(community.events("elder"), [event(eid, "pending", sender="guest:levadura"),
                                          outcome(eid, response_text=secret)])
    write_jsonl(community.events("fable"), [outcome(eid, response_text=secret)])
    view, serialized = surfaces(community)
    assert [(r["door"], r["reply"]) for r in view["replies_to_you"]] == [("qwen", "Qwen mail")]
    assert all(secret not in text for text in serialized)


@pytest.mark.parametrize("surface", ["state", "http", "page"])
def test_conflicting_duplicate_pending_never_exposes_the_other_senders_reply(community, surface):
    # Supported builders + append permit ID reuse; nobody impersonates Tony.
    eid = str(uuid4())
    store = EventStore(community.events())
    write_jsonl(community.events(), [])
    store.append(build_inbound_event(purpose="Tony's knock", sender="tony", event_id=eid))
    store.append(build_inbound_event(purpose="Someone else's knock", sender="guest:levadura", event_id=eid))
    claimed, running = store.claim_next_pending(now=NOW + timedelta(days=365))
    assert claimed["sender"] == "guest:levadura"
    secret = "PRIVATE-REPLY-TO-LATEST-GUEST-PENDING"
    store.append_completed(event=claimed, run_id=running["run_id"], wake_cycle=1,
                           result_record_id=uuid4(), response_text=secret)
    if surface == "http":
        code, _, body = request(community.root, "/api/state")
        assert code == 200
        text = body.decode()
    else:
        view = state.gather(community.root, NOW)
        text = json.dumps(view) if surface == "state" else replies_html(view)
    assert secret not in text


@pytest.mark.parametrize("payload", [
    '<img src=x onerror="alert(document.domain)">',
    '</div><script>alert("xss")</script><div>',
    '<svg onload="alert(1)"></svg>',
    '&lt;img src=x onerror=alert(1)&gt; & "quotes" \'apostrophes\'',
])
def test_authorized_reply_xss_is_literal_text_through_http_and_actual_page(community, payload):
    write_jsonl(community.events(), [event("mine", "pending", sender="tony"),
                                    outcome("mine", response_text=payload)])
    code, _, body = request(community.root, "/api/state")
    assert code == 200
    view = json.loads(body)
    assert view["replies_to_you"][0]["reply"] == payload
    assert payload in assert_no_active_payload(replies_html(view)).text


def test_reply_door_event_id_and_failure_type_are_escaped():
    payload = '\"><img src=x onerror="alert(1)">'
    rows = [{"door": payload, "event_id": payload, "sent_at": STAMP,
             "status": "completed", "replied_at": STAMP, "reply": payload * 60},
            {"door": payload, "event_id": "failed", "sent_at": STAMP,
             "status": "failed", "error_type": payload}]
    html = render("renderReplies", rows, [])["elements"]["replies"]["innerHTML"]
    parsed = assert_no_active_payload(html)
    assert payload * 60 in parsed.text
    assert "Show the whole message" in parsed.text


@pytest.mark.parametrize("status, expected", [
    ("pending", "it waits until"),
    ("running", "it is awake and answering now"),
    ("failed", "the wake failed (RuntimeError)"),
])
def test_waiting_knock_status_and_current_timed_quiet(community, status, expected):
    until = (NOW + timedelta(hours=2)).isoformat()
    rows = [outcome("quiet-wake", result_record_id="quiet-cycle"),
            {"record_type": "quiet_declaration", "declared_by_record_id": "quiet-cycle",
             "declared_by_cycle": 1, "reason": "Resident's choice", "created_at": STAMP,
             "until": until},
            event("mine", "pending", sender="tony", defer_to_declared_quiet=True)]
    if status != "pending":
        rows.append(outcome("mine", status, error_type="RuntimeError"))
    write_jsonl(community.events(), rows)
    view = state.gather(community.root, NOW)
    html = replies_html(view)
    parsed = assert_no_active_payload(html)
    assert "Not answered:" in parsed.text and expected in parsed.text
    if status == "pending":
        assert "when the quiet it declared ends" in parsed.text
        # Independently format this instant through the page's timestamp title.
        # This avoids machine-specific timezone/locale expectations.
        dated = render("renderReplies", [{"door": "qwen", "event_id": "formatter",
            "status": "pending", "sent_at": until}], [])["elements"]["replies"]["innerHTML"]
        expected_date = next(value for name, value in ParsedHTML(dated).attributes if name == "title")
        assert expected_date in parsed.text
        assert "Invalid Date" not in parsed.text


@pytest.mark.parametrize("until", [None, STAMP, (NOW - timedelta(seconds=1)).isoformat()])
def test_untimed_or_elapsed_quiet_does_not_promise_a_future_end(community, until):
    write_jsonl(community.events(), [outcome("quiet-wake", result_record_id="quiet-cycle"),
        {"record_type": "quiet_declaration", "declared_by_record_id": "quiet-cycle",
         "declared_by_cycle": 1, "reason": "Quiet", "created_at": STAMP, "until": until},
        event("mine", "pending", sender="tony", defer_to_declared_quiet=True)])
    text = ParsedHTML(replies_html(state.gather(community.root, NOW))).text
    assert "it has not woken for it yet" in text
    assert "it waits until" not in text


@pytest.mark.parametrize("status", ["expired", "suppressed"])
def test_terminal_unanswered_knocks_show_their_actual_status(community, status):
    write_jsonl(community.events(), [event("mine", "pending", sender="tony"),
                                    outcome("mine", status)])
    view = state.gather(community.root, NOW)
    assert view["replies_to_you"][0]["status"] == status
    text = ParsedHTML(replies_html(view)).text.lower()
    assert status in text
    assert "it has not woken for it yet" not in text


def test_shared_ids_for_two_authorized_long_replies_have_distinct_dom_controls(community):
    for door in ("qwen", "elder"):
        write_jsonl(community.events(door), [event("shared-id", "pending", sender="tony"),
            outcome("shared-id", response_text=f"{door}'s mail " * 200)])
    view = state.gather(community.root, NOW)
    assert {r["door"] for r in view["replies_to_you"]} == {"qwen", "elder"}
    parsed = assert_no_active_payload(replies_html(view))
    ids = [value for name, value in parsed.attributes if name == "id"]
    controls = [value for name, value in parsed.attributes if name == "data-seq"]
    assert len(ids) == len(set(ids)) == 2
    assert len(controls) == len(set(controls)) == 2
    assert set(ids) == {"t" + key for key in controls}
