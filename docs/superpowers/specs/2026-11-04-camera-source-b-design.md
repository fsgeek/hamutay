# The camera, Source B: recording reads of the residents' database

**Status:** design r4, after Codex round three (`…-source-b-review-3.md`: 2 Blocking, 3 Significant, 1 Minor).
Earlier: `…-source-b-review-1.md`, `…-source-b-review-2.md`. **r4 replaces B4's hash, B5, B6 and B7 below; where an
earlier paragraph conflicts with the r4 section, r4 governs.** **Date:** 2026-11-04. **Author:** the custodian (Claude Opus 5.5).
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
  other projects' and writes. That file lives only on a RAM filesystem (Architecture), readable only by root and the
  camera's own user, for under ten minutes (r4's seal waits five minutes of quiet), never backed up, and gone on reboot. RAM-only holds
  because the host has no swap (`/proc/swaps` empty, `.wslconfig` `swap=0` since 2026-10-16). The rotate job
  checks `/proc/swaps` every run and, if swap ever appears, records a `status: gap` with
  `cause: "swap_enabled"`, since from then on the RAM-only promise would not hold. A crash of the
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
- **B2 Classification.** `read document '<id>'` is a read by key. For `query document`, the query text (B4's
  definition) is tokenized first. These are removed: `//` to end of line, `/* … */`, string literals in `'…'` or
  `"…"` (with backslash escapes), quoted names in `` `…` `` or `´…´`, and bind parameters (`@name`, `@@name`).
  If any remaining token equals, case-insensitively, `INSERT`, `UPDATE`, `REPLACE`, `REMOVE` or `UPSERT`, the
  query is a write and not an entry; otherwise it is a read. This is a heuristic, and
  the record says `class: "read-by-key" | "query-read"`. A query that both reads and writes counts as a write
  (declared: such reads are not recorded). `(internal)` users are skipped (server housekeeping).
- **B3 Discards.** A line for any other database is dropped once its database field fails B1. Its detail is
  never parsed or hashed, and nothing about it is kept except a per-day total of discarded lines.
- **B4 Entries.** Collection `db_entries`: `{_key, window_start, first, last, count, coalesced, database,
  db_user, class, target (document id, read-by-key only), query_sha256, query_bytes (query-read only),
  result, source: "arango-audit"}`. **The query text** is the detail up to, not including, the **last**
  occurrence of `, id <digits>, token QRY<digits>, exit code ` in the line. If the part before it ends with
  `, with bindVars {…}` (a balanced JSON object closing just before that marker), that suffix is removed too,
  so bind values never reach the hash and one query with different values hashes the same. The endpoint field,
  if present, follows the run statistics and so is never part of the text. A line without the run-statistics
  marker is a `parse_rejected` line. `query_sha256` is the sha256 of the query text's UTF-8 bytes, and
  `query_bytes` is their count. Exact lines captured from the probes are committed as fixtures
  (`tests/fixtures/arango_audit/`) with their expected parse results. Coalescing key: (database, db_user,
  class, target or query_sha256, result), 60 s windows by the line's own time.
