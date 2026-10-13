"""The 2026-10-13 viewer contract, executed against the shipped page script.

The checkout intentionally contains the old page. Missing new behavior fails
normally; expectations come from the contract, not a replacement renderer.
"""

import json
import re
import subprocess
from datetime import timedelta
from html.parser import HTMLParser

import pytest

from hamutay.viewer.__main__ import PAGE

from .conftest import NOW, STAMP
from .test_page import HARNESS, NODE, assert_no_active_payload

COUNTERS = ("nav-replies", "nav-plaza", "nav-assembly")
DAY = 86400


class Element:
    def __init__(self, tag, attrs=(), parent=None):
        self.tag, self.attrs, self.parent = tag, dict(attrs), parent
        self.children = []

    @property
    def classes(self):
        return self.attrs.get("class", "").split()

    @property
    def text(self):
        return "".join(child if isinstance(child, str) else child.text
                       for child in self.children)

    def descendants(self, tag=None):
        for child in self.children:
            if isinstance(child, Element):
                if tag is None or child.tag == tag:
                    yield child
                yield from child.descendants(tag)

    def ancestors(self):
        parent = self.parent
        while parent is not None:
            yield parent
            parent = parent.parent

    @property
    def markup(self):
        # Ignore insignificant formatting whitespace, retain content/attributes.
        return (self.tag, tuple(sorted(self.attrs.items())), tuple(
            child.markup if isinstance(child, Element) else child
            for child in self.children
            if isinstance(child, Element) or child.strip()))


class HTMLTree(HTMLParser):
    VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input",
            "link", "meta", "param", "source", "track", "wbr"}

    def __init__(self, html):
        super().__init__(convert_charrefs=True)
        self.root = Element("root")
        self.stack = [self.root]
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        node = Element(tag, attrs, self.stack[-1])
        self.stack[-1].children.append(node)
        if tag not in self.VOID:
            self.stack.append(node)

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag not in self.VOID:
            self.handle_endtag(tag)

    def handle_endtag(self, tag):
        for index in range(len(self.stack) - 1, 0, -1):
            if self.stack[index].tag == tag:
                del self.stack[index:]
                break

    def handle_data(self, data):
        self.stack[-1].children.append(data)

    def by_id(self, target):
        matches = [node for node in self.root.descendants()
                   if node.attrs.get("id") == target]
        assert len(matches) == 1, f"Expected one static #{target}, found {len(matches)}"
        return matches[0]


def sections_nav(tree):
    matches = [node for node in tree.root.descendants("nav")
               if node.attrs.get("aria-label") == "Sections"]
    assert len(matches) == 1, "Expected one <nav aria-label=Sections> landmark"
    return matches[0]


def test_sections_nav_follows_header_precedes_doors_and_links_in_order():
    tree = HTMLTree(PAGE.read_text())
    nav = sections_nav(tree)
    headers = list(tree.root.descendants("header"))
    assert headers, "Expected a static header"
    doors = tree.by_id("doors")
    assert doors.tag == "section"
    nodes = list(tree.root.descendants())
    assert nodes.index(headers[0]) < nodes.index(nav) < nodes.index(doors)
    assert headers[0] not in list(nav.ancestors())
    assert nav not in list(doors.ancestors())
    assert [node.attrs.get("href") for node in nav.descendants("a")] == [
        "#doors", "#replies-h", "#plaza-h", "#assembly-h"]


@pytest.mark.parametrize("target, text", [
    ("replies-h", "Replies to you"),
    ("plaza-h", "The plaza"),
    ("assembly-h", "The assembly"),
])
def test_static_section_heading_is_a_unique_fragment_target(target, text):
    heading = HTMLTree(PAGE.read_text()).by_id(target)
    assert heading.tag == "h3"
    assert " ".join(heading.text.split()) == text


@pytest.mark.parametrize("target", COUNTERS)
def test_counter_exists_in_static_sections_nav(target):
    tree = HTMLTree(PAGE.read_text())
    counter = tree.by_id(target)
    assert sections_nav(tree) in list(counter.ancestors())


