# Plaza carrier independent validation plan

**Goal:** validate tests 1–7 of `docs/superpowers/specs/2026-10-09-plaza-carrier-field-design.md`
against its r5 Interface, including the caller-supplied `proc` and `boot_id` paths.
The implementation is absent here. Missing interfaces fail assertions or calls; no
skips, xfails, substitute implementations, production changes, or commits are used.

**Architecture:** reuse the existing plaza house fixtures, create literal message
fixtures, and inspect persisted bytes. Exercise the real session/executor, registered
FastMCP tools, CLI parser, projection, page JavaScript, repair pass, and checkpoint
script. Only model inference and host deployment infrastructure are stubbed.

**Tools:** pytest, Python, Node (the unchanged `tests/validation_viewer/render_page.js`
helper), bash, git, and standard Linux checkpoint utilities. No network/API calls.

## Review gate

- [x] Read the r4 review and r5 design plus its Interface amendment.
- [x] Boot collision is resolved by the current boot ID requirement (spec 78–90,
  regression tests 166–168).
- [x] Ordinary command-line/stat/census read failures must fail readiness (91–93,
  168–169), distinguishing confirmed exit from permission denial.
- [x] `accepts` must come from the validator actually loaded (80–83, 169–170).
- [x] No Blocking finding; proceed with independent tests.

**Should:** spec 91–93 should also say how to reject a census that succeeds but hides
processes (for example a restricted `/proc` view). Read-error handling resolves the
ordinary failure case from r4 but does not by itself establish complete visibility.
The suite covers denied enumeration; it does not invent a mount/namespace policy.

**Could:** specify the serialized types/whitespace of boot ID and start ticks
(78–80, 126–128). The choices below keep identity comparisons explicit without
depending on a private process-classification helper.

## Coverage map and execution

| Spec test | Spec items and lines | Validation files / checks |
|---|---|---|
| 1 | Design 1–2, 21–34; Interface 111–113; Tests 142–146 | `test_records.py`: old records; 1/120/121 limits; strings, Unicode, null/non-strings; stored whitespace vs writer strip; all seven forbidden characters in leading/middle/trailing positions; unrelated extras; delivery rejection; optional builder key. |
| 2 | Design 3 doors, 36–42, gate 51–53; Interface 118–119; Tests 147–152 | `test_doors.py`: scripted inference calls the real executor created by `OpenTasteSession`; real heartbeat parser and `build_session` for fresh/resumed/override cases; provider-prefixed and local IDs; spoofed input ignored; bad model fallback; gate absence; public executor keyword. |
| 3 | Design 3 guests, 43–50; Interface 120–121; Tests 153–154 | `test_writers.py`: registered post/send tools and impl keywords; optional descriptions/schema; fixed label; valid/absent/gate-off carriers; invalid first calls and retries with no artifact changes. Direct `send` spies fail if an invalid carrier reaches locking/reading. |
| 4 | Design 3 CLI, 46–53; Interface 122; Tests 155–156 | `test_writers.py`: real subprocess CLI parsing for posts and directed messages, gated/absent carrier, normalization; invalid input and existing-token retries; NUL supplied to the actual parser in process. |
| 5 | Design 4, 54–56; Tests 157–158 | `test_writers.py`: MCP and CLI retries, posts and directed messages; changed valid carrier returns original seq; plaza bytes and first persisted carrier remain unchanged. |
| 6 | Design 5, 57–63; Interface 123; Tests 159–161 | `test_readers.py`: literal stored XSS carrier -> gather -> actual JavaScript; HTML parse verifies literal text and no active elements/handlers, positioned between speaker and body; overview suffix; byte-identical wake note; unchanged directed wake event. |
| 7 | Rollout 71–99; Interface 124–130; Tests 162–173 | `test_mixed.py`: old/new/gated-less records validate/reduce, real CLI/MCP reads, real CLI repair pass, cursor coverage unchanged, delivery event has no carrier, checkpoint digest/size match bytes, removal stops subsequent emission and preserves history. `test_readiness.py`: actual reader identity, loaded old-validator probe, write failure, main ordering; fake proc matching/no evidence/PID reuse/other boot/old accepts/malformed records/wrong PID, multiple failures, dead PID and uv wrapper ignored, permissions and census failure, unreadable boot ID, confirmed exit. `test_rollout_script.py`: real shell readiness flag invokes public helper; ready passes, nonempty/crashed helper fails, dirty/non-descendant launches fail; gitignore behavior tested with git. |

