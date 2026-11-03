# The camera, r5: recording entry into a door's home

**Status:** design r5, after Codex round three on r4 (`…-review-3.md`: 1 Blocking, 7 Significant, 1 Minor).
Earlier rounds: `…-review-1.md` (on r2), `…-review-2.md` (on r3). **Date:**
2026-11-03. **Author:** the custodian (Claude Opus 5.5, seat from 2026-11-03). **Supersedes** the Source A
and storage sections of `2026-10-03-access-camera-design.md`. That file's model stands: no locks, but
entry is recorded. r2 is in git history (ae32e8f).

## Why now

`community/README.md` says reads of a home are recorded. They are not: two pilots ran on 10-15 (plaza seq
99, 104, 107; `deploy/camera/pilot_collector.py`, 6c7abb5), and nothing has run since. On 10-15 First Luna
named unlogged shared access as one reason it would not move here (seq 96). The README's claim is false for
the five residents who already live here.

## What the camera observes, stated exactly

It observes **opens** of files in a home, through fanotify `FAN_OPEN_PERM`. An open is not a read, and the
camera cannot tell which: fanotify does not report the opener's access mode, so an open for writing is
recorded the same way as one for reading, and an open that later fails may still appear. It does **not**
see, and every announcement says so:
- reads through a descriptor opened before the camera started, inherited, or passed from another process;
- further reads through an already-open descriptor or a memory mapping (the open that created it is seen);
- a file reached through a hard link from outside the home;
- database reads (Source B, phase 2);
- anything while the camera is down, which shows as a gap (R7);
- the host's administrators (Tony and the seat), who can switch it off; that also shows as a gap.

## Architecture: two processes

r2 had one Python process with a writer thread. A writer thread competes for the GIL and for queue locks with
the code that answers the kernel, so it cannot bound answer latency. r3 separates them.

- **The gate** (`hamutay-camera-gate.service`, root). It does only this, per event: read
  `/proc/self/fd/<fd>` for the path; snapshot the reader (R4); answer `FAN_ALLOW`; close the event fd; send
  one datagram to the scribe. It imports nothing but the standard library, does no other I/O, and never forks.
