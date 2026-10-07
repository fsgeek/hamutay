"""`uv run python -m hamutay.viewer` — a read-only local view of the ayllu (plaza, assembly, door vitals).

Binds 127.0.0.1 only. It writes nothing and reads no door's home (see state.py).
"""
from __future__ import annotations

import argparse
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from .state import gather

PAGE = Path(__file__).with_name("page.html")


def make_handler(project_root: Path):
    class Handler(BaseHTTPRequestHandler):
        def _send(self, code: int, body: bytes, ctype: str) -> None:
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):  # noqa: N802
            path = self.path.split("?", 1)[0]
            if path == "/":
                self._send(200, PAGE.read_bytes(), "text/html; charset=utf-8")
            elif path == "/api/state":
                try:
                    body = json.dumps(gather(project_root), default=str).encode()
                    self._send(200, body, "application/json")
                except Exception as e:  # noqa: BLE001
                    self._send(500, json.dumps({"error": f"{type(e).__name__}: {e}"}).encode(), "application/json")
            else:
                self._send(404, b"not found", "text/plain")

        def log_message(self, fmt, *args):  # quiet: the viewer is not an access log
            pass

    return Handler


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="hamutay.viewer")
    p.add_argument("--project-root", default=".")
    p.add_argument("--port", type=int, default=8787)
    a = p.parse_args(argv)
    root = Path(a.project_root).resolve()
    server = ThreadingHTTPServer(("127.0.0.1", a.port), make_handler(root))
    print(f"ayllu viewer: http://localhost:{a.port}/  (read-only; project root {root})", flush=True)
    server.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