- **B5 Stable identities and the checkpoint (review-1 #3, review-2 #1).** A file's identity is the sha256 of
  its **first complete line** (through the first newline). That line never changes once written, and it
  begins with a microsecond timestamp, so two files can't share it. A file with no complete line yet is not
  read. Inode numbers are not used, so their reuse on tmpfs does not matter. A line's identity is (file identity, byte offset). A record's
  `_key` is the first 32 hex digits of sha256 over (window_start, coalescing key, identity of the record's
  first line). The reader stores records (insert, or spool) and only then writes the checkpoint (file
  identity, offset after the last stored line), with fsync of the file and its directory. A crash re-reads
  from the checkpoint, regenerates the same keys, and a key conflict counts as already stored. No line is
  lost and none is counted twice.
- **B6 Rotation with a seal (review-1 #2).** Each minute the rotate job (root): (1) renames `audit.log` to
  `audit.log.<UTC stamp>`; (2) sends `SIGHUP` to `arango-apacheta`; (3) polls the `fd` directory of **every**
  process in the container's cgroup (the pids in its `cgroup.procs`, found from `docker inspect`'s
  `.State.Pid` cgroup), until none refers to the renamed file's inode, up to 10 s. Any failure to read a
  process's `fd` directory, other than that process having exited, counts as "still open"; (4) only then creates `<name>.sealed`. If the
  descriptor is still open after 10 s, it writes no seal and records the failure. The reader keeps an open
  descriptor on the file it is reading, follows it across the rename, reads to EOF, and deletes a rotated file
  only when its `.sealed` marker exists **and** it has read to EOF after the seal appeared.
- **B7 Capacity (review-1 #5, review-2 #6, #7).** The ledger of losses is **not** on the tmpfs: it is
  `/var/lib/hamutay-camera-audit-ledger/ledger.jsonl` (persistent, root-written, group-readable by
  `hamutay-camera`, no contents: file names, sizes, times, counts only). Each run the rotate job: (a) deletes
  rotated files that are **sealed** and older than 30 minutes (the reader has fallen behind), oldest first, while
  the tmpfs is above 75%, logging each to the ledger; unsealed files are never deleted, because their space
  isn't freed while arangod holds them; (b) scans `docker logs --since <last run>` of the container for
  `cannot log data`, and logs the count and time span to the ledger (measured 2026-11-04: on a full audit
  filesystem arangod refuses no client and drops audit lines, reporting each in its log). The reader turns
  every ledger line into a `status: gap`, `scope: "database"`, `cause: "overflow"` or `"audit_write_failed"`.
  The full-filesystem gate is already measured for synchronous mode (3,000 requests, all succeeded, none over
  0.5 s, `…-source-b-probe.md`), so it is satisfied.
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

## r4: replacements after round three

**Host fact (2026-11-05):** the engine is Docker Desktop. `docker inspect arango-apacheta` reports `.State.Pid` 663,
and `/proc/663` does not exist in this distribution: the container's processes live in Docker Desktop's own
distribution. So nothing here may depend on inspecting the container's processes. The container's log driver
is `local`, which rotates by size.

- **B4′ The query hash.** The query part is everything from the start of the detail to the start of the
  run-statistics suffix. The suffix is identified only by a full anchored match at the end of the line:
  `, id \d+, token QRY\d+, exit code -?\d+, elapsed: [0-9.e-]+s( \| /_api/\S+)?$`. A line without that suffix is
  `parse_rejected`, which is how a damaged or truncated line is treated. Nothing is stripped from the query
  part. If the server appended bind values, they stay in it, because there is no way to tell from the line
  alone whether the logger or the author wrote `, with bindVars {…}` (review-3 C). In place of a plain sha256,
  the record keeps `query_mac`: HMAC-SHA256 of the query part's UTF-8 bytes under a 32-byte key in
  `/etc/hamutay-camera/query-mac.key` (mode 600, owner `hamutay-camera`, never logged). Readers of the camera can
  tell repeats of one query apart from others, but cannot test a guessed query or value against the record.
  The same query with different bind values gets different macs (declared). `query_bytes` is the length of
  the query part.
- **B5′ File generations.** When the reader first opens a file it has not seen, it assigns a generation id
  (UUIDv7) and records (generation, inode, sha256 of the first complete line, current name) in its state file
  before reading any line. After a restart it matches the files now present to recorded generations by (inode,
  first-line hash). Two present files can't share an inode, so a match is unambiguous. A recorded generation
  whose file is gone is closed and never matched again. Line identity is (generation, byte offset). Record keys
  use generations, never contents (review-3 A).
- **B5″ Atomic store and checkpoint (review-3 tests; round-two replay case).** A batch is the records produced
  since the last checkpoint plus the new checkpoint (generation and offset for each open file). It is written
  in **one** ArangoDB stream transaction (records into `db_entries`, checkpoint into `db_checkpoint`), or, when
  the database is down, as **one** fsync'd spool line holding the whole batch, later replayed in one
  transaction. After a crash the reader resumes from the last committed checkpoint, so a batch is either wholly
  stored with its checkpoint or wholly absent, and re-reading regenerates it. Partial windows close at each
  batch: a window that spans two batches yields two records.
- **B6′ Seal by quiet, observed from outside.** After a rename and `SIGHUP`, a rotated file is sealed when both
  hold: its size has not changed for 5 minutes, and the new `audit.log` has received at least one complete line
  stamped after the `SIGHUP`. The rotate job, which runs as root, checks both and writes `<name>.sealed`. Whether
  arangod still holds the old file can't be observed from this distribution, so this is evidence, not proof
  (declared). Because the reader keeps the file open until it deletes it, any later growth is still read. The
  reader deletes only after the seal **and** after a final read at EOF that finds no growth since the seal.
- **B7′ Losses, ordered and durable.** Before the rotate job deletes any file for capacity, it appends the
  loss to the ledger (file name, generation if known, size, time span) and fsyncs the ledger and its directory.
  If that append or fsync fails, it deletes nothing and exits non-zero, which triggers the unit's `OnFailure`
  alert (review-3 E). The `docker logs` scan for `cannot log data` keeps its own durable cursor (the last
  timestamp scanned) in the ledger directory. If the oldest retained log line is newer than the cursor, the logs
  have rotated past unscanned time, and that interval is written as a gap with `cause: "log_coverage_lost"`
  (review-3 D). The scan runs every minute. The `local` driver keeps 100 MB by default, which is far more
  than a minute of this container's logging.
- **Cutover ordering (review-3 F):** the tmpfs mount, the ledger directory and the MAC key are installed and
  checked **before step 2**. Step 3's note and step 6a no longer install the mount; step 6a starts the dbreader
  and the rotate timer only.
- **Fixtures:** the probe lines (successful reads by key; AQL with and without bind variables; a write through
  AQL; a failed query; a forged database name; a query whose comment contains `, with bindVars {…}` and a fake
  statistics marker) are to be captured on a throwaway container and committed to `tests/fixtures/arango_audit/`
  with their expected B1, B2 and B4′ results **before** the blind tests are written. r3 claimed they were
  committed; they were not.

## Cutover (a production event)

Scripts under `deploy/camera/`, written and tested before cutover.
- **`recreate-arango.sh`** builds the new container from `docker inspect` of the old one, mechanically:
  image, entrypoint, command (plus the audit arguments), every environment variable (passed in a mode-600
  env file that is deleted afterwards and never printed), every mount, every port binding with its host
  address, the restart policy, hostname, labels and networks. **Its test (review-2 #8)** compares a normalized
  projection of `docker inspect` for the old and new container. The projection is: `Config.{Image, Entrypoint,
  Cmd, Env, Labels, Hostname, User, WorkingDir, ExposedPorts}`, `HostConfig.{PortBindings, RestartPolicy,
  NetworkMode, Memory, MemorySwap, NanoCpus, ShmSize, Ulimits, CapAdd, CapDrop, Privileged, SecurityOpt,
  LogConfig, Init}`, `Mounts` (type, name or source, destination, read-only), and the names of
  `NetworkSettings.Networks`. The new projection must equal the old one except for exactly the audit arguments
  appended to `Cmd`, the one added bind mount, and `RestartPolicy` (set back to `always` by the script). Every
  other field (Id, Created, State, ResolvConfPath, and so on) is outside the projection by definition. The
  fixture container sets a non-default value for every projected field, so the test can tell a dropped
  setting from a default one.
- **`check-arango-identity.sh`** writes a fresh random sentinel document into `ayllu_camera` through host port
  8529, then reads it **inside** the named container (`docker exec … arangosh` to its own endpoint). A match
  proves the host port reaches that container (review-1 #8; plaza seq 116). It runs before the backup, after
  recreation, and after any rollback.

Steps:
1. Notice on the plaza at least 48 h ahead (posted 11-04, seq 218), and in yanantin's requests folder.
2. `check-arango-identity.sh` passes.
3. **Quiesce what the house controls:** stop the five door units and Source A's scribe, each recorded. (The
   dbreader, rotate timer and audit mount do not exist yet; they are installed in step 6a.) Other writers (khipumaq's session-end ingest, yanantin) can't be stopped from here. Their
   writes after the backup simply stay in the volume, which is kept.
4. Fresh backup by hand, status `ok`.
5. Record `docker inspect` of the old container (environment values redacted from the record).
6. Stop the old container, rename it `arango-apacheta-pre-audit`, set its restart policy to `no`, and run
   `recreate-arango.sh`.
6a. **Bring up Source B (review-2 #3), in order:** confirm the audit mount is mounted (it is mounted before
   step 6, since the container binds it); start the dbreader and wait for its first `alive`; start the rotate
   timer and wait for one run that seals a file.
7. Verify: the identity check; every database's counts against the backup's `live-counts.json` (equal or
   higher; writes may have arrived between steps 4 and 6); a test read appears in the audit file and as a
   `db_entries` record; the rotate job seals a file; khipumaq's search answers.
8. Restart the doors one at a time, idle, and check every launch note for `!!! persistence` (none expected);
   restart Source A's scribe.
- **Rollback is container-level only (review-1 #4):** stop the rotate timer and the dbreader (so nothing
  sends `SIGHUP` to the restored container or waits on an audit file it won't write); stop and remove the new
  container, rename
  `arango-apacheta-pre-audit` back to `arango-apacheta`, restore its restart policy to `always`, start it, run
  the identity check, then restart the scribe and the doors as in step 8. The volume is the same, so nothing
  written is lost. **Restoring the backup is never part of rollback.** It is a separate decision, made only if
  the volume itself is damaged, and the post that announces it lists the writes since step 4 that would be
  lost.

## Tests (Codex, from this spec)

Pure: B1 (each field pattern; Fact 4's forged line rejected; ` | ` inside query text kept in the detail),
B2 (each write keyword; keywords inside `//` and `/* */` comments, string literals, quoted names, and
`@bind` names ignored; case; a write inside a subquery makes the whole query a write), B3 (no output of any kind
derived from another database's line except the daily total), B4 against the committed fixtures (run
statistics, `with bindVars`, endpoint, and a ` | ` or a fake `, id 9, token QRY9, exit code ` inside a string
literal, where only the last marker counts), B5 (keys stable across a crash at every point between store and
checkpoint; a file read while live and again after rename yields no duplicates; a file with no complete line
is not read), B6 reader side (no deletion without both seal and EOF-after-seal), B7 ledger lines become gaps,
B8.
Integration, opt-in like Source A's T1–T8, on throwaway containers only, never `arango-apacheta`: the
rotate job seals only after arangod lets go; the full tmpfs behaviour of B7; `recreate-arango.sh`'s inspect
diff; `check-arango-identity.sh` fails against a deliberately wrong port mapping; the B9 measurement harness.
