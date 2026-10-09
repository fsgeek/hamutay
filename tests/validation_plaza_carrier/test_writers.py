"""Spec tests 3–5: registered MCP, CLI parsing, pre-lock refusal, idempotency."""
import asyncio
import json

import pytest

from hamutay.assembly.ledger import Ledger
from hamutay.plaza import mcp
from hamutay.plaza.send import SendRefused, send
from tests.plaza.conftest import T0

from .helpers import FORBIDDEN, api, cli, disk_rows, gate, snapshot, tool


@pytest.mark.parametrize("name,to", [("plaza_post", "plaza"), ("plaza_send", "elder")])
@pytest.mark.parametrize("enabled,carrier", [(True, " alias "), (True, None), (False, "alias")])
def test_registered_mcp_writes_optional_normalized_carrier(house_guests, name, to, enabled, carrier):
    root, cfg, _ = house_guests
    gate(cfg, enabled)
    server = mcp.build_server(root, "levadura")
    args = {"text": "mcp carrier post"}
    if name == "plaza_send":
        args["to"] = to
    if carrier is not None:
        args["carrier"] = carrier
    result = tool(server, name, **args)
    assert result["sent"] is True
    row = disk_rows(cfg)[0]
    assert row["from"] == "guest:levadura" and row["via"] == "mcp"
    if enabled and carrier is not None:
        assert row["carrier"] == "alias"
    else:
        assert "carrier" not in row
    assert all("carrier" not in r for r in disk_rows(cfg) if r["record_type"] == "delivery")


def test_mcp_descriptions_and_schemas_keep_label_fixed(house_guests):
    root, _, _ = house_guests
    tools = {t.name: t for t in asyncio.run(mcp.build_server(root, "levadura").list_tools())}
    for name in ("plaza_post", "plaza_send"):
        schema = tools[name].inputSchema
        assert "carrier" in schema["properties"]
        assert "carrier" not in schema.get("required", [])
        assert not {"label", "actor", "from", "guest"} & schema["properties"].keys()
        desc = tools[name].description.lower()
        assert "carrier" in desc and "optional" in desc


@pytest.mark.parametrize("name", ["plaza_post", "plaza_send"])
@pytest.mark.parametrize("retry", [False, True])
@pytest.mark.parametrize("enabled", [False, True])
@pytest.mark.parametrize("bad", ["", "   ", "x" * 121, *["alias" + c for c in FORBIDDEN]])
def test_registered_mcp_invalid_carrier_refuses_without_writes(house_guests, name, retry, enabled, bad):
    root, cfg, _ = house_guests
    gate(cfg, enabled)
    server = mcp.build_server(root, "levadura")
    args = {"text": "same post", "key": "token"}
    if name == "plaza_send":
        args["to"] = "elder"
    if retry:
        assert tool(server, name, **args)["sent"] is True
    before = snapshot(root)
    result = tool(server, name, **args, carrier=bad)
    assert result["sent"] is False and "SendRefused" in result["refused"]
    assert snapshot(root) == before


@pytest.mark.parametrize("via,actor", [("mcp", "guest:levadura"), ("cli", "tony")])
@pytest.mark.parametrize("bad", ["alias\n", "", "   ", "x" * 121, 42, False, [], {}])
def test_invalid_carrier_is_refused_before_any_plaza_lock_or_read(house_guests, monkeypatch, via, actor, bad):
    _, cfg, _ = house_guests
    def forbidden(*args, **kwargs):
        pytest.fail("invalid carrier reached a plaza lock/read")
    monkeypatch.setattr(Ledger, "try_locked", forbidden)
    monkeypatch.setattr(Ledger, "read_unlocked", forbidden)
    with pytest.raises(SendRefused):
        send(cfg, actor=actor, via=via, to="plaza", text="post", now=T0, carrier=bad)


@pytest.mark.parametrize("name", ["plaza_post_impl", "plaza_send_impl"])
def test_mcp_impl_interface_accepts_carrier(house_guests, name):
    root, cfg, _ = house_guests
    gate(cfg)
    kwargs = {"text": "impl post", "carrier": "alias"}
    if name == "plaza_send_impl":
        kwargs["to"] = "elder"
    assert api(mcp, name)(root, "levadura", **kwargs)["sent"] is True
    assert disk_rows(cfg)[0]["carrier"] == "alias"


@pytest.mark.parametrize("enabled,carrier", [(True, " alias "), (True, None), (False, "alias")])
@pytest.mark.parametrize("to", ["plaza", "elder"])
def test_cli_parses_and_writes_gated_carrier(house_guests, enabled, carrier, to):
    root, cfg, _ = house_guests
    gate(cfg, enabled)
    args = ["send", "--by", "guest:levadura", "--to", to, "--text", "cli post"]
    if carrier is not None:
        args += ["--carrier", carrier]
    result = cli(root, *args)
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["sent"] is True
    row = disk_rows(cfg)[0]
    if enabled and carrier is not None:
        assert row["carrier"] == "alias"
    else:
        assert "carrier" not in row


@pytest.mark.parametrize("retry", [False, True])
@pytest.mark.parametrize("enabled", [False, True])
@pytest.mark.parametrize("bad", ["", "   ", "x" * 121, *["alias" + c for c in FORBIDDEN if c != "\x00"]])
def test_cli_invalid_carrier_refuses_even_on_duplicate(house_guests, retry, enabled, bad):
    root, cfg, _ = house_guests
    gate(cfg, enabled)
    args = ["send", "--by", "guest:levadura", "--to", "plaza", "--text", "same post", "--key", "cli-token"]
    if retry:
        first = cli(root, *args)
        assert first.returncode == 0, first.stderr
    before = snapshot(root)
    result = cli(root, *args, "--carrier", bad)
    assert result.returncode == 2, result.stdout + result.stderr
    assert "carrier" in result.stderr.lower() and "unrecognized arguments" not in result.stderr
    assert "Traceback" not in result.stderr
    assert snapshot(root) == before


def test_cli_null_character_via_real_parser_refuses(house_guests, capsys):
    from hamutay.plaza.cli import main
    root, cfg, _ = house_guests
    before = snapshot(root)
    assert main(["--project-root", str(root), "send", "--by", "tony", "--to", "plaza",
                 "--text", "post", "--carrier", "alias\x00"]) == 2
    assert "carrier" in capsys.readouterr().err.lower()
    assert snapshot(root) == before


@pytest.mark.parametrize("transport", ["mcp", "cli"])
@pytest.mark.parametrize("to", ["plaza", "elder"])
def test_valid_carrier_change_does_not_change_idempotency_or_persisted_bytes(house_guests, transport, to):
    root, cfg, _ = house_guests
    gate(cfg)
    server = mcp.build_server(root, "levadura")
    def post(carrier):
        if transport == "mcp":
            return tool(server, "plaza_post" if to == "plaza" else "plaza_send", text="stable post",
                        key="stable-token", carrier=carrier, **({} if to == "plaza" else {"to": to}))
        result = cli(root, "send", "--by", "guest:levadura", "--to", to, "--text", "stable post",
                     "--key", "stable-token", "--carrier", carrier)
        assert result.returncode == 0, result.stderr
        return json.loads(result.stdout)
    first = post("first-carrier")
    before = cfg.plaza.read_bytes()
    retry = post("second-carrier")
    assert retry["sent"] and retry["duplicate_of_seq"] == first["seq"]
    assert cfg.plaza.read_bytes() == before
    assert disk_rows(cfg)[0]["carrier"] == "first-carrier"
