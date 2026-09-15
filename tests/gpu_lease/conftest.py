import pytest
from hamutay.gpu_lease.state import paths

class FakeSystemd:
    """Unit states as the test sets them; every call is recorded."""
    def __init__(self):
        self.units = {}        # unit -> dict(active_state, sub_state, load_state, invocation_id)
        self.calls = []
        self.fail_show = False
    def show(self, unit):
        if self.fail_show:
            from hamutay.gpu_lease.systemd import SystemdUnavailable
            raise SystemdUnavailable("fake")
        self.calls.append(("show", unit))
        return dict(self.units.get(unit, {"active_state": "inactive", "sub_state": "dead",
                                          "load_state": "not-found", "invocation_id": ""}))
    def start(self, unit):
        self.calls.append(("start", unit))
        self.units[unit] = {"active_state": "active", "sub_state": "running",
                            "load_state": "loaded", "invocation_id": f"inv-{len(self.calls)}"}
        return 0, ""
    def stop(self, unit):
        self.calls.append(("stop", unit))
        u = self.units.setdefault(unit, {"load_state": "loaded", "invocation_id": ""})
        u.update(active_state="inactive", sub_state="dead")
        return 0, ""
    def kill(self, unit, signal="TERM"):
        self.calls.append(("kill", unit, signal))
        return 0, ""

class StubbornSystemd:
    """A scope that survives every stop: the workload owns the GPU regardless."""
    def __init__(self, scope):
        self.scope = scope
        self.calls = []
    def show(self, unit):
        self.calls.append(("show", unit))
        if unit == self.scope:
            return {"active_state": "active", "sub_state": "running",
                    "load_state": "loaded", "invocation_id": "i"}
        return {"active_state": "inactive", "sub_state": "dead",
                "load_state": "not-found", "invocation_id": ""}
    def start(self, unit): self.calls.append(("start", unit)); return 0, ""
    def stop(self, unit): self.calls.append(("stop", unit)); return 0, ""   # no effect
    def kill(self, unit, signal="TERM"): return 0, ""


@pytest.fixture
def sd():
    return FakeSystemd()

@pytest.fixture
def p(tmp_path, monkeypatch):
    monkeypatch.setenv("AYLLU_STATE_DIR", str(tmp_path / "state"))
    return paths()
