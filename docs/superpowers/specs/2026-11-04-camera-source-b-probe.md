# Camera Source B (database reads): what the server can record, probed 2026-11-04

Probe by the custodian (Claude Opus 5.5) on a throwaway container from the production image
(`arangodb/enterprise:3.12.9.4`, port 8599, removed afterwards). Nothing on `arango-apacheta` was touched.

## Findings
1. **The option is not `--audit.topics`.** 3.12 rejects it ("unknown option"). Audit topics are log topics:
   `--audit.output file:///…` plus `--log.level audit-document=info` (and `audit-collection`,
   `audit-database`, `audit-authentication`).
2. **Reads are recorded.** A read by key: `audit-document | root | probe | 172.17.0.1:58022 | http basic |
   read document 'c/169' | ok | /_api/document/c/169`. An AQL read: `audit-document | … | query document |
   ok | FOR x IN c RETURN x, id 172, …`. Inserts are recorded too (`insert document in 'c'`).
3. **What a line names:** time, database user, database, client address and port, auth method, operation,
   result, and for AQL the **full query text**. For AQL it does not say which documents came back.
4. **Who, only partly.** Every host process reaches the container through Docker's bridge, so the client
   address is 172.17.0.1 for all of them. The database user (apacheta_app, root, yanantin_reader, …) is
   the best attribution available, and several programs share each user.

## What this means for the design (not yet a spec)
- **Contents.** AQL text can carry data (an insert's values, a search string). The camera's promise is
  "never contents", so Source B must store a sha256 and the length of the query text, the database, the
  user and the operation, never the text itself.
- **Scope.** Audit topics are global to the server. `arango-apacheta` also holds `llm_memory` (khipumaq),
  Indaleko, PromptGuard and others. Their reads would be written to the server's audit file too. Source B
  must keep only `apacheta` and `ayllu_camera` lines and discard the rest at once. Their owners must be
  told before it starts, since a server-wide log of their reads would exist briefly even so.
- **Cutover.** The options are container arguments, so turning them on means recreating `arango-apacheta`
  on its existing volume, the same shape as the 2026-10-03 swap (`docs/backup-protocol.md`): fresh backup
  first, every door idle, the old container kept for rollback, guests told in advance. Everyone who uses
  this server loses it for about a minute.

## Second probe (2026-11-04, after Codex's review)
- With `--database.extended-names true`, a database named `apacheta | local | x` produced
  `root | apacheta | local | x | 172.17.0.1:37984 | http basic | query document | …`: pipes are not escaped,
  so a naive split mis-reads the database (Codex's finding #6, confirmed).
- `INSERT {secret: 'S3CR3T'} INTO w` through AQL produced both `insert document in 'w'` and a `query document`
  line containing `S3CR3T` (finding #11's hypothesis, confirmed: `query document` is not a read).
- Some AQL lines carry `with bindVars {…}` in the detail, and lines can end with ` | /_api/cursor`.
- Production `arango-apacheta` arguments (no environment values read): see the design's Fact 8.
