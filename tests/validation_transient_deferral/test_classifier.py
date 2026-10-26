"""Message contracts from Change 1; no provider calls or implementation helpers."""

import pytest

from hamutay import events


@pytest.mark.parametrize("code", [408, 429, 500, 502, 503, 504, 529])
@pytest.mark.parametrize("provider", ["openai", "anthropic"])
def test_listed_provider_status_is_transient(provider, code):
    message = (
        f"OpenAI backend error: {{'error': {{'code': {code}, 'message': 'unavailable'}}}}"
        if provider == "openai"
        else f"anthropic-direct error {code}: unavailable"
    )
    assert events.is_transient_provider_failure(RuntimeError(message)) is True


@pytest.mark.parametrize("message", [
    "OpenAI backend transport failed after retries",
    "anthropic-direct transport failed",
])
def test_listed_transport_prefix_is_transient(message):
    assert events.is_transient_provider_failure(RuntimeError(message)) is True


@pytest.mark.parametrize("code", [400, 401, 402, 403, 404, 413, 422])
@pytest.mark.parametrize("provider", ["openai", "anthropic"])
def test_other_provider_4xx_is_terminal(provider, code):
    message = (
        f"OpenAI backend error: {{'error': {{'code': {code}, 'message': 'invalid'}}}}"
        if provider == "openai"
        else f"anthropic-direct error {code}: invalid"
    )
    assert events.is_transient_provider_failure(RuntimeError(message)) is False


@pytest.mark.parametrize("message", [
    "ReadTimeout after 300 seconds (not retried ...)",
    "finish_reason=length",
    "malformed JSON arguments",
    "context window exhausted",
    "plain application failure",
    "",
])
def test_generation_and_application_errors_are_terminal(message):
    assert events.is_transient_provider_failure(RuntimeError(message)) is False
