"""Isolation and the only shared fixtures; no board import at collection time."""
import socket

import pytest

from .support import House


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def denied(*args, **kwargs):
        raise AssertionError("validation_board must not use the network")
    monkeypatch.setattr(socket.socket, "connect", denied)
    monkeypatch.setattr(socket, "create_connection", denied)


@pytest.fixture
def house(tmp_path):
    return House(tmp_path / "project")
