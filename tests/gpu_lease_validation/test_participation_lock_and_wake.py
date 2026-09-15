import inspect
import json
import subprocess
import sys
import threading
import time

import pytest

from hamutay.gpu_lease.gate import LeaseGate

from conftest import append_jsonl, lease_object, write_json


def _pending(event_id, at):
    return {
        "record_type": "event_status", "event_id": event_id, "status": "pending",
        "created_at": at.isoformat(), "event": {"type": "validation", "content": "wake"},
    }


def _invoke_runner(runner, store, clock):
    """Supply only public-domain collaborators; a bound store must reject before using them."""
    values = {
        "store": store,
        "event_store": store,
        "session": object(),
        "now": clock(),
        "run_pending": lambda: None,
        "max_events": 1,
        "limit": 1,
    }
    args = []
    kwargs = {}
    for parameter in inspect.signature(runner).parameters.values():
        if parameter.name in {"claim_gate", "gate", "lease_gate"}:
            continue
        if parameter.default is not inspect.Parameter.empty:
            continue
        value = values.get(parameter.name, object())
        if parameter.kind in {parameter.POSITIONAL_ONLY, parameter.POSITIONAL_OR_KEYWORD}:
            args.append(value)
        else:
            kwargs[parameter.name] = value
    return runner(*args, **kwargs)


def test_bound_store_refuses_every_unguarded_claim_surface(tmp_path, clock):
    from hamutay.events import EventStore, LeaseGateRequired, run_next_event, run_pending_events, step_pending_events

    door = tmp_path / "bound"
    door.mkdir()
    write_json(door / "door.json", {"gpu_lease": "4090"})
    log = door / "session.jsonl.events.jsonl"
    append_jsonl(log, _pending("e1", clock()))
    store = EventStore(log)

    with pytest.raises(LeaseGateRequired):
        store.claim_next_pending(clock())
    for runner in (run_next_event, run_pending_events, step_pending_events):
        with pytest.raises(LeaseGateRequired):
            _invoke_runner(runner, store, clock)


def test_unbound_store_claim_behavior_is_unchanged(tmp_path, clock):
    from hamutay.events import EventStore

    door = tmp_path / "hosted"
    door.mkdir()
    log = door / "session.jsonl.events.jsonl"
    append_jsonl(log, _pending("e1", clock()))
    store = EventStore(log)

    claimed = store.claim_next_pending(clock())

    assert claimed is not None


def test_lease_gate_claim_blocks_on_4090_lock_from_other_process(p, ctx, tmp_path, clock):
    """Observed contract: claim stayed blocked until the subprocess released flock."""
    from hamutay.events import EventStore

    door = tmp_path / "door"
    door.mkdir()
    write_json(door / "door.json", {"gpu_lease": "4090"})
    store = EventStore(door / "session.jsonl.events.jsonl")
    p.lock().parent.mkdir(parents=True, exist_ok=True)
    holder = subprocess.Popen(
        [sys.executable, "-c",
         "import fcntl,sys; f=open(sys.argv[1],'a+'); fcntl.flock(f,fcntl.LOCK_EX); print('held',flush=True); sys.stdin.read(1)",
         str(p.lock())],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True,
    )
    assert holder.stdout.readline().strip() == "held"
    finished = threading.Event()

    def claim():
        LeaseGate(store, ctx).claim(clock())
        finished.set()

    thread = threading.Thread(target=claim, daemon=True)
    thread.start()
    assert not finished.wait(0.25), "claim proceeded while another process held 4090.lock"
    holder.stdin.write("x")
    holder.stdin.flush()
    holder.wait(timeout=5)
    thread.join(timeout=5)
    assert finished.is_set(), "claim did not resume after 4090.lock was released"


def test_live_lease_does_not_stop_server_until_running_wake_completes(p, ctx, sd, tmp_path, clock):
    from hamutay.events import EventStore
    from hamutay.heartbeat import HeartbeatLoop

    door = tmp_path / "door"
    door.mkdir()
    write_json(door / "door.json", {"gpu_lease": "4090"})
    log = door / "session.jsonl.events.jsonl"
    append_jsonl(log, {
        "record_type": "event_status", "event_id": "wake", "status": "running",
        "created_at": clock().isoformat(), "event": {"type": "validation", "content": "wake"},
    })
    lease = lease_object(clock)
    write_json(p.lease(), lease)
    store = EventStore(log)
    gate = LeaseGate(store, ctx)
    calls = 0

    def run_pending():
        nonlocal calls
        calls += 1
        if calls == 2:
            append_jsonl(log, {
                "record_type": "event_status", "event_id": "wake", "status": "completed",
                "created_at": clock().isoformat(),
            })
        return {"ran": 1, "status": "ok"}

    parameters = inspect.signature(HeartbeatLoop).parameters
    values = {"store": store, "run_pending": run_pending, "now": clock, "lease_gate": gate, "gate": gate,
              "claim_gate": gate, "sleep": lambda _: None}
    kwargs = {name: values[name] for name, parameter in parameters.items()
              if name in values and parameter.kind != parameter.POSITIONAL_ONLY}
    loop = HeartbeatLoop(**kwargs)

    loop.step()
    assert not any(call[0] == "stop" for call in sd.calls)
    loop.step()
    assert any(call[0] == "stop" for call in sd.calls)

