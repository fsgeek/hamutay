from hamutay.memory.cognition import NO_ARGUMENT, SessionExchangeCognition
from hamutay.taste_open import ExchangeResult, OpenTasteSession


class FakeSession:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict]] = []

    def exchange(self, user_message: str, **kwargs):
        self.calls.append((user_message, kwargs))
        return {"visible": user_message}


def test_session_exchange_cognition_wraps_plain_exchange_without_extra_kwargs():
    session = FakeSession()
    cognition = SessionExchangeCognition(session)

    response = cognition("wake stimulus")

    assert response == "{'visible': 'wake stimulus'}"
    assert session.calls == [("wake stimulus", {})]


def test_session_exchange_cognition_passes_taste_open_controls_when_supplied():
    session = FakeSession()
    cognition = SessionExchangeCognition(
        session,
        force_memory=None,
        terminal_surface=lambda stimulus: {"kind": "terminal", "stimulus": stimulus},
    )

    cognition("scheduled wake")

    assert session.calls == [
        (
            "scheduled wake",
            {
                "force_memory": None,
                "terminal_surface": {
                    "kind": "terminal",
                    "stimulus": "scheduled wake",
                },
            },
        )
    ]


def test_session_exchange_cognition_default_force_memory_is_omitted_sentinel():
    session = FakeSession()
    cognition = SessionExchangeCognition(session, force_memory=NO_ARGUMENT)

    cognition("plain wake")

    assert session.calls[0][1] == {}


class FakeTasteBackend:
    def __init__(self) -> None:
        self.calls: list[dict] = []

    def call(
        self,
        model,
        system,
        messages,
        experiment_label,
        extra_tools=None,
        tool_executor=None,
    ):
        self.calls.append(
            {
                "model": model,
                "system": system,
                "messages": messages,
                "experiment_label": experiment_label,
                "extra_tools": extra_tools,
                "tool_executor": tool_executor,
            }
        )
        return ExchangeResult(
            raw_output={"response": "live exchange response", "adapter_state": "seen"},
            stop_reason="tool_use",
        )


def test_session_exchange_cognition_wraps_open_taste_session_without_api_call(tmp_path):
    backend = FakeTasteBackend()
    session = OpenTasteSession(
        backend=backend,
        log_path=str(tmp_path / "open_taste.jsonl"),
        experiment_label="adapter-test",
    )
    cognition = SessionExchangeCognition(session, force_memory=None)

    response = cognition("autonomous live wake")

    assert response == "live exchange response"
    assert session.state == {"cycle": 1, "adapter_state": "seen"}
    assert backend.calls[0]["experiment_label"] == "adapter-test"
    assert backend.calls[0]["messages"][-1]["content"] == "autonomous live wake"
