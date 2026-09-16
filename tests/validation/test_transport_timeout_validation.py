"""Independent validation of OpenAI transport-timeout behavior."""

from __future__ import annotations

from collections.abc import Callable

import httpx
import pytest

import hamutay.taste_open as taste_open
from hamutay.heartbeat import build_parser, resolve_transport_timeout
from hamutay.taste_open import OpenAITasteBackend


URL = "http://localhost:8080/v1/chat/completions"
PAYLOAD = {"model": "validation-model", "messages": []}
HEADERS = {"Authorization": "Bearer validation-key"}


class _Response:
    def __init__(self, status_code: int, body: dict):
        self.status_code = status_code
        self._body = body

    def json(self) -> dict:
        return self._body


def _backend(*, max_retries: int = 2, timeout: float = 412.5):
    return OpenAITasteBackend(
        api_key="validation-key",
        max_retries=max_retries,
        retry_base_delay_s=0.0,
        timeout=timeout,
    )


def test_read_timeout_fails_immediately_without_retry(monkeypatch):
    timeout = 412.5
    calls = []
    sleeps = []

    def post(url, *, json, headers, timeout):
        calls.append((url, json, headers, timeout))
        request = httpx.Request("POST", url)
        raise httpx.ReadTimeout("generation exceeded deadline", request=request)

    monkeypatch.setattr(httpx, "post", post)
    monkeypatch.setattr(taste_open.time, "sleep", sleeps.append)

    with pytest.raises(RuntimeError) as exc_info:
        _backend(max_retries=7, timeout=timeout)._post_with_retry(
            URL, PAYLOAD, HEADERS
        )

    message = str(exc_info.value).lower()
    assert len(calls) == 1
    assert calls[0] == (URL, PAYLOAD, HEADERS, timeout)
    assert sleeps == []
    assert str(timeout) in message
    assert "second" in message
    assert "not retried" in message


@pytest.mark.parametrize(
    "error_factory",
    [
        httpx.ConnectError,
        httpx.ConnectTimeout,
        httpx.RemoteProtocolError,
        httpx.ReadError,
        httpx.WriteError,
        httpx.NetworkError,
    ],
)
def test_other_transport_faults_keep_bounded_retries(
    monkeypatch,
    error_factory: Callable[..., httpx.TransportError],
):
    calls = []
    sleeps = []

    def post(url, *, json, headers, timeout):
        calls.append((url, json, headers, timeout))
        request = httpx.Request("POST", url)
        raise error_factory("transient transport fault", request=request)

    monkeypatch.setattr(httpx, "post", post)
    monkeypatch.setattr(taste_open.time, "sleep", sleeps.append)

    with pytest.raises(RuntimeError):
        _backend(max_retries=2)._post_with_retry(URL, PAYLOAD, HEADERS)

    assert len(calls) == 3
    assert len(sleeps) == 2


def test_5xx_response_is_retried(monkeypatch):
    responses = iter(
        [
            _Response(503, {"error": "temporarily unavailable"}),
            _Response(200, {"ok": True}),
        ]
    )
    calls = []
    sleeps = []

    def post(url, *, json, headers, timeout):
        calls.append((url, json, headers, timeout))
        return next(responses)

    monkeypatch.setattr(httpx, "post", post)
    monkeypatch.setattr(taste_open.time, "sleep", sleeps.append)

    result = _backend(max_retries=2)._post_with_retry(URL, PAYLOAD, HEADERS)

    assert result == {"ok": True}
    assert len(calls) == 2
    assert len(sleeps) == 1


def test_4xx_response_is_not_retried(monkeypatch):
    calls = []
    sleeps = []
    body = {"error": "invalid request"}

    def post(url, *, json, headers, timeout):
        calls.append((url, json, headers, timeout))
        return _Response(400, body)

    monkeypatch.setattr(httpx, "post", post)
    monkeypatch.setattr(taste_open.time, "sleep", sleeps.append)

    result = _backend(max_retries=5)._post_with_retry(URL, PAYLOAD, HEADERS)

    assert result == body
    assert len(calls) == 1
    assert sleeps == []


@pytest.mark.parametrize(
    "base_url",
    [
        "http://127.0.0.1:8080/v1",
        "http://localhost:8080/v1",
        "http://[::1]:8080/v1",
    ],
)
def test_local_hosts_receive_long_transport_timeout(base_url):
    assert resolve_transport_timeout(base_url, None) == (
        2700.0,
        "local substrate default",
    )


@pytest.mark.parametrize(
    "base_url",
    [None, "https://api.openai.com/v1", "https://example.invalid/v1"],
)
def test_nonlocal_or_missing_host_receives_hosted_timeout(base_url):
    assert resolve_transport_timeout(base_url, None) == (300.0, "hosted default")


@pytest.mark.parametrize(
    "base_url",
    [None, "http://localhost:8080/v1", "https://api.openai.com/v1"],
)
def test_explicit_transport_timeout_overrides_all_defaults(base_url):
    assert resolve_transport_timeout(base_url, 123) == (123.0, "explicit")


def test_heartbeat_parser_accepts_timeout_as_float():
    args = build_parser().parse_args(
        ["--log-path", "heartbeat.jsonl", "--timeout", "42.5"]
    )

    assert args.timeout == 42.5
    assert isinstance(args.timeout, float)