def compound_matches(node, selector):
    """Match ordinary type/class/id/attribute CSS selectors without a browser."""
    attrs = re.findall(r'\[([\w-]+)(?:=["\']?([^\]"\']+)["\']?)?\]', selector)
    remainder = re.sub(r'\[[^\]]+\]', '', selector)
    # State-dependent and pseudo-element rules cannot establish base stickiness.
    if ":" in remainder:
        return False
    tag = re.match(r"^[\w*-]+", remainder)
    if tag and tag[0] not in ("*", node.tag):
        return False
    if any(value != node.attrs.get("id") for value in re.findall(r"#([\w-]+)", remainder)):
        return False
    if any(value not in node.classes for value in re.findall(r"\.([\w-]+)", remainder)):
        return False
    return all(key in node.attrs and (not value or node.attrs[key] == value)
               for key, value in attrs)


def selector_matches(node, selector):
    # Covers ordinary descendant and child rules, including .wrap > nav.
    pieces = re.split(r"\s*(>)\s*|\s+", selector.strip())
    pieces = [piece for piece in pieces if piece]
    if not pieces or not compound_matches(node, pieces[-1]):
        return False
    if len(pieces) == 1:
        return True
    if pieces[-2] == ">":
        return node.parent is not None and selector_matches(node.parent, " ".join(pieces[:-2]))
    return any(selector_matches(parent, " ".join(pieces[:-1])) for parent in node.ancestors())


def test_sections_nav_has_sticky_position_in_stylesheet():
    tree = HTMLTree(PAGE.read_text())
    nav = sections_nav(tree)
    css = "\n".join(node.text for node in tree.root.descendants("style"))
    css = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
    rules = re.findall(r"([^{}]+)\{([^{}]*)\}", css)
    assert any(re.search(r"(?:^|;)\s*position\s*:\s*sticky\s*(?:!important\s*)?(?:;|$)", body)
               and any(selector_matches(nav, selector) for selector in selectors.split(","))
               for selectors, body in rules), "No stylesheet rule positions the Sections nav sticky"


def run_page(operation="refresh", *args, states=None, storage=None, clicks=None):
    assert NODE is not None, "Node is required to execute page.html's actual JavaScript"
    result = subprocess.run([NODE, str(HARNESS)], input=json.dumps({
        "page": str(PAGE), "operation": operation, "args": args, "now": STAMP,
        "refreshStates": states, "localStorage": storage or {},
        "clicks": clicks or [],
    }), text=True, capture_output=True, timeout=10)
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


def view(*, replies=(), plaza=(), assembly=()):
    return {"doors": [], "guests": [], "replies_to_you": list(replies),
            "plaza": list(plaza), "plaza_error": None, "plaza_skipped": 0,
            "assembly": list(assembly)}


def reply(index, age=0, **fields):
    row = {"door": "qwen", "event_id": f"event-{index}", "status": "completed",
           "sent_at": (NOW - timedelta(seconds=age)).isoformat(),
           "replied_at": STAMP, "reply": f"BODY-{index}-END"}
    row.update(fields)
    return row


def plaza_row(seq):
    return {"seq": seq, "from": "tony", "to": "plaza", "text": "Public post",
            "sent_at": STAMP, "truth": None}


def assembly_row(seq, closing=None):
    return {"seq": seq, "text": "A public question", "convener": "tony",
            "closes_at": STAMP, "round": 1, "positions": [], "testimony": [],
            "closing": closing, "execution": None}


def counter_text(elements, target):
    assert target in elements, f"Refresh did not update #{target}"
    return elements[target]["textContent"]