- [x] Write all tests and utilities exclusively in this package.
- [x] Review syntax and boundary use before the one requested pytest run.
- [x] Run exactly once: `uv run pytest tests/validation_plaza_carrier -q`.
- [x] Report observed counts and the choices below; do not implement fixes.

Observed baseline: **222 failed, 27 passed (249 cases), 10.89 seconds, exit 1**.
Log: `/tmp/hamutay-carrier-validation.log`. `UV_CACHE_DIR` was redirected to
`/tmp/hamutay-carrier-uv-cache` because the default uv cache is read-only here.
There were no collection errors or skips. Most failures are absent carrier APIs,
missing persisted/projected fields, missing CLI flags, unchanged MCP behavior,
and absent readiness support. One failure was a fixture helper's `pid` argument
colliding with its intended JSON `pid` override; the helper argument was renamed
to `file_pid` after the run and its fixture output checked independently. Final
review also relaxed the legacy viewer fixture's absence check to allow an omitted
key or None, since Interface 123 only requires presence for records with carriers.
Pytest was not rerun; the reported counts describe the original run.

## Ambiguities resolved for this suite

1. **Start ticks / boot whitespace:** fake reader records use integer `proc_start`;
   a written record may use a decimal string or integer, compared to the actual
   field 22. Boot identity assertions compare stripped file contents (the kernel
   file has a final newline). The census receives integer-valued record fixtures.
2. **Optional None:** omitted/None writer arguments mean no field; a stored JSON
   null and `normalize_carrier(None)` are invalid. Guests/CLI invalid strings are
   tested with the gate both present and absent.
3. **Length after strip:** a raw value longer than 120 solely because of permitted
   surrounding Unicode spaces is valid when its normalized length is 120. Forbidden
   characters are checked before stripping, at every tested position.
4. **Failure lines:** assert number and meaningful guest/PID/start identity when
   available, without specifying prose. For command-line read errors, only the PID
   can reliably be named. Malformed evidence/wrong PID and unreadable boot ID are
   treated as unready. Empty census with only dead records is ready.
5. **Process model:** fake servers use Python `-m hamutay.plaza.mcp --guest LABEL`;
   the `uv run python -m ...` launcher is a separate process. Fake stat has spaces
   and closing parentheses in comm, while retaining Linux's field 22 position.
   No test calls private `_is_plaza_server`.
6. **CLI invocation:** module entry point runs the same real parser as the deploy
   shim without `uv` nested in each test. NUL cannot be passed through OS argv, so
   its one CLI case calls `cli.main([...])` directly.
7. **Rendering placement:** carrier must appear in the same post between its
   speaker and body; no CSS/class/element choice is prescribed. Legacy projection
   may omit the carrier key or represent absence as None; stored records may
   never carry a null carrier.
8. **Heartbeat resume:** the suite uses the real heartbeat parser and `build_session`
   on a prior state-bearing launch record, including the real substrate resolver
   and real session construction. Only external tokenizer probing and inference
   are replaced; no services or model providers are started.
9. **Deployment isolation:** copies the real check script into a fixture root;
   stubs systemd/journal/git ancestry and only the shell subprocess's public
   readiness function. The actual census is tested directly. Checkpoints run with
   `--no-commit` in a temporary empty git repo, with isolated GPU state.

The matrix is intended to catch dropped propagation, relaxed validation, validation
after duplicate lookup, stale boot/PID evidence, skipped permissions, hardcoded
capability declarations, lost cursor coverage, unescaped rendering, and incorrect
checkpoint bytes. Existing behavior controls may pass before implementation; feature
cases are expected to fail. No assertion is weakened to fit the current checkout.
