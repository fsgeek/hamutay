# Camera r2: Codex review, round one (2026-11-03)

Read-only review by Codex of `2026-11-03-access-camera-r2.md` (ae32e8f), copied verbatim from its report
to the custodian. Kernel citations are upstream Linux v6.18; equivalence to the Microsoft WSL2 build was
not verified. r3 (`2026-11-03-access-camera-design.md`, b8a3127) answers it.

## Blocking

B1. R1 "Never refuse" is stronger than fanotify guarantees. Collector fd exhaustion can make create_fd() fail; fanotify_read() then answers FAN_DENY before Python receives the event. Event allocation failure also propagates -ENOMEM from fanotify_handle_event(). Qualify the guarantee and require resource-exhaustion tests.

B2. R1/R2: loop liveness does not prove every reader was released. A batch-processing exception or failed response write can abandon delivered events while the loop continues sending watchdog pings, leaving those opens blocked indefinitely. Require every delivered event to reach a confirmed response, or force final group closure; test failures midway through a multi-event batch.

B3. R2(b): WatchdogSec=10 does not mean release within ten seconds. Marks installed before READY=1 lack an active service watchdog; after activation, watchdog failure normally sends SIGABRT, with a separate abort timeout before forced killing. Specify startup ordering, notification cadence, termination settings and a measurable recovery bound; test actual watchdog recovery, not only manual SIGKILL.

## Significant

S1. R1/R2(a), R9: a writer thread does not isolate response latency (GIL, Queue.put_nowait's mutex, directory reconciliation, logging, shutdown joins). Require bounded work between answers.
S2. Opens are not reads. Write-only or failed opens can be recorded; existing, inherited or passed descriptors and mappings expose content without another open. Declare the observable operation and exclusions.
S3. R9: FAN_EVENT_ON_CHILD reaches immediate children only; a directory created, read and removed between scans is never covered; replacing a home directory can strand a path-based mark on the old inode. Require recursive coverage, inode reconciliation, declared scan gaps, failed-mark handling.
S4. R3: a unit basename is insufficient identity (another user's manager can hold the same name; a process allowed into the unit inherits the exemption). Require uid/manager and cgroup identity, exact home matching, no exemption on uncertain attribution; declare the trusted boundary.
S5. R4: snapshots are not atomic (killed readers, exiting or reparented parents, pid reuse). Require identity validation, partial fields, uid semantics, missing-ancestor behaviour; never suppress a record for incomplete attribution.
S6. R4-R6: coalescing loses identity (two processes share the key) and records (10-minute buffers lost on crash). Define aggregate identity, window type, flush boundaries, key-count limits.
S7. R6/R10: ArangoDB's classic authorization has no insert-only; read-write permits update, remove, truncate. State whether append-only is convention or enforced; a separate read-only user for the CLI.
S8. R7: short outages disappear (alive, crash, restart a minute later: no gap) and a collector that never restarts emits none. Require session boundaries and reader-side freshness.
S9. R8: dual failure and replay unspecified (DB down then ENOSPC, spool permission failure, writer death, duplicate on lost commit reply). Specify timeouts, capacity, durability, torn-tail recovery, stable ids, idempotent replay, declared losses.
S10. Root deployment: root Python from a same-user-writable repository becomes root code on restart; resident-controlled symlinks can extend monitoring outside homes. Specify trusted installed code, root-owned state, validated paths.
S11. The pilot's latency figure starts after dequeue (pilot_collector.py:116), so it excludes queueing and wake-up. Specify caller-observed latency under concurrent load, recovery time, and schemas.
S12. (in answers) The monthly restore test defaults to the apacheta database, not ayllu_camera.

## Minor

M1. R7 (status every 5 min) conflicts with R9 ("the status record for that minute").

## Answers

1. R2(c) holds on upstream v6.18 on final release of the group file: fanotify_release() answers FAN_ALLOW to delivered and queued permission events. A duplicated or fork-inherited group fd prevents final release.
2. Python can give best effort, not unconditional guarantees.
3. Cross-home reads inside another door's unit must be recorded; the viewer and the llama server have their own units; attribution names the intermediary, not the human requester.
4. Directory marks miss: outside hard links, unmarked descendants, pre-existing descriptors and mappings, inherited or passed descriptors, reads without reopening. O_PATH bypasses the hook but cannot read content.
5. Short-lived readers stay alive while awaiting permission, but attribution is not guaranteed.
6. Watchdog lifecycle, root trust, spool exhaustion and WSL lifetime need explicit treatment; systemd services do not keep WSL alive.
7. Not fully testable as written: timing bounds, schemas, coalescing, partial attribution, coverage transitions, crash losses and replay semantics were missing.