@pytest.mark.parametrize("statuses, expected", [
    ([], "(0)"),
    (["completed"], "(1)"),
    (["completed", "completed", "completed", "completed"], "(4)"),
    (["completed", "pending", "running", "failed", "expired", "suppressed", "other"],
     "(7, 6 not answered)"),
    (["pending"], "(1, 1 not answered)"),
], ids=["empty", "one-completed", "counts-folded-rows", "all-noncompleted-statuses", "one-unanswered"])
def test_refresh_counts_all_replies_and_every_noncompleted_status(statuses, expected):
    rows = [reply(i, (10 + i) * DAY, status=status) for i, status in enumerate(statuses)]
    result = run_page(states=[view(replies=rows)])
    assert counter_text(result["elements"], "nav-replies") == expected


@pytest.mark.parametrize("seqs, seen, expected", [
    ([], "8", ""),
    ([2, 10, 40], "10", "(seq 40, 1 new)"),
    ([2, 10, 40], "40", "(seq 40)"),
    ([2, 10, 40], "100", "(seq 40)"),
    ([2, 10, 40], None, "(seq 40, 3 new)"),
    ([2, 10, 40], "0", "(seq 40, 3 new)"),
    ([40, 10, 20], "10", "(seq 20, 2 new)"),
], ids=["empty", "strict-gapped-cursor", "all-seen", "cursor-ahead", "missing-cursor",
        "zero-cursor", "last-row-not-maximum"])
def test_refresh_plaza_uses_last_row_seq_and_counts_rows_above_loaded_cursor(seqs, seen, expected):
    storage = {} if seen is None else {"ayllu.lastSeenSeq": seen}
    result = run_page(states=[view(plaza=[plaza_row(seq) for seq in seqs])], storage=storage)
    assert counter_text(result["elements"], "nav-plaza") == expected


@pytest.mark.parametrize("closings, expected", [
    ([], ""),
    ([None], "(1 open)"),
    ([{"closed_at": STAMP, "outcome": "assented"}], ""),
    ([None, {"closed_at": STAMP, "outcome": "dissented"}, None], "(2 open)"),
], ids=["empty", "one-open", "all-closed", "mixed"])
def test_refresh_assembly_counts_only_questions_without_closing(closings, expected):
    result = run_page(states=[view(assembly=[assembly_row(i, closing)
                                           for i, closing in enumerate(closings)])])
    assert counter_text(result["elements"], "nav-assembly") == expected


def test_refresh_counters_use_textcontent_even_for_html_in_state():
    payload = '<img src=x onerror="alert(1)"> & <script>boom</script>'
    result = run_page(states=[view(replies=[reply(0, reply=payload)],
                                  plaza=[plaza_row(payload)], assembly=[assembly_row(1)])])
    for target, expected in zip(COUNTERS, ["(1)", f"(seq {payload})", "(1 open)"]):
        writes = [write for write in result["assignments"] if write["id"] == target]
        assert writes, f"No counter assignment to #{target}"
        assert all(write["property"] == "textContent" for write in writes), writes
        assert counter_text(result["elements"], target) == expected
        assert result["elements"][target]["innerHTML"] == ""


def test_successive_refreshes_clear_stale_counts():
    first = view(replies=[reply(0, status="pending")], plaza=[plaza_row(3)],
                 assembly=[assembly_row(1)])
    result = run_page(states=[first, view()])
    actual = [tuple(counter_text(snapshot, target) for target in COUNTERS)
              for snapshot in result["snapshots"]]
    assert actual == [("(1, 1 not answered)", "(seq 3, 1 new)", "(1 open)"),
                      ("(0)", "", "")]
    for target in COUNTERS:
        writes = [write for write in result["assignments"] if write["id"] == target]
        assert len(writes) >= 2
        assert all(write["property"] == "textContent" for write in writes)


def test_successive_refreshes_keep_cursor_read_at_page_load():
    first = view(plaza=[plaza_row(2), plaza_row(5), plaza_row(9)])
    second = view(plaza=[plaza_row(2), plaza_row(5), plaza_row(9), plaza_row(12)])
    result = run_page(states=[first, second], storage={"ayllu.lastSeenSeq": "5"})
    assert [counter_text(snapshot, "nav-plaza") for snapshot in result["snapshots"]] == [
        "(seq 9, 1 new)", "(seq 12, 2 new)"]
    # Real setItem persists in the harness, so re-reading it would hide row 9.
    assert ["ayllu.lastSeenSeq", "9"] in result["writes"]


