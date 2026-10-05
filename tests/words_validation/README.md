# Independent words validation

The sole behavioral specification is
`docs/superpowers/plans/2026-10-05-recall-words.md`. Neither the words
implementation nor its existing unit/wiring tests were read. Only public
signatures and their interface documentation were extracted from the executor,
taste_open, and heartbeat modules. No community logs are used.

Work plan: create synthetic byte-preserving JSONL fixtures; validate addressed
reads and search populations; validate offering, guidance, record flags, schemas,
CLI, and heartbeat through their calling interfaces; inspect the new files
without importing or executing them. The custodian commits before the first run.

After freezing, run with:

```sh
env -u VIRTUAL_ENV uv run pytest tests/words_validation/
```

Interpretations of underspecified details:

* Raw-line hashes include the stored line terminator. Unicode, CRLF, trailing
  whitespace, and a final line without a terminator distinguish this from hashing
  parsed or normalized JSON. Any declared hash convention must agree with the
  bytes actually hashed.
* The plan does not name the skipped-line counter or reply-source metadata key.
  Tests accept clearly labeled keys for these facts, without accepting their
  absence. Likewise an omitted-character count can be an integer or a labeled
  object. Invalid addresses can be refused with an error dictionary or an
  explicit refusal status with a reason (including `unreachable`).
* Interim fragments must all survive in order, whether returned as a list or
  joined text; the joining separator is not specified.
* `matches_total` counts substring occurrences, while `records_matched` counts
  distinct records. Occurrences in fixtures do not overlap. Bounds are inclusive;
  bounded searches do not assert whether `records_scanned` includes excluded
  cycles. Unbounded scans count parseable record objects, excluding blank and
  malformed lines.
* Spread sampling must reach the first and last quarters of a sufficiently large
  matched population. No exact interpolation algorithm is required. With one
  match, the default sample limit, or a requested limit exceeding the population,
  all available matches must be reported.
* Near misses are tested with both words in the same selected field, avoiding
  the unspecified question of combining words across fields.
* A textual field's retained original prefix plus its omitted count must account
  for every original character. A visible truncation marker is allowed. The
  allocation of the total `max_chars` budget between fields is not prescribed.
* Search snippets are bounded around the hit by 150 characters on either side;
  a small allowance permits visible ellipsis markers at the cut edges.
* The backend's synthetic structured reply uses `STATE` (named by the plan) and
  `response_text`; these integration tests assert offering and the record flag,
  not the unrelated response-envelope protocol.
* Heartbeat is exercised with its public parser/session builder and a stopped
  loop, synthetic paths, no persistence, and no network. The launch-note wording
  must appear exactly, and the constructor must receive `words_recall=True`.

No suite run, collection, application import, or feature execution was performed
while writing this suite.
