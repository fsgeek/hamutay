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


@pytest.mark.parametrize("runner_name", ["run_next_event", "run_pending_events", "step_pending_events"])
def test_bound_store_refuses_every_unguarded_claim_surface(tmp_path, clock, runner_name):
    from hamutay.events import EventStore, LeaseGateRequired, run_next_event, run_pending_events, step_pending_events

    door = tmp_path / "bound"
    door.mkdir()
    write_json(door / "door.json", {"gpu_lease": "4090"})
    log = door / "session.jsonl.events.jsonl"
    append_jsonl(log, _pending("e1", clock()))
    store = EventStore(log)

    with pytest.raises(LeaseGateRequired):
        store.claim_next_pending(now=clock())
    runner = {
        "run_next_event": run_next_event,
        "run_pending_events": run_pending_events,
        "step_pending_events": step_pending_events,
    }[runner_name]
    with pytest.raises(LeaseGateRequired):
        _invoke_runner(runner, store, clock)


@pytest.mark.parametrize("command", ["run-next", "run-all"])
def test_bound_store_refuses_cli_runners(tmp_path, clock, command):
    door = tmp_path / "bound-cli"
    door.mkdir()
    write_json(door / "door.json", {"gpu_lease": "4090"})
    log = door / "session.jsonl.events.jsonl"
    session_log = door / "session.jsonl"
    append_jsonl(session_log, {
        "record_type": "open_taste_cycle",
        "cycle": 0,
        "state": {},
        "timestamp": clock().isoformat(),
    })
    append_jsonl(log, _pending("e1", clock()))
    result = subprocess.run(
        [
            sys.executable, "-m", "hamutay.events", command,
            "--log-path", str(session_log),
            "--event-log-path", str(log),
            "--provider", "openai", "--api-key", "validation",
            "--project-root", str(tmp_path),
        ],
        text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=10,
    )

    assert result.returncode != 0
    assert "LeaseGateRequired" in result.stdout or "claim through the heartbeat gate" in result.stdout


def test_unbound_store_claim_behavior_is_unchanged(tmp_path, clock):
    from hamutay.events import EventStore

    door = tmp_path / "hosted"
    door.mkdir()
    log = door / "session.jsonl.events.jsonl"
    append_jsonl(log, _pending("e1", clock()))
    store = EventStore(log)

    claimed = store.claim_next_pending(now=clock())

    assert claimed is not None


def test_lease_gate_claim_blocks_on_4090_lock_from_other_process(p, ctx, tmp_path, clock):
    """Observed contract: claim stayed blocked until the subprocess released flock."""
    from hamutay.events import EventStore

    door = tmp_path / "door"
    door.mkdir()
    write_json(door / "door.json", {"gpu_lease": "4090"})
    store = EventStore(door / "session.jsonl.events.jsonl")
    p.lock.parent.mkdir(parents=True, exist_ok=True)
    holder = subprocess.Popen(
        [sys.executable, "-c",
         "import fcntl,sys; f=open(sys.argv[1],'a+'); fcntl.flock(f,fcntl.LOCK_EX); print('held',flush=True); sys.stdin.read(1)",
         str(p.lock)],
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
    holder.communicate("x", timeout=5)
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
    write_json(p.lease, lease)
    sd.units["hamutay-llama-server.service"] = sd.active()
    store = EventStore(log)
    gate = LeaseGate(store, ctx)
    calls = 0

    def run_pending(*args, **kwargs):
        nonlocal calls
        calls += 1
        if calls == 2:
            append_jsonl(log, {
                "record_type": "event_status", "event_id": "wake", "status": "completed",
                "created_at": clock().isoformat(),
            })
        return {"ran": 1, "status": "ok"}

    loop = HeartbeatLoop(
        None,
        store,
        now=clock,
        run_pending=run_pending,
        summarize=lambda records, now: {
            "pending_runnable_count": 0,
            "pending_waiting_count": 0,
        },
        guard=gate,
    )

    loop.step()
    assert not any(call[0] == "stop" for call in sd.calls)
    loop.step()
    assert any(call[0] == "stop" for call in sd.calls)
