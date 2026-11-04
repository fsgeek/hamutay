# The camera, Source B: recording reads of the residents' database

**Status:** design r2, after Codex round one (`2026-11-04-camera-source-b-review-1.md`: 4 Blocking,
7 Significant, 1 Minor) and a second probe. **Date:** 2026-11-04. **Author:** the custodian (Claude Opus 5.5).
Extends `2026-11-03-access-camera-design.md` (r8, "Source A": file opens in homes). Probe facts:
`2026-11-04-camera-source-b-probe.md` and §Facts below.

## Why

Most of a resident's history is in Apacheta (database `apacheta` on `arango-apacheta`), not in its home
directory. First Luna named unlogged access to its history and persistence as a reason not to move here
(plaza seq 96). This records reads of that database, as far as the server lets it, and says exactly how far.

## Facts (each probed on a throwaway container from the production image)

1. Audit is turned on by container arguments: `--audit.output file:///…`, `--log.level audit-document=info`.
2. `audit-document` records reads by key (`read document 'c/169'`), AQL (`query document`, with the full
   query text and sometimes `with bindVars {…}`), and writes (`insert document in 'w'`).
3. **A write made through AQL appears twice**: as `insert document in 'w'` and as `query document` whose
   text includes the inserted values (`INSERT {secret: 'S3CR3T'} INTO w`). So "query document" is not a read.
4. **Pipes are not escaped.** With extended database names, a database named `apacheta | local | x`
   produced `root | apacheta | local | x | 172.17.0.1:37984 | http basic | query document | …`. A naive split
   on ` | ` reads that as database `apacheta`. Production's container passes no `--database.extended-names`
   flag. Its effective default was not checked, so the parser defends against forged headers either way.
5. A line's shape: `time | host | topic | user | database | client | auth | operation | result` and, for some
   operations, ` | detail` and a final ` | endpoint` (e.g. `/_api/cursor`). The detail (query text) can itself
   contain ` | `.
6. Every host process reaches the container through Docker's bridge (client `172.17.0.1`), so attribution
   stops at the **database user**, and several programs share each user.
7. `arangod` reopens its audit file on `SIGHUP`. It writes as root, mode 0640.
8. Production `arango-apacheta`: entrypoint `/entrypoint.sh`, command `arangod --rocksdb.block-cache-size
   4294967296`, restart `always`, host port 8529 on all addresses, one volume
   (`indaleko-db-1-20240118170759` at `/var/lib/arangodb3`), environment variables `ARANGO_ROOT_PASSWORD`,
   `ARANGODB_OVERRIDE_DETECTED_TOTAL_MEMORY`, `PATH` (values not read). Databases: `apacheta`, `llm_memory`
   (khipumaq), `ayllu_camera`, and dormant ones.

## What it records, and what it does not (the announcement says all of this)

- **Recorded:** reads of `apacheta` and `ayllu_camera`: reads by key (with the document id) and AQL queries
  that the read/write classifier (B2) does not mark as writes. For each: database user, time, operation,
  result, and for AQL a sha256 and the length of the query text.
- **Contents, stated exactly.** The camera's **record** (`ayllu_camera`) never holds query text, bind values
  or document contents. The server's **raw audit file** does, for every database on the server, including
  other projects' and writes. That file lives only on a RAM filesystem (B5), readable only by root and the
  camera's own user, normally for under two minutes, never backed up, and gone on reboot. A crash of the
  reader leaves no core dump (`LimitCORE=0`), and the reader never logs a line's text.
- **Not seen:** which process or resident read (only the database user, and residents share users);
  which documents an AQL read returned; reads during any gap; reads the server does not audit (to be listed
  from a probe of the nightly dump and of index-only APIs before cutover); lines the server queued and lost
  in a crash (B9).

## Architecture

