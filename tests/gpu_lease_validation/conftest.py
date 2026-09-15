import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import UUID, uuid4

import pytest

from hamutay.gpu_lease.cli import _ctx
from hamutay.gpu_lease.state import paths, scope_unit_for
from hamutay.gpu_lease.systemd import SystemdUnavailable


UTC = timezone.utc
SERVER = "hamutay-llama-server.service"


class FrozenClock:
    def __init__(self, value=None):
        self.value = value or datetime(2026, 9, 15, 12, 0, tzinfo=UTC)

    def __call__(self):
        return self.value

    def advance(self, **kwargs):
        self.value += timedelta(**kwargs)


class FakeSystemd:
    """Deterministic systemd boundary; no command reaches the host."""

    def __init__(self):
        self.units = {}
        self.calls = []
        self.unavailable = False
        self.before_start = None
        self.before_stop = None

    @staticmethod
    def inactive(*, load_state="loaded"):
        return {
            "active_state": "inactive",
            "sub_state": "dead",
            "load_state": load_state,
            "invocation_id": "",
        }

    @staticmethod
    def active(invocation_id="inv-1"):
        return {
            "active_state": "active",
            "sub_state": "running",
            "load_state": "loaded",
            "invocation_id": invocation_id,
        }

    def show(self, unit):
        if self.unavailable:
            raise SystemdUnavailable("validation fake: systemctl unavailable")
        self.calls.append(("show", unit))
        return dict(self.units.get(unit, self.inactive(load_state="not-found")))

    def start(self, unit):
        if self.unavailable:
            raise SystemdUnavailable("validation fake: systemctl unavailable")
        if self.before_start:
            self.before_start(unit)
        self.calls.append(("start", unit))
        self.units[unit] = self.active(f"inv-{len(self.calls)}")
        return 0, ""

    def stop(self, unit):
        if self.unavailable:
            raise SystemdUnavailable("validation fake: systemctl unavailable")
        if self.before_stop:
            self.before_stop(unit)
        self.calls.append(("stop", unit))
        state = self.units.setdefault(unit, self.inactive())
        state.update(active_state="inactive", sub_state="dead")
        if unit.endswith(".scope"):
            state["load_state"] = "not-found"
        return 0, ""

    def kill(self, unit, signal="TERM"):
        if self.unavailable:
            raise SystemdUnavailable("validation fake: systemctl unavailable")
        self.calls.append(("kill", unit, signal))
        return 0, ""


def write_json(path: Path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value) + "\n")


def append_jsonl(path: Path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a") as stream:
        stream.write(json.dumps(value) + "\n")


def read_jsonl(path: Path):
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text().splitlines() if line]


def lease_object(clock, *, lease_id=None, mutation_id=None, minutes=60, holder="yupi", purpose="training"):
    lease_id = lease_id or str(uuid4())
    mutation_id = mutation_id or str(uuid4())
    UUID(lease_id)
    UUID(mutation_id)
    return {
        "resource": "4090",
        "lease_id": lease_id,
        "generation": 1,
        "mutation_id": mutation_id,
        "holder": holder,
        "purpose": purpose,
        "since": clock().isoformat(),
        "expires_at": (clock() + timedelta(minutes=minutes)).isoformat(),
        "expected_until": (clock() + timedelta(minutes=minutes)).isoformat(),
        "scope_unit": scope_unit_for(lease_id),
    }


@pytest.fixture
def clock():
    return FrozenClock()


@pytest.fixture
def sd():
    return FakeSystemd()


@pytest.fixture
def p(tmp_path, monkeypatch):
    state_root = tmp_path / "state"
    monkeypatch.setenv("AYLLU_STATE_DIR", str(state_root))
    return paths()


@pytest.fixture
def ctx(p, sd, clock):
    return _ctx(p, sd, clock, "validator")
