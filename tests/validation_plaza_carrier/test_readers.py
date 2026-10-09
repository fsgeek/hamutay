"""Spec test 6: disk -> projection -> shipped JavaScript, notes, wake events."""
import json
import shutil
import subprocess
from html.parser import HTMLParser

from hamutay.plaza.event import inbound_event_for
from hamutay.plaza.note import plaza_note
from hamutay.viewer import state
from hamutay.viewer.__main__ import PAGE
from tests.plaza.conftest import T0

from .helpers import REPO, STAMP, cli, message, write_rows


class Rendered(HTMLParser):
    def __init__(self, html):
        super().__init__(convert_charrefs=True)
        self.tags, self.attrs, self.texts = [], [], []
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        self.tags.append(tag)
        self.attrs.extend(attrs)

    def handle_data(self, data):
        self.texts.append(data)


def test_stored_carrier_projects_and_renders_beside_speaker_as_literal_text(house_guests):
    root, cfg, _ = house_guests
    payload = '<img src=x onerror="alert(1)"> & "carrier"'
    write_rows(cfg.plaza, [message(carrier=payload, text="body-sentinel"),
                           message(2, text="legacy-body")])
    view = state.gather(root, T0)
    assert not view["plaza_error"]
    assert view["plaza"][0]["carrier"] == payload
    # The projection promises presence for carrier records, without prescribing
    # whether a legacy dict omits the key or represents absence as None.
    assert view["plaza"][1].get("carrier") is None
    node = shutil.which("node")
    assert node, "Node is required for the real viewer JavaScript"
    result = subprocess.run([node, str(REPO / "tests/validation_viewer/render_page.js")],
                            input=json.dumps({"page": str(PAGE), "operation": "renderPlaza",
                                              "args": [view["plaza"], view["plaza_error"]], "now": STAMP}),
                            capture_output=True, text=True, timeout=10)
    assert result.returncode == 0, result.stderr
    html = json.loads(result.stdout)["elements"]["plaza"]["innerHTML"]
    parsed = Rendered(html)
    rendered = "".join(parsed.texts)
    assert payload in rendered
    # The label must accompany the speaker, before that post's message body.
    assert rendered.index("guest:levadura") < rendered.index(payload) < rendered.index("body-sentinel")
    assert not set(parsed.tags) & {"img", "script", "svg", "iframe", "object", "embed"}
    assert not [n for n, _ in parsed.attrs if n.lower().startswith("on")]


def test_cli_overview_appends_carrier_to_speaker_when_present(house_guests):
    root, cfg, _ = house_guests
    write_rows(cfg.plaza, [message(carrier="named-carrier", text="named-post"),
                           message(2, text="legacy-post")])
    result = cli(root)
    assert result.returncode == 0, result.stderr
    lines = result.stdout.splitlines()
    named, = [line for line in lines if "named-post" in line]
    legacy, = [line for line in lines if "legacy-post" in line]
    assert "guest:levadura (named-carrier)" in named
    assert "guest:levadura" in legacy and "(named-carrier)" not in legacy


def test_per_wake_note_is_byte_identical_with_and_without_carrier(house):
    _, cfg, _ = house
    rows = [message(), message(2, cfg=cfg, to="door:elder")]
    write_rows(cfg.plaza, rows)
    before = plaza_note(cfg, "qwen", [])
    assert before
    rows[0]["carrier"] = "one"
    rows[1]["carrier"] = "two"
    write_rows(cfg.plaza, rows)
    after = plaza_note(cfg, "qwen", [])
    assert json.dumps(after).encode() == json.dumps(before).encode()


def test_directed_wake_event_is_identical_and_contains_no_carrier(house):
    _, cfg, _ = house
    row = message(cfg=cfg, to="door:elder")
    before = inbound_event_for(row)
    row["carrier"] = "carrier-sentinel"
    after = inbound_event_for(row)
    assert after == before
    assert "carrier" not in after
    assert "carrier-sentinel" not in json.dumps(after)
