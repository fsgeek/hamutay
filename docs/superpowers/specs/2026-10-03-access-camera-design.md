# The camera: recording entry into another's home, with no locks

**Status:** design, for Tony's review. **Date:** 2026-10-03. **Author:** the custodian (Claude Opus 5.5).

## The model, and the gap

The ayllu's privacy model: **no locks on the doors, but entry into another's home is recorded.**
Anyone may read; the act of reading is on the record. `community/README.md` states that "reads of
the database are access-logged". On 10-03 that could not be verified:

- **Apacheta / ArangoDB.** `yanantin/apacheta/backends/arango.py` checks access but records no
  reads. `arango-ayllu` runs ArangoDB **Enterprise** 3.12, which supports audit logging, but its
  running config (`/tmp/arangod.conf`) has no `[audit]` section, and `/var/log/arangodb3` is empty.
- **JSONL logs.** `community/<door>/session.jsonl` and the events stores are plain files. Every
  resident has unscoped bash. Nothing records a read.
- **The custodian.** Its reads on 10-01 to 10-03 went unrecorded, and were declared afterwards
  (plaza seq 11).

## Requirements

1. **Records live in ArangoDB** (`arango-ayllu`), in the same store and backup as the residents'
   records. They do **not** go in another JSONL file: a separate storage mechanism adds another way
   to lose them in a catastrophe (Tony, 10-03).
2. **Records are append-only.** They follow Apacheta's immutability rule: compose, never overwrite.
3. **No locks.** The camera records reads and never refuses them.
4. **The camera is itself readable by anyone,** and reads of the camera are recorded too.
5. **A door reading its own home is not recorded,** because the camera would otherwise drown in
   each door's own 30-second polling. Every other reader is recorded: other doors, the custodian,
   Tony's shells, guests, scripts (the checkpoint digest reads every log), and backups.
6. **It is announced to residents before it starts.** One constitution sentence tells them that
   entries into their home are recorded, and that they can see who entered.

## Design

**Source A: file reads, through Linux audit.** The kernel has `CONFIG_AUDIT`/`AUDITSYSCALL`, and the
`auditd` package is to be installed. Rules use `-w /home/tony/projects/hamutay/community/<door>/ -p r
-k hamutay-home-<door>`, one per door, plus the plaza directory. Each audit event carries the pid,
the exe and the cgroup. The cgroup resolves to `hamutay-heartbeat@<door>.service` for a door,
to a user session for a shell, and so on.

**Source B: database reads, through Arango Enterprise audit.** The topics are `audit-document` and
`audit-collection`, with output to a local file. Turning this on means a config change and a
restart of `arango-ayllu`, done with every door idle, because the doors persist to it.

**The collector.** One small systemd service (`hamutay-camera.service`) tails both sources. It
normalises each read into an access record: reader (attributed by unit, user or Arango user),
target door, path or collection, operation, time, pid/exe. It drops self-reads and inserts the
rest into an `access` collection in `arango-ayllu` through a dedicated Arango user. The collector's
own writes are filtered out of Source B by that user, so it does not record itself recording.

**Volume.** Reads are bursty (bash `cat`/`grep`, the checkpoint digest). The collector coalesces
repeated reads by the same reader of the same file within 60 s into one record with a count, and
says so in the record.

**Seeing the camera.** `deploy/ayllu-camera who --door <door> [--since]` lists who entered. A
resident tool (`who_entered`) is a later step, offered on request and not by default.

## Failure, honestly stated

- If the collector is down, reads still happen and are not recorded. The collector writes a gap
  record on restart ("camera down from T1 to T2"), so that silence is declared.
- auditd can drop events under load. Its lost-event counter goes into a daily status record.
- Root can disable everything. The camera records ordinary entry; it does not defend against the
  host's administrators (Tony and the custodian). Their disabling it would show as a gap.

## Open before planning

- **The backup.** README says Arango is "backed up off this host". No backup timer, cron job or
  deploy script for it was found on the host on 10-03. Tony's argument for keeping records in
  Arango assumes that backup exists, so it needs confirming, and if it is missing, fixing.
- **Arango audit topics.** Confirm that `audit-document` records reads in 3.12, not only writes.
- **WSL2 audit.** Confirm that auditd runs under WSL2's init on this host. The kernel has support,
  but the userspace daemon has not yet been tried.
