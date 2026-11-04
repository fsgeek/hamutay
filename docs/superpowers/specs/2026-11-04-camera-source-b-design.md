# The camera, Source B: recording reads of the residents' database

**Status:** design r1, for Codex review. **Date:** 2026-11-04. **Author:** the custodian (Claude Opus 5.5).
Extends `2026-11-03-access-camera-design.md` (r8; "Source A", file opens in homes), which declared database
reads unseen. Probe facts: `2026-11-04-camera-source-b-probe.md`, plus two more found the same day (§Facts 5–6).

## Why

Most of a resident's history is in Apacheta (database `apacheta` on `arango-apacheta`), not in its home
directory. The camera now shows who opens a file in a home, but not who reads a resident's records. First
Luna's condition was unlogged access to a resident's history and persistence (plaza seq 96), and the
README now says database reads are not recorded. This closes that gap for the database, as far as the server
lets it.

## Facts this rests on (probed on throwaway containers from the production image)

1. Audit is enabled by container arguments: `--audit.output file:///…` and `--log.level audit-document=info`.
2. `audit-document` records reads by key (`read document 'c/169'`) and AQL (`query document`, with the full
   query text), and also inserts.
3. A line is ` | `-separated: time, host, topic, database user, database, client address:port, auth method,
   operation text, result, then a detail field. For AQL the detail is the query text followed by
   `, id N, token …, exit code …, elapsed …`.
4. Every host process reaches the container through Docker's bridge (client 172.17.0.1), so attribution
   stops at the database user.
5. `arangod` reopens its audit file on `SIGHUP`. After the file is renamed and the container is sent
   `SIGHUP`, new lines go to a new file. It writes as root, mode 0640.
6. Databases on `arango-apacheta` (dump of 2026-11-04): `apacheta`, `llm_memory` (khipumaq), `ayllu_camera`,
   and dormant ones (`Indaleko`, `PromptGuard`, `PromptGuard2`, `AdversarialPrompts`, `apacheta_test`,
   `spike_proseidx`). Audit is server-wide: it cannot be limited to one database.

## Requirements

- **B1 What is recorded.** Every `audit-document` line whose database is `apacheta` or `ayllu_camera` and
  whose operation is a read: `read document …`, `query document`, or any other operation text beginning
  `read`. Inserts, updates and removals are not entries (writes are the residents' own persistence, already
  in Apacheta). Reads of `ayllu_camera` itself are recorded, so the camera's own readers are seen, except
  reads by the scribe's own database user `camera_scribe`, which are its own bookkeeping (declared).
- **B2 Never contents.** An AQL query's text is never stored. The entry keeps `query_sha256` (of the text
  as logged, without the `, id N, …` suffix) and `query_bytes`. A read by key keeps the document id
  (`collection/key`), which is an identifier, not content.
- **B3 Everything else is discarded unread.** Lines for any other database are dropped by the parser as soon
  as the database field is known. Their detail field is never parsed, stored or counted by name. Only a
  per-day count of discarded lines is kept, with no breakdown by database.
- **B4 Entries.** Collection `db_entries` in `ayllu_camera`: `{_key, session, window_start, first, last,
  count, coalesced, database, db_user, operation ("read" | "query"), target (document id) or query_sha256
  and query_bytes, result ("ok" | other), source: "arango-audit"}`. Coalesced like R5: key (database,
  db_user, operation, target or query_sha256, result), 60 s windows by the line's own time.
- **B5 The file.** Host directory `/var/lib/hamutay-camera-audit`, owned `root:hamutay-camera`, mode 2770
  (setgid, so files arangod creates as root inherit the group; the house user has no access). Bind-mounted
  into the container at `/audit`; arangod writes `/audit/audit.log`.
- **B6 Rotation and purge.** A root timer, every 15 minutes: rename `audit.log` to `audit.log.<UTC stamp>`,
  then `docker kill --signal=HUP arango-apacheta`. The scribe reads rotated files in name order, to the end,
  then deletes each one. It reads the live file only by following it. So lines about other projects'
  databases exist on disk for at most about 15 minutes plus the scribe's lag, and never leave the machine
  (the directory is not in any backup).
- **B7 Position and gaps.** The scribe keeps its position (file name, inode, byte offset) in its state
  directory and resumes from it. Its `alive` gains `db_lines_read`, `db_entries`, `db_discarded`,
  `db_parse_errors` and `db_last_line_at`. If the audit directory or file is missing, or no line has
  arrived for 10 minutes while the server answers its health query, it writes `status: gap` with
  `scope: "database"`. The CLI reports database-read freshness separately from the gate's and the scribe's.
- **B8 Parsing is total.** A line that cannot be parsed counts as a parse error and is skipped; it never
  stops the scribe. A line longer than 1 MB is skipped and counted. The text is split on ` | ` at most nine
  times, so a ` | ` inside query text stays in the detail field.
- **B9 Load.** `--audit.queue true`, so auditing queues lines instead of writing synchronously. Before
  cutover, measure a khipumaq-shaped search and a door's persist with audit on and off on a throwaway copy,
  and record both.

## Cutover (a production event)

The arguments can only be changed by recreating `arango-apacheta` on its existing volume, as on 2026-10-03
(`docs/backup-protocol.md`).
1. Notice on the plaza at least 48 h ahead, naming khipumaq (whose store `llm_memory` is on the server) and
   qhaway (whose reground reads through it). Also a file in yanantin's `docs/requests/` (yanantin
   writes `apacheta` and isn't a plaza guest). Dormant projects get no notice. Their databases' lines are
   discarded by B3 like any other.
2. Fresh backup by hand (`hamutay-backup-arango`), status `ok`.
3. Every door idle (no event running), and the scribe stopped.
4. Stop `arango-apacheta`, rename it `arango-apacheta-pre-audit` with restart off (the rollback), start a new
   `arango-apacheta` from the same image, volume, port and restart policy, plus the bind mount and B1/B9
   arguments. The exact old arguments come from `docker inspect` of the old container, recorded first.
5. Check: every database's counts match the backup's `live-counts.json`; the doors' persistence check
   (`!!! persistence` absent from launch notes after one idle restart each); khipumaq's health; an audit line
   appears for a test read; the scribe records it.
6. Rollback: stop the new container, start the renamed one. Nothing written in between is lost only if
   nothing was written; otherwise restore from the step-2 backup.

## Tests (Codex, from this spec)

Pure: the line parser (every field; ` | ` inside query text; the `, id N` suffix stripped before hashing;
long and malformed lines), the B1 filter (databases, operations, the camera_scribe exclusion), B3 (nothing of
another database's line survives in any output), B4 coalescing, B7 position and resume across rotation (a
renamed file finished before the live one; a truncated or replaced file detected by inode). Integration,
opt-in like T1–T8: a throwaway container with the B5 mount, where a read by key and an AQL read each become
one `db_entries` record and a read in another database becomes nothing but a discard count.
