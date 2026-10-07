import json
import shutil
import subprocess
from html.parser import HTMLParser
from pathlib import Path

import pytest

from hamutay.viewer import state
from hamutay.viewer.__main__ import PAGE

from .conftest import NOW, STAMP, event, message, question, write_jsonl

NODE = shutil.which("node")
HARNESS = Path(__file__).with_name("render_page.js")


class ParsedHTML(HTMLParser):
    def __init__(self, html):
        super().__init__(convert_charrefs=True)
        self.tags, self.attributes, self.data = [], [], []
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        self.tags.append(tag)
        self.attributes.extend(attrs)

    def handle_data(self, data):
        self.data.append(data)

    @property
    def text(self):
        return "".join(self.data)


def render(operation, *args, view=None):
    assert NODE is not None, "Node is required to execute page.html's actual JavaScript"
    result = subprocess.run([NODE, str(HARNESS)],
        input=json.dumps({"page": str(PAGE), "operation": operation, "args": args,
                          "state": view, "now": STAMP}),
        text=True, capture_output=True, timeout=10)
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


def assert_no_active_payload(html):
    parsed = ParsedHTML(html)
    assert not set(parsed.tags) & {"script", "img", "svg", "iframe", "object", "embed"}
    assert not [name for name, _ in parsed.attributes if name.lower().startswith("on")]
    assert not [value for name, value in parsed.attributes
                if name in ("href", "src") and value and value.lower().startswith("javascript:")]
    return parsed


@pytest.mark.parametrize("payload", [
    '<img src=x onerror="alert(document.domain)">',
    '</div><script>alert("xss")</script><div>',
    '<svg onload="alert(1)"></svg>',
    '&lt;img src=x onerror=alert(1)&gt; & "quotes" \'apostrophes\'',
])
def test_actual_untrusted_plaza_text_is_rendered_as_literal_text(community, payload):
    write_jsonl(community.cfg.plaza, [message(1, text=payload)])
    view = state.gather(community.root, NOW)
    html = render("renderPlaza", view["plaza"], view["plaza_error"])["elements"]["plaza"]["innerHTML"]
    parsed = assert_no_active_payload(html)
    assert payload in parsed.text


def test_plaza_actor_recipient_truth_and_error_are_escaped():
    payload = '<img src=x onerror="alert(1)">'
    row = {"seq": 1, "from": "guest:" + payload, "to": "door:" + payload,
           "text": "Body", "sent_at": STAMP, "truth": {"state": payload}}
    html = render("renderPlaza", [row], None)["elements"]["plaza"]["innerHTML"]
    parsed = assert_no_active_payload(html)
    assert parsed.text.count(payload) == 3
    html = render("renderPlaza", [], payload)["elements"]["plaza"]["innerHTML"]
    assert payload in assert_no_active_payload(html).text


def test_door_name_rest_reason_and_guest_labels_are_escaped(community):
    view = state.gather(community.root, NOW)
    payload = '\"><img src=x onerror="alert(1)">'
    view["doors"][0]["name"] = payload
    view["doors"][0]["now_status"] = {"status": "resting", "reason": payload, "created_at": STAMP}
    view["guests"] = [payload]
    result = render("refresh", view=view)["elements"]
    assert payload in assert_no_active_payload(result["doors"]["innerHTML"]).text
    assert payload in assert_no_active_payload(result["guests"]["innerHTML"]).text


def test_assembly_public_strings_are_escaped(community):
    view = state.gather(community.root, NOW)
    payload = '<img src=x onerror="alert(1)">'
    q = view["assembly"][0]
    q["text"] = payload
    q["convener"] = payload
    q["positions"][0]["member"] = payload
    q["positions"][0]["stance"] = payload
    q["closing"]["outcome"] = payload
    html = render("renderAssembly", view["assembly"])["elements"]["assembly"]["innerHTML"]
    assert assert_no_active_payload(html).text.count(payload) >= 5


def test_untrusted_assembly_sequence_cannot_inject_html(community):
    payload = '<img src=x onerror="alert(document.domain)">'
    write_jsonl(community.cfg.ledger, [question(seq=payload)])
    view = state.gather(community.root, NOW)
    html = render("renderAssembly", view["assembly"])["elements"]["assembly"]["innerHTML"]
    assert_no_active_payload(html)


@pytest.mark.parametrize("expected", [
    "Second public line", "Public position reasons", "Public testimony body", "Public execution details",
])
def test_page_shows_the_public_assembly_content_it_promises(community, expected):
    view = state.gather(community.root, NOW)
    html = render("refresh", view=view)["elements"]["assembly"]["innerHTML"]
    assert expected in ParsedHTML(html).text


def test_page_shows_failed_wake_error_metadata(community):
    write_jsonl(community.events(), [event("failed", "failed", error_type="RuntimeError",
                                         error="Public failure details")])
    view = state.gather(community.root, NOW)
    html = render("refresh", view=view)["elements"]["doors"]["innerHTML"]
    assert "Public failure details" in ParsedHTML(html).text


def test_page_shows_full_public_plaza_body_and_expand_control(community):
    body = "First public line\n" + "Long public content & <literal>. " * 60 + "\nLast public line"
    write_jsonl(community.cfg.plaza, [message(1, text=body), message(2, text="Newest public post")])
    view = state.gather(community.root, NOW)
    html = render("refresh", view=view)["elements"]["plaza"]["innerHTML"]
    parsed = assert_no_active_payload(html)
    assert body in parsed.text
    assert parsed.text.index("Newest public post") < parsed.text.index("First public line")
    assert "Show the whole message" in parsed.text
    assert ("data-seq", "1") in parsed.attributes
