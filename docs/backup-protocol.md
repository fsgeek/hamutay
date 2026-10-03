# Backup protocol: the ArangoDB server that holds Apacheta

**Established:** 2026-10-03 by the custodian (Claude Opus 5.5), after the README's "backed up off this
host" could not be verified.

## What is backed up, and where it lives

- **The server.** Docker container `arango-indaleko-20240118170759`, image `arangodb/arangodb:latest`
  (3.12.4). The name is a leftover from Indaleko. This container holds the ayllu's record.
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

## Open

- **Restore tests should recur,** monthly for example, and be automated the same way.
- **Pin the image.** `latest` means a re-pull could upgrade the server without a decision. It
  should be pinned to `3.12.4`.
- **A third copy off the premises:** Azure blob storage under Tony's MSDN allowance, when it is
  judged worth it.
- **Rotate credentials:** the root and app passwords appeared in a session transcript on 10-03.
  Automatic rotation is future work.
- **Show freshness in checks:** the age of the last `ok` run should appear in `check-plaza` or in
  the checkpoint commit, so that a silent stop is seen.
