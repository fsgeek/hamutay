from hamutay.memory.cognition import NO_ARGUMENT, SessionExchangeCognition


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
