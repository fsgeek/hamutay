# Camera Source B: a first bound on volume, for r5 (2026-11-05)

The review-4 note asks r5 to drop coalescing, "precondition: measure the read
volume on `apacheta` first." This is the cheapest first measurement: the
server's own aggregate HTTP counters, read once.

## What was read

One `GET /_admin/statistics` on the production server (host 127.0.0.1:8529),
2026-11-05 ~19:10Z, with the admin credentials from the yanantin config, read
the way `deploy/backup-arango.sh` reads them (never printed). The response holds
counts since server start: no query text, no collection or database names, no
documents. Nothing else was requested.

## Result

Uptime 192.6 h (about 8 days).

| method | total | per day |
|---|---:|---:|
| POST | 148,562 | 18,516 |
| GET | 11,020 | 1,373 |
| DELETE | 1,161 | 145 |
| HEAD | 604 | 75 |
| PATCH | 310 | 39 |
| PUT | 289 | 36 |
| **all** | **161,946** | **20,184** |

All requests are user requests (none superuser, none async).

## What it does and does not show

- **Upper bound, per request:** about 20k requests/day on the whole server, every
  database included. This includes writes (the doors' cycle persistence posts
  documents), the nightly `arangodump`, and guests' queries. Reads are a subset.
- **One record per audit line** at this rate would be roughly 20k records/day,
  about 7M/year. That is ordinary for ArangoDB. On this evidence, volume does
  not force coalescing back in.
- **Not measured: lines per request.** The audit log's topics can write more
  than one line per request (for example, a document topic on a batch
  operation). The ratio of audit lines to requests has to be measured on a
  throwaway container with a door-shaped workload before r5 relies on the
  bound. Until then this is a bound on requests, not on records.
- **Not measured: the split between reads and writes** inside the POSTs (AQL
  cursors versus document inserts). Not needed for the volume decision, since
  the bound covers both.