def rendered_replies(rows, doors=()):
    result = run_page("renderReplies", rows, list(doors))
    html = result["elements"]["replies"]["innerHTML"]
    assert_no_active_payload(html)
    return HTMLTree(html)


def older_details(tree):
    return [node for node in tree.root.descendants("details") if "older" in node.classes]


def articles(tree):
    return [node for node in tree.root.descendants("article") if "reply" in node.classes]


@pytest.mark.parametrize("ages, kept, folded", [
    ([], 0, 0),
    ([10 * DAY], 1, 0),
    ([10 * DAY, 11 * DAY], 2, 0),
    ([10 * DAY, 11 * DAY, 12 * DAY], 3, 0),
    ([10 * DAY, 11 * DAY, 12 * DAY, 13 * DAY], 3, 1),
    ([DAY, 2 * DAY, 3 * DAY, 4 * DAY, 6 * DAY], 5, 0),
    ([DAY, 2 * DAY, 3 * DAY, 7 * DAY - 1, 8 * DAY], 4, 1),
    ([DAY, 2 * DAY, 3 * DAY, 7 * DAY, 8 * DAY], 3, 2),
    ([DAY, 2 * DAY, 3 * DAY, 7 * DAY + 1, 8 * DAY], 3, 2),
    ([7 * DAY, 8 * DAY, 9 * DAY, 10 * DAY, 11 * DAY, 12 * DAY], 3, 3),
], ids=["empty", "one-old", "two-old", "three-old", "four-old", "all-recent",
        "one-second-inside", "exact-cutoff", "one-second-outside", "many-old"])
def test_reply_folding_keeps_leading_three_or_recent_rows_without_dropping_any(ages, kept, folded):
    rows = [reply(i, age) for i, age in enumerate(ages)]
    tree = rendered_replies(rows)
    details = older_details(tree)
    rendered = articles(tree)
    assert len(rendered) == len(rows), "Folding must never drop a reply"
    assert [node.text.count(f"BODY-{i}-END") for i, node in enumerate(rendered)] == [1] * len(rows)
    assert len(details) == (1 if folded else 0)
    open_rows = [node for node in rendered if not any(parent.tag == "details"
                                                     for parent in node.ancestors())]
    assert open_rows == rendered[:kept]
    if folded:
        assert "open" not in details[0].attrs
        assert list(details[0].descendants("article")) == rendered[kept:]
        assert not list(details[0].descendants("details")), "Use one fold, not a fold per row"


@pytest.mark.parametrize("tail_ages, expected", [
    ([8 * DAY], "1 older reply, the oldest 8 days ago"),
    ([8 * DAY, 30 * DAY], "2 older replies, the oldest 30 days ago"),
    ([8 * DAY, 10 * DAY, 400 * DAY], "3 older replies, the oldest 400 days ago"),
], ids=["singular", "plural-last-row", "many-last-row"])
def test_older_summary_uses_folded_count_and_last_rows_relative_age(tail_ages, expected):
    rows = [reply(i, age) for i, age in enumerate([DAY, 2 * DAY, 3 * DAY, *tail_ages])]
    details = older_details(rendered_replies(rows))
    assert len(details) == 1, "Expected one details.older containing the tail"
    summaries = list(details[0].descendants("summary"))
    assert len(summaries) == 1
    assert summaries[0].parent is details[0]
    assert " ".join(summaries[0].text.split()) == expected


