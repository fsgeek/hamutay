"""T1--T8, destructive-to-service integration tests. NEVER enabled by default.

Run only on the installed house as uid 1000, with HAMUTAY_CAMERA_ROOT_TESTS=1
and passwordless sudo. Collection without that opt-in does not even run sudo.
The fixture restores initial service states, member metadata, and test files.
The x86-64 ptrace helper is test infrastructure, not camera implementation.
See ASSUMPTIONS.md before explicitly enabling these tests.
"""

from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from datetime import datetime, timezone
import errno
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import select
import socket
import subprocess
import sys
import threading
import time
from urllib.request import Request, urlopen
import base64
import uuid
import warnings

import pytest


ROOT = Path(__file__).resolve().parents[2]
GATE = "hamutay-camera-gate.service"
SCRIBE = "hamutay-camera-scribe.service"
SOCKET = Path("/run/hamutay-camera/events.sock")
INSTALLED_GATE = Path("/usr/local/lib/hamutay-camera/gate.py")
INSTALLED_FILES = tuple(INSTALLED_GATE.with_name(name) for name in ("gate.py", "scribe.py", "camera.py"))
MEMBERS = ROOT / "community/plaza/members.json"
pytestmark = pytest.mark.skipif(
    os.environ.get("HAMUTAY_CAMERA_ROOT_TESTS") != "1",
    reason="real services: explicitly set HAMUTAY_CAMERA_ROOT_TESTS=1",
)


def command(*args, check=True, timeout=15):
    return subprocess.run([str(a) for a in args], check=check, text=True,
                          capture_output=True, timeout=timeout)


def sudo(*args, **kwargs):
    return command("sudo", "-n", *args, **kwargs)


def systemctl(*args, **kwargs):
    return sudo("systemctl", *args, **kwargs)


def wait_for(predicate, seconds, description):
    deadline = time.monotonic() + seconds
    while True:
        result = predicate()
        if result:
            return result
        if time.monotonic() >= deadline:
            pytest.fail("timed out waiting for " + description)
        time.sleep(min(0.02, max(0, deadline - time.monotonic())))


def gate_pid():
    return int(systemctl("show", GATE, "--property=MainPID", "--value").stdout.strip() or 0)


def fanotify_info(pid):
    # Read root-owned proc data without running this pytest process as root.
    code = """import json, os, pathlib, sys
p = pathlib.Path('/proc') / sys.argv[1]
out = {}
for fd in (p / 'fd').iterdir():
    try:
        if 'fanotify' in os.readlink(fd):
            out[fd.name] = (p / 'fdinfo' / fd.name).read_text()
    except FileNotFoundError:
        pass
print(json.dumps(out))
"""
    return {int(fd): info for fd, info in json.loads(sudo(sys.executable, "-c", code, pid).stdout).items()}


def marked_inodes():
    return {int(ino, 16) for info in fanotify_info(gate_pid()).values()
            for ino in re.findall(r"fanotify ino:([0-9a-fA-F]+)\b", info)}


def database_rows(query, bind_vars=None):
    # The CLI has no specified JSON format; query the specified database/schema.
    endpoint = os.environ.get("HAMUTAY_CAMERA_ARANGO_URL", "http://127.0.0.1:8529")
    req = Request(endpoint.rstrip("/") + "/_db/ayllu_camera/_api/cursor",
                  data=json.dumps({"query": query, "bindVars": bind_vars or {}, "batchSize": 2000}).encode(),
                  headers={"Content-Type": "application/json"})
    username = os.environ.get("HAMUTAY_CAMERA_ARANGO_USER")
    if username is not None:
        secret = username + ":" + os.environ.get("HAMUTAY_CAMERA_ARANGO_PASSWORD", "")
        req.add_header("Authorization", "Basic " + base64.b64encode(secret.encode()).decode())
    with urlopen(req, timeout=5) as response:
        body = json.load(response)
    assert not body.get("hasMore"), "database observation exceeded the harness's 2000-row bound"
    return body["result"]


def statuses():
    return database_rows("FOR s IN status SORT s.at DESC LIMIT 2000 RETURN s")


