# Guests independent validation plan

Authority: plaza design revision 7 (537ba73), invariants 3/8 and sections 2/11,
including round-five acceptance conditions. Implementation plan is interface
context, not the test oracle. No restricted implementation bodies inspected.

1. Pin the record matrix and label grammar with independently constructed rows.
2. Exercise durable admission, tokens, cap, UTC dates, and read truth through
   public APIs and CLI subprocesses, including a new process retry.
3. Pin configuration provenance and prompt wording, flags, and stripping.
4. Exercise MCP identity/schema and per-call admission/error contracts.
5. Copy deploy scripts without inspecting their bodies into temporary git
   houses, intercept host services on PATH, test readiness, activation, dry run,
   and configuration-only rollback with a real guest append in the window.

Write only here. Do not run pytest (including collection). Syntax may be checked
with ast.parse without importing tests. Commit each completed test group with
the requested frozen-validation message. Execution and defect triage belong to
the subsequent validation phase.

## Frozen coverage map

| Acceptance condition | Test module |
| --- | --- |
| All actor/transport/wake combinations; exact label grammar | test_records.py |
| Removed-label historical validity and refused writes/retries | test_writes.py, test_mcp.py |
| Mixed transports, concurrent final slot, 48th retry, posts, humans, separate labels, UTC | test_writes.py, test_records.py |
| Token content conflicts, canonical recipient, namespaces, no-token repetition | test_writes.py, test_records.py |
| New process CLI retry and new MCP server retry | test_writes.py, test_mcp.py |
| Digest coherence during atomic replacement; directed provenance | test_configuration.py, test_writes.py |
| Absent/empty lists, malformed lists, snapshot freeze, binding flag | test_configuration.py |
| Constitution truth table, historical plaza bytes, stripping | test_presentation.py |
| Guest/door/human header and envelope sentences; note wording | test_presentation.py |
| Shared inclusive reads, empty intervals, truth | test_writes.py, test_mcp.py |
| MCP schemas, reload, write refusals as data/read exceptions | test_mcp.py |
| Both scripts reject unknown flags; readiness retains plaza checks | test_deploy.py |
| Installed count verified on each door, dry run leaves house untouched | test_deploy.py |
| Failed activation preserves guest effects; pending delivery repaired; retry refused | test_deploy.py |

Validation performed before handoff: AST syntax parsing only, no pytest invocation
or collection and no test execution. The old plaza clause was cross-checked against
its constant at spec commit 537ba73 (schemas.py is outside the restricted bodies).

Commit attempt: the requested git add/commit could not create
/home/tony/projects/hamutay/.git/worktrees/guests/index.lock (read-only filesystem).
Git metadata is outside the permitted writable roots; no bypass was attempted.
