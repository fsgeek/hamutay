import io
import json
from pathlib import Path

import pytest

from hamutay.viewer import __main__ as viewer

from .conftest import SECRETS
from .test_state import snapshot


class MemoryConnection:
    """Run BaseHTTPRequestHandler's real parser/dispatch without opening a socket."""

    def __init__(self, request):
        self.request = io.BytesIO(request)
        self.response = bytearray()

    def makefile(self, mode, buffering=None):
        assert mode == "rb"
        return self.request

    def sendall(self, data):
        self.response.extend(data)


def request(root, target, method="GET"):
    connection = MemoryConnection(f"{method} {target} HTTP/1.0\r\nHost: localhost\r\n\r\n".encode())
    viewer.make_handler(root)(connection, ("127.0.0.1", 43210), object())
    head, body = bytes(connection.response).split(b"\r\n\r\n", 1)
    lines = head.decode().split("\r\n")
    status = int(lines[0].split()[1])
    headers = {k.lower(): v.strip() for k, v in (line.split(":", 1) for line in lines[1:])}
    return status, headers, body


def test_api_exposes_only_public_data_and_is_not_cached(community):
    status, headers, body = request(community.root, "/api/state?cache-bust=1")
    assert status == 200
    assert headers["content-type"] == "application/json"
    assert headers["cache-control"] == "no-store"
    assert int(headers["content-length"]) == len(body)
    view = json.loads(body)
    assert len(view["doors"]) == 3
    assert len(view["plaza"]) == 2
    assert view["guests"] == ["levadura", "visitor-two"]
    assert all(secret.encode() not in body for secret in SECRETS)
    assert b'"response_text"' not in body


def test_api_request_creates_or_changes_no_project_files(community):
    before = snapshot(community.root)
    status, _, _ = request(community.root, "/api/state")
    assert status == 200
    assert snapshot(community.root) == before


def test_root_serves_the_bundled_page_without_project_reads(community, monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("Serving the page must not gather community state")

    monkeypatch.setattr(viewer, "gather", forbidden)
    before = snapshot(community.root)
    status, headers, body = request(community.root, "/?anything=1")
    assert status == 200
    assert headers["content-type"] == "text/html; charset=utf-8"
    assert headers["cache-control"] == "no-store"
    assert body == viewer.PAGE.read_bytes()
    assert snapshot(community.root) == before


@pytest.mark.parametrize("target", [
    "/community/qwen/session.jsonl", "/community/qwen/state.json", "/community/qwen/raw-output.txt",
    "/community/qwen/session.jsonl.events.jsonl", "/../community/qwen/session.jsonl",
    "/%2e%2e/community/qwen/session.jsonl", "/api/state/", "/favicon.ico",
])
def test_routes_cannot_serve_private_files(community, target):
    before = snapshot(community.root)
    status, _, body = request(community.root, target)
    assert status == 404
    assert all(secret.encode() not in body for secret in SECRETS)
    assert snapshot(community.root) == before


@pytest.mark.parametrize("method", ["POST", "PUT", "PATCH", "DELETE"])
def test_mutating_http_methods_are_rejected_without_writes(community, method):
    before = snapshot(community.root)
    status, _, _ = request(community.root, "/api/state", method)
    assert status in (405, 501)
    assert snapshot(community.root) == before


def test_plaza_read_failure_remains_a_200_state_response(community, monkeypatch):
    read = Path.read_bytes

    def unreadable(path):
        if path == community.cfg.plaza:
            raise OSError("Plaza read failed")
        return read(path)

    monkeypatch.setattr(Path, "read_bytes", unreadable)
    status, _, body = request(community.root, "/api/state")
    assert status == 200
    view = json.loads(body)
    assert "OSError" in view["plaza_error"]
    assert len(view["doors"]) == 3
    assert len(view["assembly"]) == 1


@pytest.mark.parametrize("port", [8787, 0, 9876])
def test_startup_binds_only_ipv4_loopback(community, monkeypatch, port):
    servers = []

    class FakeServer:
        def __init__(self, address, handler):
            self.address, self.handler, self.served = address, handler, False
            servers.append(self)

        def serve_forever(self):
            self.served = True

    monkeypatch.setattr(viewer, "ThreadingHTTPServer", FakeServer)
    before = snapshot(community.root)
    args = ["--project-root", str(community.root)]
    if port != 8787:
        args += ["--port", str(port)]
    assert viewer.main(args) == 0
    assert len(servers) == 1
    assert servers[0].address == ("127.0.0.1", port)
    assert servers[0].served
    assert snapshot(community.root) == before


def test_no_cli_option_can_override_loopback(community, monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("Unrecognized host option must not start a server")

    monkeypatch.setattr(viewer, "ThreadingHTTPServer", forbidden)
    with pytest.raises(SystemExit) as exc:
        viewer.main(["--project-root", str(community.root), "--host", "0.0.0.0"])
    assert exc.value.code == 2
