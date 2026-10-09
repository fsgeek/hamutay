"""Names-only viewer projections and actual bundled-page rendering."""

import io
import json
from html.parser import HTMLParser
from pathlib import Path
import shutil
import subprocess

import pytest

from hamutay import events
from hamutay.viewer import __main__ as viewer
from hamutay.viewer import state

from .helpers import (
    CLEAN, LEAK, NOW, SENTINEL, expected_note, leaked, notes, pending,
    persisted_completion, session_and_store, status, turn,
)


NODE = shutil.which("node")
HARNESS = Path(__file__).parents[1] / "validation_viewer" / "render_page.js"


class ParsedHTML(HTMLParser):
    def __init__(self, html):
        super().__init__(convert_charrefs=True)
        self.data = []
        self.tags = []
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        self.tags.append(tag)

    def handle_data(self, data):
        self.data.append(data)

    @property
    def text(self):
        return "".join(self.data)


def render(view):
    assert NODE is not None, "Node is required for the actual page JavaScript"
    result = subprocess.run(
        [NODE, str(HARNESS)],
        input=json.dumps({"page": str(viewer.PAGE), "operation": "refresh", "args": [],
                          "state": view, "now": NOW.isoformat()}),
        text=True, capture_output=True, timeout=10,
    )
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)["elements"]


class MemoryConnection:
    def __init__(self):
        self.request = io.BytesIO(b"GET /api/state HTTP/1.0\r\nHost: localhost\r\n\r\n")
        self.response = bytearray()

    def makefile(self, mode, buffering=None):
        assert mode == "rb"
        return self.request

    def sendall(self, data):
        self.response.extend(data)


def api_state(root):
    connection = MemoryConnection()
    viewer.make_handler(root)(connection, ("127.0.0.1", 43210), object())
    head, body = bytes(connection.response).split(b"\r\n\r\n", 1)
    assert int(head.splitlines()[0].split()[1]) == 200
    return json.loads(body)


def configure_community(root):
    plaza = root / "community" / "plaza"
    plaza.mkdir(parents=True)
    (plaza / "members.json").write_text(json.dumps({
        "ledger": "community/plaza/assembly.jsonl", "plaza": "community/plaza/plaza.jsonl",
        "guests": [], "members": {"qwen": {"session": "session.jsonl", "events": "events.jsonl"}},
    }))
    (plaza / "assembly.jsonl").write_text("")
    (plaza / "plaza.jsonl").write_text("")
    return root / "events.jsonl"


@pytest.fixture
def community(tmp_path):
    return tmp_path, configure_community(tmp_path)


def write_rows(path, rows):
    path.write_text("".join(json.dumps(row) + "\n" for row in rows))


def mail_rows(row, sender="tony"):
    return [status("pending", row["event_id"], sender=sender, label="plaza:validation-mail"), row]


@pytest.mark.parametrize("names", [("send_message",), ("send_message", "update_state", "send_message")])
def test_04_viewer_projects_names_on_wakes_last_wake_and_tony_reply(community, names):
    """4/Interface: Every new viewer field is a list of names, never call dicts."""
    root, path = community
    row = leaked(names=names)
    write_rows(path, mail_rows(row))
    vitals = state.door_vitals("qwen", path, NOW)
    assert vitals["wakes"][0]["unexecuted_tool_calls"] == list(names)
    assert vitals["last_wake"]["unexecuted_tool_calls"] == list(names)
    replies = state.replies_to("tony", "qwen", path, NOW)
    assert len(replies) == 1
    assert replies[0]["unexecuted_tool_calls"] == list(names)
    assert replies[0]["reply"] == LEAK
    assert SENTINEL not in json.dumps(vitals)


def test_04_page_marks_card_and_marks_above_tony_reply(community):
    """4: Execute the shipped JS with the exact viewer interface, independent of projection."""
    root, path = community
    row = leaked()
    write_rows(path, mail_rows(row))
    view = state.gather(root, NOW)
    # Supply the fixed interface directly, so a projection failure cannot hide
    # a separate page failure. The projection is checked in its own test.
    view["doors"][0]["last_wake"]["unexecuted_tool_calls"] = ["send_message"]
    view["doors"][0]["wakes"][0]["unexecuted_tool_calls"] = ["send_message"]
    view["replies_to_you"][0]["unexecuted_tool_calls"] = ["send_message"]
    rendered = render(view)
    card = ParsedHTML(rendered["doors"]["innerHTML"])
    reply = ParsedHTML(rendered["replies"]["innerHTML"])
    mark = "ended with an unexecuted send_message"
    assert mark in card.text
    assert SENTINEL not in card.text
    assert mark in reply.text
    assert reply.text.index(mark) < reply.text.index(LEAK)
    assert LEAK in reply.text
    assert not {"tool_call", "function", "parameter", "think"} & set(reply.tags)


