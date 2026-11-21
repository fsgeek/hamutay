# Camera r3: Codex review, round two (2026-11-03)

Read-only review by Codex of r3 (b8a3127) against round one (`…-review-1.md`), copied from its report.
r4 answers it. Codex's own limits: no privileged commands; systemd bus access denied in its sandbox; the
cgroup path came from sysfs, not from a heartbeat process's /proc.

## Round-one dispositions
B1 partly (exhaustion untested). B2 resolved. B3 resolved. S1 partly (gate-side scanning and batches
unbounded). S2 resolved. S3 resolved. S4 partly (wrong cgroup path). S5 partly (no revalidation or
attribution-state rules). S6 partly (crash-loss claim incomplete). S7 resolved. S8 partly (gate outages
invisible). S9 partly (spool-write failure, replay retirement). S10 resolved. S11 partly (blind-test
ambiguities). S12 resolved. M1 resolved.

## New, Blocking
N-B1. Opener access mode is unavailable: fanotify_init(2) has the listener choose event-fd flags and
fanotify(7) metadata carries no opener mode; inspecting the event fd could label a write-only open as read.
N-B2. FIFO startup and reconnection: RuntimeDirectory= creates a directory, not a FIFO; O_WRONLY|O_NONBLOCK
on a FIFO with no reader fails ENXIO (fifo(7)), so the gate could restart-loop without coverage; runtime
directory removal can leave the scribe on a stale inode.

## New, Significant
N-S1. R3's path omits the template slice: observed `…/app.slice/app-hamutay\x2dheartbeat.slice/hamutay-heartbeat@elder.service`.
N-S2. A live scribe can conceal a dead gate; gate health needs its own reporting.
N-S3. Non-blocking pipe writes above PIPE_BUF (4096) can be partial; framing breaks.
N-S4. The counter file's path, permissions, format and reset semantics are unspecified.
N-S5. Watchdog during legitimate long work (start, scan, large batch) is undefined.
N-S6. A dropped coverage line is never resent.
N-S7. The crash-loss claim is false for some schedules (buffered open before the last alive, crash after).
N-S8. Not every requirement is testable: partial vs lost attribution, the message/timestamp contract,
spool-write failure, window clock.
