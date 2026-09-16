"""Transport timeouts on the OpenAI-compatible backend.

Found live 2026-09-16 on community/qwen c9: the resident's first request
generated for 5m34s on the local llama-server and was cancelled by our
client at its 300 s read timeout; the client then retried three times,
each retry hit the prompt cache, thought for another 5.5 minutes, and was
cancelled again. Twenty-one minutes of GPU work thrown away on a retry
that could never succeed, and the wake failed.

Two rules follow. A read timeout is not a transient transport fault when
the generation has a fixed length: it is never retried. And a local
substrate's timeout is bounded by its generation speed, not by a hosted
API's defaults.
"""

import httpx
import pytest

from hamutay.heartbeat import resolve_transport_timeout
from hamutay.taste_open import OpenAITasteBackend


def _backend(monkeypatch, exc, *, max_retries=3):
    calls = []

    def fake_post(url, json=None, headers=None, timeout=None):
        calls.append(timeout)
        raise exc

    monkeypatch.setattr(httpx, "post", fake_post)
    monkeypatch.setattr("hamutay.taste_open.time.sleep", lambda s: None)
    backend = OpenAITasteBackend(
        api_key="k", max_retries=max_retries, retry_base_delay_s=0.0, timeout=123.0
    )
    return backend, calls


def test_read_timeout_is_not_retried(monkeypatch):
    backend, calls = _backend(monkeypatch, httpx.ReadTimeout("timed out"))
    with pytest.raises(RuntimeError) as err:
        backend._post_with_retry("http://x/v1/chat/completions", {}, {})
    assert len(calls) == 1
    msg = str(err.value)
    assert "ReadTimeout" in msg and "123" in msg and "not retried" in msg


def test_connect_error_is_still_retried(monkeypatch):
    backend, calls = _backend(monkeypatch, httpx.ConnectError("refused"), max_retries=2)
    with pytest.raises(RuntimeError):
        backend._post_with_retry("http://x/v1/chat/completions", {}, {})
    assert len(calls) == 3


def test_timeout_is_passed_to_httpx(monkeypatch):
    backend, calls = _backend(monkeypatch, httpx.ReadTimeout("timed out"))
    with pytest.raises(RuntimeError):
        backend._post_with_retry("http://x/v1/chat/completions", {}, {})
    assert calls == [123.0]


@pytest.mark.parametrize(
    "base_url, explicit, expected, source",
    [
        ("http://127.0.0.1:8081/v1", None, 2700.0, "local substrate default"),
        ("http://localhost:8081/v1", None, 2700.0, "local substrate default"),
        ("https://openrouter.ai/api/v1", None, 300.0, "hosted default"),
        (None, None, 300.0, "hosted default"),
        ("http://127.0.0.1:8081/v1", 60.0, 60.0, "explicit"),
        ("https://openrouter.ai/api/v1", 900.0, 900.0, "explicit"),
    ],
)
def test_transport_timeout_resolution(base_url, explicit, expected, source):
    assert resolve_transport_timeout(base_url, explicit) == (expected, source)