def test_folded_replies_preserve_row_markup_escaping_and_long_message_controls():
    payload = '\"><img src=x onerror="alert(1)"> & <script>boom</script>'
    tail = [reply(3, 8 * DAY, door=payload, event_id=payload, reply=payload * 60),
            reply(4, 9 * DAY, door="elder", reply="Full multiline mail\n" + "long & <literal> " * 150)]
    rows = [reply(i, (i + 1) * DAY) for i in range(3)] + tail
    tree = rendered_replies(rows)
    # Assert preservation even on the old page before checking the missing fold.
    rendered = articles(tree)
    assert len(rendered) == 5
    for row, article in zip(tail, rendered[3:]):
        assert row["reply"] in article.text
        assert article.markup == articles(rendered_replies([row]))[0].markup
        texts = [node for node in article.descendants("div") if "text" in node.classes]
        buttons = list(article.descendants("button"))
        assert len(texts) == len(buttons) == 1
        assert "clamped" in texts[0].classes
        assert buttons[0].text == "Show the whole message"
        assert texts[0].attrs["id"] == "t" + buttons[0].attrs["data-seq"]
    assert len({node.attrs["id"] for article in rendered[3:]
                for node in article.descendants() if "id" in node.attrs}) == 2
    details = older_details(tree)
    assert len(details) == 1
    assert list(details[0].descendants("article")) == rendered[3:]


def test_folded_long_reply_toggle_expands_collapses_and_survives_rerender():
    rows = [reply(i, (i + 1) * DAY) for i in range(3)] + [reply(3, 8 * DAY, reply="Long & <literal> " * 150)]
    initial = articles(rendered_replies(rows))[-1]
    button = list(initial.descendants("button"))[0]
    text = next(node for node in initial.descendants("div") if "text" in node.classes)
    click = {"key": button.attrs["data-seq"], "textId": text.attrs["id"],
             "classes": text.classes, "label": button.text}
    result = run_page("renderReplies", rows, [], clicks=[click, click])
    assert [(action["label"], action["clamped"]) for action in result["clickResults"]] == [
        ("Show less", False), ("Show the whole message", True)]
    for snapshot, clamped, label in zip(result["snapshots"],
                                        [True, False, True],
                                        ["Show the whole message", "Show less", "Show the whole message"]):
        tree = HTMLTree(snapshot["replies"]["innerHTML"])
        article = articles(tree)[-1]
        assert rows[-1]["reply"] in article.text
        content = next(node for node in article.descendants("div") if "text" in node.classes)
        assert ("clamped" in content.classes) == clamped
        assert list(article.descendants("button"))[0].text == label
    # Every render must keep the row inside the single older-replies fold.
    for snapshot in result["snapshots"]:
        tree = HTMLTree(snapshot["replies"]["innerHTML"])
        details = older_details(tree)
        assert len(details) == 1
        assert list(details[0].descendants("article")) == articles(tree)[3:]


@pytest.mark.parametrize("status, quiet, expected", [
    ("pending", None, "it has not woken for it yet"),
    ("pending", STAMP, "it has not woken for it yet"),
    ("pending", (NOW + timedelta(hours=2)).isoformat(), "when the quiet it declared ends"),
    ("running", (NOW + timedelta(hours=2)).isoformat(), "it is awake and answering now"),
    ("failed", (NOW + timedelta(hours=2)).isoformat(), "the wake failed"),
    ("expired", None, "the knock ended without a reply (expired)"),
    ("suppressed", None, "the knock ended without a reply (suppressed)"),
], ids=["pending", "elapsed-quiet", "future-quiet", "running", "failed", "expired", "suppressed"])
def test_folded_unanswered_rows_keep_waiting_failed_and_quiet_texts(status, quiet, expected):
    payload = '<svg onload="alert(1)"></svg> & literal error'
    tail = reply(3, 8 * DAY, status=status, error_type=payload)
    doors = [{"name": "qwen", "quiet": {"until": quiet}}]
    tree = rendered_replies([reply(i, (i + 1) * DAY) for i in range(3)] + [tail], doors)
    article = articles(tree)[-1]
    assert "waiting" in article.classes
    assert "Not answered:" in article.text and expected in article.text
    if status == "failed":
        assert payload in article.text
    assert article.markup == articles(rendered_replies([tail], doors))[0].markup
    details = older_details(tree)
    assert len(details) == 1
    assert list(details[0].descendants("article")) == [article]