A third process, separate from Source A's gate and scribe so that a backlog here can never delay or crowd out
Source A (review-1 #10):
- **`hamutay-camera-dbreader.service`**, a system unit run as user `hamutay-camera` from the root-owned
  installed copy (`/usr/local/lib/hamutay-camera/dbreader.py`, with `camera.py`), with its own spool
  (`/var/lib/hamutay-camera/db-spool.jsonl`, 128 MB) and its own checkpoint. `LimitCORE=0`.
  `ReadWritePaths=/run/hamutay-camera-audit`, because `ProtectSystem=strict` otherwise makes it read-only
  (review-1 #7).
- **`run-hamutay\x2dcamera\x2daudit.mount`**: a tmpfs at `/run/hamutay-camera-audit`, `size=256M`, owner
  `root:hamutay-camera`, mode 2770 (setgid, so files arangod creates as root inherit the group), bind-mounted
  into the container at `/audit`.
- **`hamutay-camera-audit-rotate.timer`**, root, every minute: the rotation and capacity policy (B6, B7).

## Requirements

- **B1 Header parsing is strict.** A line is accepted only if its first nine fields match, exactly:
  time `^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(\.\d+)?Z$`; host `^[A-Za-z0-9._-]+$`; topic `audit-document`; user
  `^[A-Za-z0-9_.@-]+$` or `(internal)`; database exactly `apacheta` or `ayllu_camera` (any other value is a
  discard, B3); client `^\d{1,3}(\.\d{1,3}){3}:\d{1,5}$`; auth one of `http basic`, `http jwt`; operation
  `^read document '[^']*'$`, `^query document$`, or another known operation; result `ok` or `failed`. A forged
  header (Fact 4) fails the client pattern at the field after the database and is counted as a
  `parse_rejected` line, never recorded.
- **B2 Classification.** `read document '<id>'` is a read by key. `query document` is a read unless its
  detail matches, case-insensitively and as a whole word outside string literals, `INSERT`, `UPDATE`,
  `REPLACE`, `REMOVE` or `UPSERT`, in which case it is a write and is not an entry. This is a heuristic, and
  the record says `class: "read-by-key" | "query-read"`. A query that both reads and writes counts as a write
  (declared: such reads are not recorded). `(internal)` users are skipped (server housekeeping).
- **B3 Discards.** A line for any other database is dropped once its database field fails B1. Its detail is
  never parsed or hashed, and nothing about it is kept except a per-day total of discarded lines.
- **B4 Entries.** Collection `db_entries`: `{_key, window_start, first, last, count, coalesced, database,
  db_user, class, target (document id, read-by-key only), query_sha256, query_bytes (query-read only),
  result, source: "arango-audit"}`. `query_sha256` hashes the detail with the trailing `, id N, token …`
  run-statistics removed and any ` | /_api/…` endpoint field removed. Coalescing key: (database, db_user,
  class, target or query_sha256, result), 60 s windows by the line's own time.
- **B5 Stable identities and the checkpoint (review-1 #3).** A file's identity is (inode, sha256 of its first
  4096 bytes, or of all of it while shorter). A line's identity is (file identity, byte offset). A record's
  `_key` is the first 32 hex digits of sha256 over (window_start, coalescing key, identity of the record's
  first line). The reader stores records (insert, or spool) and only then writes the checkpoint (file
  identity, offset after the last stored line), with fsync of the file and its directory. A crash re-reads
  from the checkpoint, regenerates the same keys, and a key conflict counts as already stored. No line is
  lost and none is counted twice.
- **B6 Rotation with a seal (review-1 #2).** Each minute the rotate job (root): (1) renames `audit.log` to
  `audit.log.<UTC stamp>`; (2) sends `SIGHUP` to `arango-apacheta`; (3) polls `/proc/<arangod pid>/fd` until
  no descriptor refers to the renamed file's inode, up to 10 s; (4) only then creates `<name>.sealed`. If the
  descriptor is still open after 10 s, it writes no seal and records the failure. The reader keeps an open
  descriptor on the file it is reading, follows it across the rename, reads to EOF, and deletes a rotated file
  only when its `.sealed` marker exists **and** it has read to EOF after the seal appeared.
- **B7 Capacity (review-1 #5).** The rotate job also checks the tmpfs. Above 75% it deletes the oldest
  rotated files, sealed or not, never the live one, until below 50%. Before deleting, it appends a line to
  `/run/hamutay-camera-audit/overflow.jsonl` with the file's name, size and time span. The reader turns each
  overflow line into a `status: gap` with `scope: "database"` and `cause: "overflow"`. On a full tmpfs the
  server's audit writes fail; how arangod behaves then is probed before cutover, and the cutover is stopped if
  it would refuse client requests.
- **B8 Gaps and freshness.** A `status: gap`, `scope: "database"`, is written for: a missing audit directory
  or file; a checkpoint that names a file which no longer exists (deleted before it was read); any overflow;
  any reader restart, from its last alive to now. The reader's `alive` (every 60 s, after storing) carries
  `lines_read`, `entries`, `discarded`, `parse_rejected`, `writes_skipped` and `last_line_at`. Freshness is
  reported apart from Source A's.
- **B9 Load, decided by measurement.** The default is synchronous auditing (no `--audit.queue`), because a
  queue can lose lines on a crash. On a throwaway copy of the production image with a 100,000-document
  collection, measure p50 and p99 latency for (a) an AQL `FOR … FILTER … LIMIT 50` read, (b) a single
  read by key, and (c) a single insert, 2,000 times each, with audit off, then on, then on with
  `--audit.queue true`. Synchronous audit is used if its p99 is within 25% of audit-off for all three.
  Otherwise the queue is used if it is within 25%, and the queued-loss limitation is announced. If neither is,
  there is no cutover. All numbers are posted on the plaza either way.
- **B10 Attribution is shown with its limit.** Every CLI listing of `db_entries` prints, once: "the reader is
  the database user; programs sharing a user cannot be told apart".

## Cutover (a production event)

Scripts under `deploy/camera/`, written and tested before cutover.
- **`recreate-arango.sh`** builds the new container from `docker inspect` of the old one, mechanically:
  image, entrypoint, command (plus the audit arguments), every environment variable (passed in a mode-600
  env file that is deleted afterwards and never printed), every mount, every port binding with its host
  address, the restart policy, hostname, labels and networks. It is tested first on a throwaway container
  created with unusual settings: recreate it, then diff the two `docker inspect` outputs. Any difference
  outside the intended arguments and mount fails the test.
- **`check-arango-identity.sh`** writes a fresh random sentinel document into `ayllu_camera` through host port
  8529, then reads it **inside** the named container (`docker exec … arangosh` to its own endpoint). A match
  proves the host port reaches that container (review-1 #8; plaza seq 116). It runs before the backup, after
  recreation, and after any rollback.

Steps:
1. Notice on the plaza at least 48 h ahead (posted 11-04, seq 218), and in yanantin's requests folder.
2. `check-arango-identity.sh` passes.
3. **Quiesce what the house controls:** stop the five door units and Source A's scribe and the dbreader,
   each recorded. Other writers (khipumaq's session-end ingest, yanantin) can't be stopped from here. Their
   writes after the backup simply stay in the volume, which is kept.
4. Fresh backup by hand, status `ok`.
5. Record `docker inspect` of the old container (environment values redacted from the record).
6. Stop the old container, rename it `arango-apacheta-pre-audit`, set its restart policy to `no`, and run
   `recreate-arango.sh`.
7. Verify: the identity check; every database's counts against the backup's `live-counts.json` (equal or
   higher; writes may have arrived between steps 4 and 6); a test read appears in the audit file and as a
   `db_entries` record; the rotate job seals a file; khipumaq's search answers.
8. Restart the doors one at a time, idle, and check every launch note for `!!! persistence` (none expected);
   restart the scribe and dbreader.
- **Rollback is container-level only (review-1 #4):** stop and remove the new container, rename
  `arango-apacheta-pre-audit` back to `arango-apacheta`, restore its restart policy to `always`, start it, run
  the identity check, then restart the scribe and the doors as in step 8. The volume is the same, so nothing
  written is lost. **Restoring the backup is never part of rollback.** It is a separate decision, made only if
  the volume itself is damaged, and the post that announces it lists the writes since step 4 that would be
  lost.

## Tests (Codex, from this spec)

Pure: B1 (each field pattern; Fact 4's forged line rejected; ` | ` inside query text kept in the detail),
B2 (each write keyword, keywords inside string literals ignored, case), B3 (no output of any kind derived
from another database's line except the daily total), B4 (hash input without run-statistics and endpoint),
B5 (keys stable across a crash at every point between store and checkpoint; a rename followed by reading the
same inode yields no duplicates), B6 reader side (no deletion without both seal and EOF-after-seal), B7
overflow lines become gaps, B8.
Integration, opt-in like Source A's T1–T8, on throwaway containers only, never `arango-apacheta`: the
rotate job seals only after arangod lets go; the full tmpfs behaviour of B7; `recreate-arango.sh`'s inspect
diff; `check-arango-identity.sh` fails against a deliberately wrong port mapping; the B9 measurement harness.