def fresh_statuses(previous):
    return [s for s in statuses() if s["_key"] not in previous]


@pytest.fixture
def house():
    # This fixture is not entered at all unless the module's explicit opt-in holds.
    try:
        available = command("sudo", "-n", "true", check=False).returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        available = False
    if not available:
        pytest.skip("requires sudo -n true to succeed")
    assert os.geteuid() == 1000, "invoke pytest as the house user, never as root"
    assert all(p.is_file() for p in INSTALLED_FILES), "install deploy/camera/install.sh before opting in"
    assert (ROOT / "deploy/ayllu-camera").is_file()
    states = {
        "gate": systemctl("is-active", GATE, check=False).returncode == 0,
        "scribe": systemctl("is-active", SCRIBE, check=False).returncode == 0,
    }
    original_members = MEMBERS.read_bytes()
    members_mode = MEMBERS.stat().st_mode & 0o777
    members = json.loads(original_members)["members"]
    homes = [ROOT / "community" / name for name in members]
    assert homes and all(p.is_dir() and not p.is_symlink() and p.stat().st_uid == 1000 for p in homes)
    files, new_homes, children = [], [], []
    token = ".camera-validation-" + uuid.uuid4().hex

    class House:
        def start_gate(self):
            systemctl("reset-failed", GATE, check=False)
            systemctl("restart", GATE)
            return wait_for(lambda: gate_pid() or False, 5, "gate MainPID")

        def start_scribe(self):
            systemctl("start", SCRIBE)
            wait_for(lambda: sudo("test", "-S", SOCKET, check=False).returncode == 0, 5, "scribe socket")

        def start_db(self):
            # Never control the production container; only check readiness and
            # that the test's read-only credentials work.
            def ready():
                try:
                    statuses()
                    return True
                except OSError:
                    return False
            wait_for(ready, 15, "ayllu_camera database")

        def probe(self, home=None):
            p = (home or homes[0]) / token
            p.write_bytes(b"camera validation\n")
            files.append(p)
            return p

        def reader(self, path):
            # Child output appears immediately before the potentially blocked open.
            code = """import json, os, sys, time
print('ready', flush=True)
t = time.monotonic()
fd = os.open(sys.argv[1], os.O_RDONLY)
os.close(fd)
print(json.dumps({'allowed': True, 'elapsed': time.monotonic() - t}), flush=True)
"""
            child = subprocess.Popen([sys.executable, "-c", code, str(path)], bufsize=0,
                                     stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            children.append(child)
            assert select.select([child.stdout], [], [], 2)[0], "reader did not start"
            assert child.stdout.readline().strip() == b"ready"
            return child

        def new_member(self):
            name = "camera_validation_" + uuid.uuid4().hex
            home = ROOT / "community" / name
            home.mkdir()
            new_homes.append(home)
            document = json.loads(original_members)
            document["members"][name] = {
                "session": f"community/{name}/session.jsonl",
                "events": f"community/{name}/session.jsonl.events.jsonl",
            }
            return name, home, document

        def publish_members(self, document):
            temporary = MEMBERS.with_name(token + ".json")
            files.append(temporary)
            temporary.write_text(json.dumps(document))
            temporary.chmod(members_mode)
            os.replace(temporary, MEMBERS)

    try:
        yield House()
    finally:
        # Stop releasing/marking first, then kill any blocked test readers.
        try:
            systemctl("kill", "--kill-whom=main", "--signal=SIGCONT", GATE, check=False)
            systemctl("stop", GATE)
        finally:
            for child in children:
                if child.poll() is None:
                    child.kill()
                child.communicate(timeout=3)
            if MEMBERS.read_bytes() != original_members:
                restore = MEMBERS.with_name(token + ".restore")
                restore.write_bytes(original_members)
                restore.chmod(members_mode)
                os.replace(restore, MEMBERS)
            for p in files:
                p.unlink(missing_ok=True)
            for p in new_homes:
                p.rmdir()
            systemctl("start" if states["scribe"] else "stop", SCRIBE)
            systemctl("start" if states["gate"] else "stop", GATE)


def assert_allowed(child, timeout):
    stdout, stderr = child.communicate(timeout=timeout)
    assert child.returncode == 0, stderr
    result = json.loads(stdout)
    assert result["allowed"] is True
    return result["elapsed"]


# PTRACE_SYSCALL on Linux x86-64: no production hook or repository code as root.
# On a fanotify read's syscall-exit stop, its permission events are delivered.
# To exercise R1's failure path, replace only the second fanotify write syscall
# with an invalid syscall, then supply -EBADF at its exit stop.
TRACE_HELPER = r'''
import ctypes, errno, json, os, signal, struct, sys
pid, fanfd, mode = int(sys.argv[1]), int(sys.argv[2]), sys.argv[3]
libc = ctypes.CDLL(None, use_errno=True)
libc.ptrace.restype = ctypes.c_long
class Registers(ctypes.Structure):
    _fields_ = [(name, ctypes.c_ulonglong) for name in (
        'r15 r14 r13 r12 rbp rbx r11 r10 r9 r8 rax rcx rdx rsi rdi orig_rax '
        'rip cs eflags rsp ss fs_base gs_base ds es fs gs').split()]
def ptrace(op, addr=0, data=0):
    ctypes.set_errno(0)
    result = libc.ptrace(op, pid, ctypes.c_void_p(addr), data)
    if result == -1 and ctypes.get_errno():
        raise OSError(ctypes.get_errno(), os.strerror(ctypes.get_errno()))
    return result
def regs():
    r = Registers()
    ptrace(12, data=ctypes.byref(r))
    return r
def memory(addr, size):
    out = bytearray()
    for offset in range(0, size, 8):
        out.extend(struct.pack('Q', ptrace(2, addr + offset) & ((1 << 64) - 1)))
    return bytes(out[:size])
ptrace(16)  # ATTACH
os.waitpid(pid, 0)
ptrace(0x4200, data=0x1)  # SETOPTIONS, PTRACE_O_TRACESYSGOOD
# Remove the deliberate group stop used to queue the test readers.
os.kill(pid, signal.SIGCONT)
writes, injected = 0, False
while True:
    ptrace(24)  # SYSCALL
    _, status = os.waitpid(pid, 0)
    if os.WIFEXITED(status) or os.WIFSIGNALED(status):
        print(json.dumps({'exited': True, 'writes': writes,
                          'exit_code': os.WEXITSTATUS(status) if os.WIFEXITED(status) else None}), flush=True)
        break
    if os.WSTOPSIG(status) != (signal.SIGTRAP | 0x80):
        continue
    info = (ctypes.c_ubyte * 128)()
    ptrace(0x420e, 128, ctypes.byref(info))  # GET_SYSCALL_INFO
    if info[0] not in (1, 2):
        continue
    entering = info[0] == 1
    r = regs()
    if not entering and r.orig_rax == 0 and r.rdi == fanfd and 0 < r.rax < (1 << 63):
        raw, offset, events = memory(r.rsi, r.rax), 0, []
        while offset < len(raw):
            length, vers, reserved, meta, mask, fd, opener = struct.unpack_from('IBBHQii', raw, offset)
            if length < 24:
                raise RuntimeError('invalid fanotify metadata')
            events.append({'fd': fd, 'pid': opener, 'mask': mask})
            offset += length
        print(json.dumps({'delivered': events}), flush=True)
        if mode == 'hold':
            # Remain at syscall exit; SIGKILL of the tracee is observable by waitpid.
            os.waitpid(pid, 0)
            break
    if entering and r.orig_rax == 1 and r.rdi == fanfd:
        writes += 1
        if mode == 'fail-second' and writes == 2:
            r.orig_rax = (1 << 64) - 1
            ptrace(13, data=ctypes.byref(r))
            injected = True
    elif not entering and injected:
        r.rax = ((1 << 64) - errno.EBADF)
        ptrace(13, data=ctypes.byref(r))
        injected = False
'''


@contextmanager
def trace_gate(pid, mode):
    assert platform.machine() == "x86_64", "the fault-injection harness requires Linux x86-64"
    fds = fanotify_info(pid)
    assert len(fds) == 1, "R2 requires one unduplicated fanotify group fd"
    tracer = subprocess.Popen(["sudo", "-n", sys.executable, "-u", "-c", TRACE_HELPER,
                               str(pid), str(next(iter(fds))), mode],
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE, bufsize=0)
    try:
        yield tracer
    finally:
        if tracer.poll() is None:
            # Killing the gate releases readers and lets a held tracer finish.
            sudo("kill", "-KILL", pid, check=False)
        try:
            tracer.communicate(timeout=3)
        except subprocess.TimeoutExpired:
            tracer.kill()
            tracer.communicate(timeout=3)


def trace_line(tracer, timeout=3):
    assert select.select([tracer.stdout], [], [], timeout)[0], "no syscall trace result"
    line = tracer.stdout.readline()
    assert line, "syscall tracer exited without a result"
    return json.loads(line)


@contextmanager
def scribe_endpoint(mode):
    # The house user cannot traverse RuntimeDirectory. Keep endpoint setup,
    # queue filling and cleanup in a root helper, including the sender socket.
    code = r'''
import json, os, pathlib, pwd, socket, sys
path, mode = pathlib.Path(sys.argv[1]), sys.argv[2]
created = not path.parent.exists()
bound = None
try:
    if created:
        owner = pwd.getpwnam('hamutay-camera')
        path.parent.mkdir(mode=0o750)
        os.chown(path.parent, owner.pw_uid, owner.pw_gid)
        path.parent.chmod(0o750)
    path.unlink(missing_ok=True)
    if mode != 'never_started':
        bound = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
        bound.bind(str(path))
        if mode == 'stopped':
            bound.close()
            bound = None
        else:
            with socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM) as sender:
                sender.setblocking(False)
                for _ in range(100000):
                    try:
                        sender.sendto(b'{}', str(path))
                    except BlockingIOError:
                        break
                else:
                    raise RuntimeError('could not fill the Unix datagram queue')
    print(json.dumps({'ready': True, 'pid': os.getpid()}), flush=True)
    sys.stdin.buffer.read(1)
finally:
    if bound is not None:
        bound.close()
    path.unlink(missing_ok=True)
    if created:
        path.parent.rmdir()
'''
    helper = subprocess.Popen(["sudo", "-n", sys.executable, "-u", "-c", code, str(SOCKET), mode],
                              stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    helper_pid = None
    try:
        assert select.select([helper.stdout], [], [], 5)[0], "endpoint helper did not start"
        line = helper.stdout.readline()
        assert line, "endpoint helper exited: " + helper.stderr.read().decode()
        ready = json.loads(line)
        helper_pid = ready["pid"]
        assert ready["ready"] is True
        yield
    finally:
        try:
            _, stderr = helper.communicate(input=b"\n", timeout=3)
        except subprocess.TimeoutExpired:
            sudo("kill", "-KILL", helper_pid or helper.pid, check=False)
            helper.communicate(timeout=3)
            raise
        assert helper.returncode == 0, stderr.decode()


def test_t1_gate_starts_and_allows_every_home_without_scribe(house):
    systemctl("stop", GATE)
    systemctl("stop", SCRIBE)
    homes = [ROOT / "community" / name for name in json.loads(MEMBERS.read_bytes())["members"]]
    probes = [house.probe(home) for home in homes]
    # Absent pathname, stopped scribe's stale pathname, and a bound/full queue
    # exercise ENOENT, ECONNREFUSED, and EAGAIN respectively.
    for mode in ("never_started", "stopped", "queue_full"):
        systemctl("stop", GATE)
        with scribe_endpoint(mode):
            try:
                house.start_gate()
                wait_for(lambda: {h.stat().st_ino for h in homes} <= marked_inodes(), 5, "every home's fanotify mark")
                for path in probes:
                    assert_allowed(house.reader(path), timeout=7)
            finally:
                systemctl("stop", GATE)


def test_t2_gate_death_releases_queued_and_delivered_events_within_one_second(house):
    path = house.probe()
    for delivered in (False, True):
        pid = house.start_gate()
        wait_for(lambda: path.parent.stat().st_ino in marked_inodes(), 5, "home mark")
        sudo("kill", "-STOP", pid)
        first = house.reader(path)
        time.sleep(0.05)
        assert first.poll() is None, "queued open did not wait on the gate"
        if delivered:
            with trace_gate(pid, "hold") as tracer:
                event = trace_line(tracer)
                assert first.pid in [e["pid"] for e in event["delivered"]]
                second = house.reader(path)
                time.sleep(0.05)
                assert second.poll() is None
                killed = time.monotonic()
                sudo("kill", "-KILL", pid)
                for child in (first, second):
                    assert_allowed(child, timeout=max(0.001, 1 - (time.monotonic() - killed)))
                assert time.monotonic() - killed < 1
        else:
            killed = time.monotonic()
            sudo("kill", "-KILL", pid)
            assert_allowed(first, timeout=max(0.001, 1 - (time.monotonic() - killed)))
            assert time.monotonic() - killed < 1


def test_t3_watchdog_alone_releases_blocked_open_within_seven_seconds(house):
    path = house.probe()
    pid = house.start_gate()
    wait_for(lambda: path.parent.stat().st_ino in marked_inodes(), 5, "home mark")
    stopped = time.monotonic()
    sudo("kill", "-STOP", pid)
    child = house.reader(path)
    assert_allowed(child, timeout=max(0.001, 7 - (time.monotonic() - stopped)))
    assert time.monotonic() - stopped < 7
    wait_for(lambda: gate_pid() not in (0, pid), 3, "automatic gate restart")


def test_t4_mid_batch_response_failure_exits_and_releases_every_reader(house):
    path = house.probe()
    pid = house.start_gate()
    wait_for(lambda: path.parent.stat().st_ino in marked_inodes(), 5, "home mark")
    sudo("kill", "-STOP", pid)
    children = [house.reader(path) for _ in range(3)]
    time.sleep(0.05)
    assert all(c.poll() is None for c in children)
    with trace_gate(pid, "fail-second") as tracer:
        event = trace_line(tracer)
        assert {c.pid for c in children} <= {e["pid"] for e in event["delivered"]}, "need a multi-event batch"
        result = trace_line(tracer)
        assert result == {"exited": True, "writes": 2, "exit_code": 70}
        for child in children:
            assert_allowed(child, timeout=1)


def test_t5_twenty_concurrent_readers_meet_caller_latency_bounds_for_sixty_seconds(house):
    house.start_db()
    house.start_scribe()
    path = house.probe()
    house.start_gate()
    wait_for(lambda: path.parent.stat().st_ino in marked_inodes(), 5, "home mark")
    previous = {s["_key"] for s in statuses()}
    barrier = threading.Barrier(21)
    deadline = [None]

    def read_loop():
        samples = []
        barrier.wait()
        while time.monotonic() < deadline[0]:
            began = time.perf_counter_ns()
            fd = os.open(path, os.O_RDONLY)
            elapsed = time.perf_counter_ns() - began
            os.close(fd)
            samples.append(elapsed)
        return samples

    # Threads are independent concurrent callers; measure around open(), including
    # scheduling and permission wait. A stop timer bounds a broken gate's test.
    release = threading.Timer(68, lambda: systemctl("stop", GATE))
    release.daemon = True
    release.start()
    try:
        with ThreadPoolExecutor(max_workers=20) as pool:
            futures = [pool.submit(read_loop) for _ in range(20)]
            deadline[0] = time.monotonic() + 60
            barrier.wait()
            samples = [sample for f in futures for sample in f.result(timeout=68)]
    finally:
        release.cancel()
    samples.sort()
    assert len(samples) >= 20
    p99 = samples[(99 * len(samples) + 99) // 100 - 1]
    assert p99 < 2_000_000, f"caller p99 {p99 / 1e6:.3f} ms"
    assert samples[-1] < 50_000_000, f"caller max {samples[-1] / 1e6:.3f} ms"
    alive = wait_for(lambda: [s for s in fresh_statuses(previous) if s["kind"] == "alive"], 65, "scribe alive while writing")
    assert any(s.get("counts", {}).get("records_written", 0) > 0 for s in alive)


def test_t6_new_member_marked_within_ten_seconds_and_coverage_recorded(house):
    house.start_db()
    house.start_scribe()
    house.start_gate()
    previous = {s["_key"] for s in statuses()}
    name, home, document = house.new_member()
    path = house.probe(home)
    started = time.monotonic()
    house.publish_members(document)
    wait_for(lambda: home.stat().st_ino in marked_inodes(), max(0.001, 10 - (time.monotonic() - started)), "new member mark within 10 s")
    assert time.monotonic() - started <= 10
    assert_allowed(house.reader(path), timeout=7)

    def coverage_for_home():
        return [s for s in fresh_statuses(previous) if s["kind"] == "coverage"
                and [home.stat().st_dev, home.stat().st_ino, str(home)] in s["coverage"]["marks"]]

    # Coverage retransmission has no guarantee under arbitrary loss. This harness
    # grants 65 s on a healthy channel, separately from the 10 s marking bound.
    assert wait_for(coverage_for_home, 65, "completed coverage for " + name)


def test_t7_short_gate_restart_records_restart_and_closed_gate_gap(house):
    house.start_db()
    house.start_scribe()
    house.start_gate()
    # Ensure there was a prior beat, rather than relying on a sleep after READY.
    previous = {s["_key"] for s in statuses()}
    wait_for(lambda: [s for s in fresh_statuses(previous) if s["kind"] == "alive"], 65, "scribe alive with gate beats")
    previous = {s["_key"] for s in statuses()}
    began = time.monotonic()
    house.start_gate()
    assert time.monotonic() - began < 10, "test must exercise a short restart"

    def restart_and_gap():
        rows = fresh_statuses(previous)
        restarts = [s for s in rows if s["kind"] == "gate_restart"]
        gaps = [s for s in rows if s["kind"] == "gap" and s.get("scope") == "gate" and s.get("gap_to") is not None]
        return (restarts, gaps) if restarts and gaps else None

    restarts, gaps = wait_for(restart_and_gap, 65, "gate_restart and closed gate gap")
    assert restarts[0].get("counts") is not None
    assert any(0 <= (datetime.fromisoformat(s["gap_to"]) - datetime.fromisoformat(s["gap_from"])).total_seconds() < 10 for s in gaps)


def test_t8_directory_denies_house_user_and_scribe_checks_kernel_sender_uid(house):
    house.start_db()
    systemctl("stop", GATE)
    house.start_scribe()
    assert systemctl("show", SCRIBE, "--property=User", "--value").stdout.strip() == "hamutay-camera"
    directory = json.loads(sudo(sys.executable, "-c", """import json, os, pwd, stat, sys
s = os.stat(sys.argv[1])
print(json.dumps({'owner': pwd.getpwuid(s.st_uid).pw_name, 'mode': stat.S_IMODE(s.st_mode)}))
""", SOCKET.parent).stdout)
    assert directory == {"owner": "hamutay-camera", "mode": 0o750}

    # house enforces uid 1000. This must fail on directory traversal, before
    # the scribe can see or authenticate the payload.
    with socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM) as sender:
        with pytest.raises(PermissionError) as refused:
            sender.sendto(b"{}", str(SOCKET))
    assert refused.value.errno == errno.EACCES

    def send_as(messages, identity):
        # Connect as root, then drop *all* uid/gid privileges before sending.
        # A connected datagram socket needs no subsequent pathname traversal;
        # SO_PASSCRED still supplies the uid of the process doing the send.
        # No production directory or socket permissions are changed.
        code = r'''
import json, os, pwd, socket, sys
path, messages, identity = sys.argv[1], json.loads(sys.argv[2]), sys.argv[3]
with socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM) as sender:
    sender.settimeout(3)
    sender.connect(path)
    if identity != 'root':
        account = pwd.getpwnam(identity)
        assert account.pw_uid not in (0, 1000)
        os.setgroups([])
        os.setgid(account.pw_gid)
        os.setuid(account.pw_uid)
        assert os.getuid() == os.geteuid() == account.pw_uid
    sent = 0
    error = None
    for message in messages:
        payload = json.dumps(message, separators=(',', ':')).encode()
        try:
            assert sender.send(payload) == len(payload)
        except PermissionError as exc:
            error = exc.errno
            break
        sent += 1
print(json.dumps({'uid': os.getuid(), 'sent': sent, 'errno': error}))
'''
        return json.loads(sudo(sys.executable, "-c", code, SOCKET, json.dumps(messages), identity).stdout)

    def beat(gen):
        return {
            "v": 1, "kind": "beat", "gen": gen, "seq": 0,
            "t": datetime.now(timezone.utc).isoformat(timespec="microseconds"),
            "opened": 0, "self_reads": 0, "answered": 0, "dropped": 0,
            "coverage_version": hashlib.sha256(b'{"marks":[],"unmarked":[]}').hexdigest(),
            "marks_count": 0,
        }

    # Two unique forged generations give observable proof that root sends from
    # a process other than the gate are accepted, even with no prior gate beat.
    previous = {s["_key"] for s in statuses()}
    first_gen, accepted_gen, rejected_gen = (str(uuid.uuid7()) for _ in range(3))
    root_beats = [beat(first_gen), beat(accepted_gen)]
    assert send_as(root_beats, "root") == {"uid": 0, "sent": 2, "errno": None}

    def accepted_beats():
        rows = fresh_statuses(previous)
        # R7 promises these gap endpoints; the status schema leaves gen optional.
        return (any(s["kind"] == "gate_restart" for s in rows)
                and any(s["kind"] == "gap" and s.get("scope") == "gate"
                        and s.get("gap_from") is not None and s.get("gap_to") is not None
                        and datetime.fromisoformat(s["gap_from"]) == datetime.fromisoformat(root_beats[0]["t"])
                        and datetime.fromisoformat(s["gap_to"]) == datetime.fromisoformat(root_beats[1]["t"])
                        for s in rows))

    wait_for(accepted_beats, 65, "acceptance of a root helper's forged beats")

    door = next(iter(json.loads(MEMBERS.read_bytes())["members"]))
    path = str(ROOT / "community" / door / (".camera-validation-" + rejected_gen))
    forged_open = {
        "v": 1, "kind": "open", "gen": rejected_gen, "seq": 0,
        "t": datetime.now(timezone.utc).isoformat(timespec="microseconds"),
        "path": path, "path_sha256": hashlib.sha256(path.encode()).hexdigest(),
        "door": door, "truncated": False,
        "reader": {
            "pid": os.getpid(), "start_time": 123456, "reused": False, "uid": 1000,
            "exe": sys.executable, "comm": "camera-validation", "cgroup": "/",
            "cwd": str(ROOT), "ancestors": [], "proc_readable": True,
            "start_time_before": 123456, "start_time_after": 123456,
            "attribution": "complete",
        },
    }
    previous = {s["_key"] for s in statuses()}
    result = send_as([forged_open], "nobody")
    assert result["uid"] not in (0, 1000)
    if result["errno"] in (errno.EACCES, errno.EPERM):
        warnings.warn("T8 verified uid-1000 EACCES and root-beat acceptance only: "
                      "this host denies the connected non-root send; "
                      "rejected_sender/entries checks omitted without changing production modes.")
        return
    assert result["sent"] == 1 and result["errno"] is None
    # An alive flushes all earlier buffered opens (R7). Observe rejection in
    # that cycle before checking that the unique forged entry was not stored.
    wait_for(lambda: [s for s in fresh_statuses(previous)
                      if s["kind"] == "alive" and s.get("counts", {}).get("rejected_sender", 0) >= 1],
             65, "rejected_sender in the next scribe alive")
    assert database_rows("FOR e IN entries FILTER e.gen == @gen RETURN e", {"gen": rejected_gen}) == []
    assert not [s for s in fresh_statuses(previous) if s.get("gen") == rejected_gen], "rejected sender changed gate status"