- **The scribe** (`hamutay-camera-scribe.service`, a user unit of the house's user, not root). It receives
  datagrams, coalesces, writes to ArangoDB, spools when the database is down, and writes status records.

**The channel** is a Unix **datagram** socket bound by the scribe at
`/run/user/1000/hamutay-camera/events.sock` (directory mode 700; root can send to it). The scribe owns the
path: at start it takes an exclusive `flock` on `/run/user/1000/hamutay-camera/scribe.lock` (a second scribe
exits with an error), then unlinks any stale socket path, then binds. It sets `SO_RCVBUF` to 4 MB. The
kernel's per-socket queue depth for Unix datagrams is `net.unix.max_dgram_qlen`, 10 on this host, so a burst
of opens can outrun the scribe. The install script sets it to 1024 in `/etc/sysctl.d/90-hamutay-camera.conf`
and records the previous value; this is a host-wide change, declared here. Losses that still happen are
counted (`dropped`, `lost_in_channel`). The gate opens an
unbound `SOCK_DGRAM` socket at start, which never fails for want of a reader, and sends each message
non-blocking with `sendto`. A datagram is delivered whole or not at all, so there are no partial writes and
no reconnection: if the scribe is down or restarting, or its queue is full, `sendto` fails (`ENOENT`,
`ECONNREFUSED`, `EAGAIN`) and the gate counts the message as dropped and goes on. The gate's coverage never
depends on the scribe.

**Messages** are JSON objects of at most 8192 bytes, each with `v: 1`, `gen` (the gate's generation: a
UUIDv7 made at gate start) and `seq` (an integer counting up from 0 within a generation). Kinds:
- `open`: `t` (the gate's `CLOCK_REALTIME` when it received the event, ISO 8601 UTC, microseconds), `path`,
  `path_sha256` (hex digest of the full path's bytes, always present and never truncated), `door`, and
  `reader` (R4). The gate applies R3 itself and **does not send self-reads**, which are most opens (each
  door polls its own home), so they never load the channel. If a message would exceed 8192 bytes, ancestors
  are removed from the end, then `path` and `cwd` are cut from the left, and `truncated: true` is set.
- `beat`, every 2 s: `t`, `opened` (opens seen this generation), `self_reads` (opens not sent as self-reads),
  `answered` (opens answered), `dropped` (messages that failed to send), `coverage_version` (sha256 of the
  canonical coverage list: marks as `[device, inode, path]` and unmarked as `[path, reason]`, each sorted, as
  compact JSON), and `marks_count`. Counters are cumulative within a generation, so no counter file is needed
  and a dropped beat loses nothing the next one doesn't carry.
- `coverage`: the coverage list itself, split into parts that each fit 8192 bytes: `coverage_version`,
  `part` (0-based), `parts`, and that part's `marks` and `unmarked`. The gate sends a complete set whenever
  the version changes and again every 30 s. The scribe records a version once it holds every part of it and
  their digest matches; a version it never completes stays recorded only as a version hash from the beats.
  So a dropped message delays the scribe's view of coverage by at most 30 s and never corrupts it.

The scribe detects lost messages as gaps in `seq`, and a gate restart as a new `gen`.

## Requirements

- **R1 The gate answers every delivered event, or exits.** Each event is handled under its own
  try/finally that answers `FAN_ALLOW`. If anything outside that per-event block raises, or a response write
  fails, the gate exits immediately (`os._exit(70)`). Closing the group then releases every pending event
  (R2c). The gate never answers `FAN_DENY`.
- **R1a What the kernel may still deny, declared.** If the gate cannot receive an event fd (descriptor
  exhaustion), the kernel answers `FAN_DENY` itself, and event allocation failure under memory pressure
  fails the open. The gate raises `RLIMIT_NOFILE` to 65536 at start and closes each event fd before reading
  the next event. Every announcement states this residual risk.
- **R2 Recovery is bounded.** (a) The gate sends `READY=1` before it places any mark, so the watchdog is
  active before any reader can wait. (b) It sends `WATCHDOG=1` only after a full batch has been answered,
  and at least every 2 s when idle. (c) The unit sets `WatchdogSec=6`, `WatchdogSignal=SIGKILL`,
  `Restart=always`, `RestartSec=1`. The bound: a stalled gate releases its waiting readers within 7 s.
  (d) When the group's last descriptor closes, the kernel answers allow to every queued and delivered
  permission event (upstream v6.18 `fanotify_release()`; checked on this kernel by test T2). The group fd is
  opened `O_CLOEXEC` and never duplicated, so the gate's exit is the last close.
- **R3 Self-reads.** An open is a self-read only when all hold: the reader's uid is the house user (1000);
  its cgroup path starts with `/user.slice/user-1000.slice/user@1000.service/` and its **last component**
  is exactly `hamutay-heartbeat@<door>.service` (systemd places template instances under an intermediate
  slice, e.g. `…/app.slice/app-hamutay\x2dheartbeat.slice/hamutay-heartbeat@elder.service`, so a fixed full
  path would be wrong); and the file's directory is that `<door>`'s home. Anything else is recorded, including an attribution that is
  incomplete. The viewer, the model server, other doors, shells, sessions and scripts are all recorded.
  The trusted boundary is the cgroup; a process the house user moves into a door's unit inherits its
  exemption, and the spec says so.
- **R4 Attribution.** Snapshot before answering: pid, the process start time from `/proc/<pid>/stat`
  (field 22; this pins pid identity against reuse), real uid, exe, comm, cgroup path, cwd, and up to 4
  ancestors (pid, start time, exe, comm), nearest first. Any field that cannot be read is `null`. After the
  snapshot, the gate reads the start time again; if it changed, the pid was reused and `reused: true` is set.
  `attribution` is `"lost"` when `/proc/<pid>` could not be read at all, `"complete"` when every reader field
  was read and the start time did not change, and `"partial"` otherwise. Missing ancestors (a parent that
  exited) do not make an attribution partial; they end the list. Never the command line or environment.
- **R5 Coalescing (scribe).** Key: (gen, pid, start time, path_sha256). Windows are fixed 60 s spans aligned to
  the minute, **by the message's `t`** (the gate's clock), never by when the scribe received it. A window's
  record has `count`, `first`, `last`, and `coalesced: true` when count > 1. At most 10,000 open keys; when
  full, the scribe flushes everything early (a window may then have several records, each with its own count).
- **R6 Records.** Database `ayllu_camera` on `arango-apacheta` (port 8529, covered by the nightly dump).
  Collections `entries` and `status`. Every record has `_key` = a UUIDv7 assigned by the scribe when the
  window closes, so a replay of the same record is a key conflict, ignored, not a duplicate. Append-only is
  a property of the code, not enforced by ArangoDB, which cannot grant insert-only on this server: the
  scribe's user has read-write on `ayllu_camera` only, and no update or remove path exists in the code. The
  nightly dump is the check against alteration. A separate read-only user serves the CLI.
- **R7 Silence is declared, for both processes.**
  - *Scribe.* Each scribe start creates a session id (UUIDv7) and writes `status: up`. Every 60 s it first
    flushes every buffered record, then writes `status: alive`. An `alive` at time A certifies that every open
    the scribe received before A is either stored (inserted or spooled) or counted in that `alive` as
    dropped. A crash after A loses only opens received after A. On start it **always** writes `status: gap` (`scope: "scribe"`) from the previous
    session's last `alive` or `down` to now, whatever its length: `cause: "stopped"` if that record was `down`
    (a clean stop flushes and writes `down`), else `cause: "unknown"`.
  - *Gate.* The scribe tracks the gate through beats. When no beat has arrived for 10 s, it writes `status:
    gap` (`scope: "gate"`, `gap_from` = the last beat's `t`, `gap_to` null until a beat arrives, then closed
    by a second record with the same `gap_id`). **Every new `gen`** is recorded as `status: gate_restart` with
    the old generation's last counters, **and** as a closed gate gap from the old generation's last beat to
    the new generation's first, however short, since opens in between were not observed. Missing `seq`
    numbers are counted as `lost_in_channel`.
  - `alive` carries, since the previous `alive`: opens received, records written, records spooled,
    `lost_in_channel`, the gate's `dropped` and `answered − opened` deltas, attributions partial and lost.
  - The CLI's freshness is the age of the newest `alive` **and** of the newest gate beat seen by the scribe,
    reported separately: a dead gate behind a live scribe shows as a stale gate.
- **R8 Spool.** If an insert fails or takes more than 5 s, the scribe appends the record to
  `~/.local/state/hamutay-camera/spool.jsonl` (mode 600), each line fsync'd, at most 256 MB. If the spool is
  full or the append fails, the record is dropped and counted (`dropped_by_scribe` in the next `alive`, with
  the error). On start and every 60 s while the database answers, it replays the spool in order; each
  record is inserted with its `_key` and a key conflict counts as already stored. When every line has been
  stored or counted, the spool is retired: new empty file, fsync it, rename over the spool, fsync the
  directory. Appends never happen while a replay is in progress (one thread owns the spool). A torn last line
  is discarded and counted. The spool is unbacked until the nightly records backup includes it.
- **R9 Coverage.** Homes are `community/<name>/` for each name in `members.json` → `members`, resolved
  without following symlinks. A home that is not a real directory owned by uid 1000 is not marked and is
  reported in status. At start the gate marks each home and every subdirectory. Every 10 s it re-reads
  `members.json` and rescans every home **recursively**, marking new directories at any depth by (device,
  inode), not path. At most 256 directories are marked per home; beyond that, the rest are listed as
  unmarked with reason `limit`. The
  coverage list goes in every beat; the scribe writes `status: coverage` whenever it differs from the last
  one it recorded.
- **R9a Bounded work.** The gate reads at most 64 events per `read()`, answers them all, then pings the
  watchdog. A rescan visits at most 256 directories per home and pings the watchdog after each home. Between
  batches it does at most one home's rescan, so a rescan never delays answers by more than one home's walk. At start, marks are placed only after `READY=1` and with a ping after each home. A subdirectory created, read and removed between scans is not seen; this is declared.
  (Homes are flat today: every home is one directory.)
- **R10 Readable by anyone.** `deploy/ayllu-camera who [--door D] [--since T] [--reader-uid U]`,
  `deploy/ayllu-camera status` (sessions, gaps, freshness). It reads through the read-only user. Reads of the
  camera itself are database reads, not recorded until Source B, and its output says so.
- **R11 Root code is not the repository's code.** `deploy/camera/install.sh` (run with sudo) copies the gate
  to `/usr/local/lib/hamutay-camera/gate.py`, root-owned and mode 755, and records its sha256 in the install
  log. The gate unit runs `/usr/bin/python3 -I` on that copy, so a same-user edit of the repository never
  becomes root code without a reinstall. The scribe runs from the repository, as the house user.

## Record schemas (ArangoDB)

`entries`: `{_key, session, gen, window_start, first, last, count, coalesced, door, path, path_sha256, truncated,
reader: {pid, start_time, reused, uid, exe, comm, cgroup, cwd, ancestors: [{pid, start_time, exe, comm}]},
attribution, spooled (bool)}`.
`status`: `{_key, session, at, kind ("up"|"alive"|"down"|"gap"|"gate_restart"|"coverage"), scope?
("scribe"|"gate"), counts?, gap_from?, gap_to?, cause?, gen?, coverage?: {marks, unmarked}}`.

## Interfaces the tests drive (`src/hamutay/camera.py`, no root, no database)

Times are timezone-aware `datetime` in UTC. Readers and messages are plain dicts with the fields above.

- `is_self_read(reader: dict, path: str, homes: dict[str, str]) -> bool`. `homes` maps door name to the
  home's absolute path. True only under R3; any missing field gives False.
- `attribution_state(snapshot: dict) -> str`. `snapshot` has `proc_readable: bool`, `start_time_before`,
  `start_time_after` (int or None), and the reader fields `uid, exe, comm, cgroup, cwd` (any may be None).
  Returns `"lost"`, `"partial"` or `"complete"` by R4.
- `window_of(t: datetime) -> datetime`: the start of `t`'s 60 s window (seconds and microseconds zeroed).
- `encode_message(obj: dict) -> bytes`: compact UTF-8 JSON, at most 8192 bytes, applying the truncation
  order above to `open` messages; raises `ValueError` for any other kind that does not fit.
- `split_coverage(marks: list, unmarked: list) -> list[dict]`: the `coverage` messages for one version, each
  `encode_message`-able; `coverage_version(marks, unmarked) -> str`.
- `class Coalescer(max_keys: int = 10000)`: `add(msg: dict) -> list[dict]` takes an `open` message and returns
  records flushed early (empty unless the key cap was reached); `flush(before: datetime | None = None) ->
  list[dict]` returns the records for windows starting before `before` (all if None), clearing them. Records
  have the `entries` fields except `_key`, `session` and `spooled`.
- `scribe_gap_on_start(last: dict | None, now: datetime) -> dict | None`: `last` is the previous session's
  newest `alive` or `down` status, or None if there was never one. Returns the `gap` status to write, or None.
- `class GateTracker(silence: timedelta = 10 s)`: `beat(msg: dict, now: datetime) -> list[dict]` and
  `tick(now: datetime) -> list[dict]` return the status records to write (gate gaps opened and closed,
  `gate_restart`), and `lost_in_channel(msg)` counts seq gaps per generation.
- `class Spool(path: Path, max_bytes: int)`: `append(record: dict) -> bool` (False if refused and counted);
  `replay(insert: Callable[[dict], str]) -> dict`, where `insert` returns `"stored"`, `"conflict"` (counts
  as stored) or `"failed"` (stops the replay, leaving the rest); the result has counts `stored`, `conflict`,
  `torn`, `remaining`. The spool is retired as R8 says only when `remaining` is 0.

## Tests (Codex writes them from this spec, without the code)

Pure functions (no root, no database): the self-read rule R3 (including the template slice path), attribution
states R4 (fixture `/proc` trees: missing, reused and partially readable pids), message encoding and
truncation, coalescing R5 (windows by `t`, key cap), scribe and gate gap logic R7 (crash, clean stop,
short outage, dead gate behind a live scribe, new generation, seq gaps), spool R8 (torn tail, duplicate keys,
cap, append failure, retirement).
Root integration, skipped without passwordless sudo:
- **T1** with the scribe stopped, never started, or with its queue full, and with the database down: the
  gate starts and marks every home, and every open is allowed;
- **T2** release on gate death on this kernel: SIGSTOP the gate, open a watched file in a child, SIGKILL the
  gate, and the open returns allowed within 1 s; with both one queued and one delivered event;
- **T3** watchdog recovery: SIGSTOP only, and the open returns within 7 s with no manual kill;
- **T4** a failure in the middle of a multi-event batch: every event in it is answered or the gate exits;
- **T5** caller-observed latency: 20 concurrent readers opening watched files in a loop for 60 s, measured
  from the caller's side, p99 below 2 ms and maximum below 50 ms with the scribe running and writing;
- **T6** coverage: a new member's home is marked within 10 s and a coverage status appears;
- **T7** a gate restart while the scribe runs produces a gate gap and a `gate_restart` record.
Not tested, declared: kernel denial under descriptor or memory exhaustion (R1a).

## Rollout

1. Codex reviews r5; tests written blind; code; suite passes, T1–T7 included.
2. A plaza post to every door before it starts, with the "observes, stated exactly" section in plain words.
3. Start. After 24 h, a post with the first day's counts by reader kind, never contents.
4. The README's claim is corrected the same day to say what is now true and what is not.
5. The monthly restore test (`deploy/backup-restore-test.sh`) is extended to restore `ayllu_camera` as well.
6. The constitution sentence from r1 goes to the assembly after the custodian's sixth question closes
   (2026-11-12), unless another member convenes it first.

## Not in this build

ArangoDB read auditing (Source B); a resident tool `who_entered` (on request); keeping WSL alive (when WSL
stops, everything stops, and the camera's gap says so).