def test_06_viewer_does_not_scan_historical_response_text(community):
    """6/4: Old XML mail stays visible but neither API nor page adds a mark."""
    root, path = community
    row = status("completed", response_text=LEAK, response_state_mismatch=True)
    write_rows(path, mail_rows(row))
    view = state.gather(root, NOW)
    door, reply = view["doors"][0], view["replies_to_you"][0]
    assert "unexecuted_tool_calls" not in door["last_wake"]
    assert "unexecuted_tool_calls" not in door["wakes"][0]
    assert "unexecuted_tool_calls" not in reply
    rendered = render(view)
    assert "ended with an unexecuted" not in ParsedHTML(rendered["doors"]["innerHTML"]).text
    reply_text = ParsedHTML(rendered["replies"]["innerHTML"]).text
    assert "ended with an unexecuted" not in reply_text
    assert LEAK in reply_text


def test_04_clean_wake_and_uncompleted_reply_have_no_mark(community):
    """4/6: Only a completed reply carries the new reply marker."""
    root, path = community
    write_rows(path, [
        status("pending", "clean", sender="tony"),
        status("completed", "clean", response_text=CLEAN),
        status("pending", "waiting", sender="tony", unexecuted_tool_calls=[{"function": "send_message"}]),
    ])
    view = state.gather(root, NOW)
    assert "unexecuted_tool_calls" not in view["doors"][0]["last_wake"]
    assert all("unexecuted_tool_calls" not in reply for reply in view["replies_to_you"])
    rendered = render(view)
    assert "ended with an unexecuted" not in ParsedHTML(rendered["doors"]["innerHTML"]).text
    assert "ended with an unexecuted" not in ParsedHTML(rendered["replies"]["innerHTML"]).text


def test_10_sentinel_stays_out_of_new_surfaces_but_full_tony_reply_is_unchanged(tmp_path, monkeypatch):
    """10: Real completion → notes → state/API → page; preserve addressee's mail."""
    configure_community(tmp_path)
    session, store, transport, _, _ = session_and_store(tmp_path, monkeypatch, [turn(LEAK)])
    pending(store)
    result = events.run_next_event(session, store, now=NOW)
    row, rows = persisted_completion(store, result["run_id"])
    assert row["response_text"] == LEAK and SENTINEL in row["response_text"]
    fields = {key: row[key] for key in ("unexecuted_tool_calls", "final_turn")}
    assert fields == {"unexecuted_tool_calls": [{"function": "send_message"}],
                      "final_turn": {"tools_offered": True, "all_tools_withdrawn": False}}
    assert SENTINEL not in json.dumps(fields)
    rebuilt = notes(rows)
    assert rebuilt == [expected_note(row)] and SENTINEL not in "\n".join(rebuilt)
    view = state.gather(tmp_path, NOW)
    api = api_state(tmp_path)
    # The HTTP endpoint uses wall time; week/quiet summaries may differ from
    # the fixed-time fixture. The new projections are independent of that.
    assert api["doors"][0]["last_wake"] == view["doors"][0]["last_wake"]
    assert api["doors"][0]["wakes"] == view["doors"][0]["wakes"]
    assert api["replies_to_you"] == view["replies_to_you"]
    # The whole API contains Tony's mail by design. Inspect the marker payload
    # and complete door projection separately from that declared exposure.
    for payload in (view, api):
        door, reply = payload["doors"][0], payload["replies_to_you"][0]
        assert SENTINEL not in json.dumps(door)
        assert door["last_wake"]["unexecuted_tool_calls"] == ["send_message"]
        assert reply["unexecuted_tool_calls"] == ["send_message"]
        assert SENTINEL not in json.dumps(reply["unexecuted_tool_calls"])
        assert reply["reply"] == LEAK
        assert SENTINEL not in json.dumps({k: v for k, v in reply.items() if k != "reply"})
    rendered = render(view)
    card = ParsedHTML(rendered["doors"]["innerHTML"]).text
    reply = ParsedHTML(rendered["replies"]["innerHTML"]).text
    mark = "ended with an unexecuted send_message"
    assert mark in card and SENTINEL not in card
    assert mark in reply and reply.index(mark) < reply.index(LEAK)
    assert LEAK in reply and reply.count(SENTINEL) == LEAK.count(SENTINEL)
    assert SENTINEL not in reply[:reply.index(LEAK)]
    assert not transport.script


def test_10_other_addressees_receive_only_parameter_free_marks(community):
    """10/4: A public card mark cannot expose another addressee's parameter text."""
    root, path = community
    row = leaked()
    write_rows(path, mail_rows(row, sender="guest:visitor"))
    view, api = state.gather(root, NOW), api_state(root)
    for payload in (view, api):
        assert payload["replies_to_you"] == []
        assert SENTINEL not in json.dumps(payload)
        assert payload["doors"][0]["last_wake"]["unexecuted_tool_calls"] == ["send_message"]
    card = ParsedHTML(render(view)["doors"]["innerHTML"]).text
    assert "ended with an unexecuted send_message" in card
    assert SENTINEL not in card
