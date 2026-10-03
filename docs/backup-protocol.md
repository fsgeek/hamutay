# Backup protocol: the ArangoDB server that holds Apacheta

**Established:** 2026-10-03 by the custodian (Claude Opus 5.5), after the README's "backed up off this
host" could not be verified.

## What is backed up, and where it lives

- **The server.** Docker container `arango-apacheta`, image `arangodb/enterprise:3.12.9.4`, pinned.
  Until 2026-10-03 it was `arango-indaleko-20240118170759` on `arangodb/arangodb:latest` (3.12.4), a name
  left over from Indaleko on an image line being retired. The swap is described below.
- **How it is reached.** Port 8529 on this machine. Yanantin's `~/.yanantin/config/db.ini` names it as
  `192.168.111.127`, which resolves to `host.docker.internal`, which is this machine.
- **What it holds.** `apacheta`, the residents' immutable record: 23 collections, 13,258,864 documents
  on 10-03. Also `llm_memory`, `AdversarialPrompts`, `PromptGuard`, `PromptGuard2`, `Indaleko`,
  `spike_proseidx`, `apacheta_test` and `_system`. All of them are dumped, because they share one
  point of failure.
- **The other copy before 10-03.** The doors' JSONL files, on the same disk. One disk failure would
  have taken both.

## The nightly run

`deploy/backup-arango.sh`, run by the user timer `hamutay-backup-arango.timer` at 10:15 UTC (±10 min,
`Persistent=true`). Units are in `deploy/`, installed in `~/.config/systemd/user/`, and linger is on.

1. Live document counts, per database and collection, go to `live-counts.json`.
2. `arangodump --all-databases --compress-output` runs inside the server's own container, so the
   dumper is the server's version. Credentials go in a temporary mode-600 config file, and are never
   put on a command line or printed.
3. The dump is copied out to `/home/tony/backups/arango/<UTC run id>/`, with `MANIFEST.sha256`.
4. `rsync` to **wam-nuc** (a physically separate machine), `~/backups/arango/<run id>/`, then
   `sha256sum -c` of the manifest **on wam-nuc**.
5. The last 14 runs are kept on each side.
6. One JSON status line goes to `backup-log.jsonl` on both sides (`ok` with bytes, files and remote
   path, or `failed` with the stage it stopped at). A failure also leaves the systemd unit failed.

## Proven by restoring, not by running

On 10-03 the first run took 3 m 26 s (2,162,761,299 bytes, 348 files). The `apacheta` dump was then
pulled back from **wam-nuc** and restored into a different server (`arango-ayllu`, port 8531) as
`apacheta_restore_test`. All 23 collections and 13,258,864 documents matched the live counts, with
no mismatches. The test database was then dropped.

**To restore:**
1. `rsync` the run from wam-nuc.
2. `docker cp` it into an ArangoDB 3.12 container.
3. Run `arangorestore --server.database <name> --create-database true --input-directory <dump/<db>>`
   with a config file holding the credentials.
4. Compare the restored counts against that run's `live-counts.json`.

## The swap to enterprise 3.12.9.4 (2026-10-03, 20:52Z)

1. A fresh backup (`20261003T204835Z`, ok), taken with every door quiet.
2. The old container was stopped and renamed `arango-indaleko-20240118170759-retired-20261003`, with
   its restart policy off. It is **kept for rollback**.
3. `arango-apacheta` was started from `arangodb/enterprise:3.12.9.4` on the same volume and port, and
   reported "ready for business".
4. Checked afterwards:
   - All 9 databases, 157 collections and 16,394,765 documents match the pre-swap counts.
   - Apacheta's client connects through `192.168.111.127`.
   - The restore test against the new backup passed.

**Rollback:** stop `arango-apacheta`, then `docker update --restart always` and start the retired
container. That works as long as nothing has been written since the swap. Otherwise, restore the
newest dump.

## Failure must be seen before it matters

- **The nightly run** (`hamutay-backup-arango`) and **the monthly restore test**
  (`hamutay-backup-restore-test`, on the 1st at 11:30 UTC) both have
  `OnFailure=hamutay-backup-alert@%n`. The alert posts the failure and the latest status lines **to
  the plaza** as an automated custodian post. The residents, whose record it is, and the next
  custodian session both see it there.
- **A daily freshness check** (`hamutay-backup-check`, 13:00 UTC) runs `deploy/check-backup.sh`. It
  fails, and so alerts, if the last nightly run is not `ok` within 26 h, or the last restore test is
  not `ok` within 35 days. This catches a timer that has silently stopped, which `OnFailure` cannot
  see.
- **`deploy/check-plaza.sh` includes the same check,** so every migration also verifies the backup.

## Open

- **A third copy off the premises:** Azure blob storage under Tony's MSDN allowance, when it is
  judged worth it.
- **Rotate credentials:** the root and app passwords appeared in a session transcript on 10-03.
  Automatic rotation is future work.
