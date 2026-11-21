# Camera Source B r3: Codex review, round three (2026-11-04/05)

Read-only review of r3 (302612d), copied from its report. r4 answers it.

Confirmed by the custodian afterwards: the engine is Docker Desktop (`docker info`), `.State.Pid` of
arango-apacheta is 663, and `/proc/663` does not exist in this distribution, so finding B holds outright:
B6 cannot be implemented from here. The container log driver is `local` (size-rotated).

**Blocking findings remain in r3.** The reviewed spec matches `302612d`. All failure scenarios below are **hypotheses**, not observed production incidents.

Round-two dispositions, using its numbered findings:

1. **Partly** — hashing the first complete line fixes identity changes during append, but does not establish uniqueness between file generations. [B5](/home/tony/projects/hamutay/docs/superpowers/specs/2026-11-04-camera-source-b-design.md:98)
2. **Partly** — cgroup enumeration improves wrapper/child coverage and descriptor errors fail closed; hierarchy coverage, namespace resolution, and process-replacement races remain unspecified. [B6](/home/tony/projects/hamutay/docs/superpowers/specs/2026-11-04-camera-source-b-design.md:107)
3. **Resolved** — the reader starts before ingestion verification; rollback stops the reader and rotation first. A mount-installation wording conflict remains below. [Cutover](/home/tony/projects/hamutay/docs/superpowers/specs/2026-11-04-camera-source-b-design.md:165)
4. **Resolved** — B2 explicitly excludes comments, quoted names, and bind parameters before matching write tokens. [B2](/home/tony/projects/hamutay/docs/superpowers/specs/2026-11-04-camera-source-b-design.md:78)
5. **Partly** — bindVars removal and exact hash bytes are now specified, but the suffix rule can remove query text, and the promised fixtures are absent. [B4](/home/tony/projects/hamutay/docs/superpowers/specs/2026-11-04-camera-source-b-design.md:87)
6. **Partly** — unsealed files are protected and the ledger is outside tmpfs; durable accounting before deletion and ledger-failure behavior remain unspecified. [B7](/home/tony/projects/hamutay/docs/superpowers/specs/2026-11-04-camera-source-b-design.md:115)
7. **Partly** — the probe establishes 3,000 successful, bounded AQL requests under full-filesystem conditions in synchronous mode; it does not identify separate read/write coverage or define a future timeout/inconclusive-result rejection rule. [B7 probe](/home/tony/projects/hamutay/docs/superpowers/specs/2026-11-04-camera-source-b-probe.md:50)
8. **Resolved** — the comparison now has an explicit configuration projection, exclusions, allowed differences, and non-default fixture requirements. [Recreation contract](/home/tony/projects/hamutay/docs/superpowers/specs/2026-11-04-camera-source-b-design.md:144)
9. **Resolved** — the spec states the no-swap condition and defines monitoring and disclosure if it changes. [Contents promise](/home/tony/projects/hamutay/docs/superpowers/specs/2026-11-04-camera-source-b-design.md:42)
   
**Tests paragraph: Not resolved** — coverage categories improved, but a complete blind acceptance suite still requires invented expectations for parsing, generation identity, replay/coalescing, spool failures, and seal discovery. [Round-two tests assessment](/home/tony/projects/hamutay/docs/superpowers/specs/2026-11-04-camera-source-b-review-2.md:71)

The following problems concern r3’s replacement mechanisms.

**A. Blocking — immutable content is not a unique file-generation identity.**

B5 says the first line “begins with a microsecond timestamp, so two files can't share it.” Timestamp resolution does not establish uniqueness. Equal timestamps alone also do **not** establish a collision: the entire first line must match.

**Failure scenario—hypothesis:** the clock steps backward, and the same persistent client connection repeats the same read-by-key at the earlier timestamp. Both files’ first lines can then match completely. Their file identities and offset-zero line identities alias; matching record keys are treated as already stored, losing the second event. This requires equal input, not a cryptographic hash collision. [B5](/home/tony/projects/hamutay/docs/superpowers/specs/2026-11-04-camera-source-b-design.md:98)

Two rotations within one microsecond are **not an ordinary execution of the specified every-minute timer**. Nor does an empty file automatically collide: B5 correctly waits for a complete line. But if its eventual first complete line is byte-identical to an old file’s, it aliases that file by construction. Neither case establishes that this occurred in the probes.

Specify a persisted generation identity independent of audit contents, including its assignment, rename, recovery, and reboot behavior.

**B. Blocking — `cgroup.procs` does not establish a complete, stable writer set.**

B6 equates every container process with the PIDs in one `cgroup.procs`. For ordinary domain cgroups, that file lists direct members; descendant cgroups require traversal. Membership can also change during enumeration. These are documented kernel semantics, not observed production topology. [B6](/home/tony/projects/hamutay/docs/superpowers/specs/2026-11-04-camera-source-b-design.md:107), [kernel documentation](https://docs.kernel.org/admin-guide/cgroup-v2.html#organizing-processes-and-threads)

**Failure scenario—hypothesis:** the enumerated writer forks a child inheriting the audit descriptor, then closes its own descriptor or exits. The saved PID list contains no remaining holder, so the job seals the file while the omitted child can still append. A writer in an unvisited descendant cgroup presents the same problem. The existing probe establishes HUP reopening, not an invariant excluding these cases. [Facts §7](/home/tony/projects/hamutay/docs/superpowers/specs/2026-11-04-camera-source-b-design.md:30)

The Docker Desktop lookup also needs an executable contract:

- `.State.Pid` supplies a PID, not a cgroup path.
- Read `/proc/<pid>/cgroup` in the Docker daemon host’s PID/cgroup namespace, then resolve that path against the corresponding cgroup mount.
- On Docker Desktop for WSL2, explicitly provide access to that environment; the CLI running in Ubuntu does not make Ubuntu’s `/proc/<pid>` the correct lookup. Docker Desktop runs in its own `docker-desktop` distribution. [Docker documentation](https://docs.docker.com/desktop/features/wsl/#wsl-2-security-in-docker-desktop)
- Require a supported hierarchy, recursive coverage where applicable, container-generation validation across inspection, and fail-closed behavior for discovery failures—not just unreadable descriptor directories.

A wrong local PID could select an unrelated process with no audit descriptor and falsely permit sealing. That is a **hypothesis**; I did not inspect the running container.

The camera reader itself intentionally holds the file outside the container. The safety requirement concerns every possible **writer**, rather than every holder indiscriminately.

**C. Significant — the bindVars suffix predicate is decidable, but does not reliably identify metadata.**

B4 removes any trailing `, with bindVars {…}` before the statistics marker. Consider this query:

```aql
RETURN 1 // , with bindVars {"note":"example"}
```

**Failure scenario—hypothesis:** the server logs the full query without actual bind variables. The prescribed rule strips part of its comment and hashes different bytes from the submitted query. This follows from B2’s recognized comment syntax and B4’s unconditional suffix rule; this particular query was not probed. [B2–B4](/home/tony/projects/hamutay/docs/superpowers/specs/2026-11-04-camera-source-b-design.md:78)

“Is this suffix a JSON object?” is a decidable syntactic question. It requires proper JSON string/escape handling—brace counting is insufficient. “Was this object appended by the logger?” is a separate question the rule does not settle. Specify and demonstrate an unambiguous framing contract, or explicitly narrow the claimed hash semantics.

For the **last statistics marker**, the proposed query-string attack alone does **not** break the rule: if the genuine statistics suffix follows the entire query and bindVars, every marker inside those inputs precedes it. Last occurrence is then correct.

What remains unestablished is the complete trailing grammar, especially for failed or damaged lines. **Conditional failure scenario—hypothesis:** a line lacks genuine statistics but contains the marker inside its query; substring detection accepts that fake boundary. Require validation of the complete suffix and captured successful/failed fixtures before claiming general soundness. [B4 and Tests](/home/tony/projects/hamutay/docs/superpowers/specs/2026-11-04-camera-source-b-design.md:89)

**D. Significant — loss detection now depends on container-log retention without specifying that prerequisite.**

B7 scans `docker logs --since <last run>`. The probe says dropped audit lines are visible **only** in the container log. [B7](/home/tony/projects/hamutay/docs/superpowers/specs/2026-11-04-camera-source-b-design.md:120), [probe](/home/tony/projects/hamutay/docs/superpowers/specs/2026-11-04-camera-source-b-probe.md:50)

**Failure scenario—hypothesis:** audit errors occur during an interval whose container logs are rotated away before the next scan, particularly during timer downtime. The subsequent scan returns no retained errors, so those losses produce no ledger entry.

Define supported logging configurations, retention requirements, durable scan progress, and a gap when complete log coverage cannot be established. The current text promises detection without establishing its input remains available.

**E. Significant — moving the ledger fixes its location, but r3 drops explicit write-before-delete ordering.**

R2 required recording overflow before deletion; r3 says “deletes … logging each,” without durable ordering. B5 specifies fsync for checkpoints, but B7 gives no corresponding ledger guarantee. [B7](/home/tony/projects/hamutay/docs/superpowers/specs/2026-11-04-camera-source-b-design.md:115)

**Failure scenario—hypothesis:** the job deletes an unread sealed file, then crashes before recording its loss—or the ledger append remains only buffered. An unread file that the reader never discovered cannot reliably be reconstructed from its checkpoint.

Require durable loss accounting before unlinking, and explicit behavior when that accounting fails.

**F. Minor — mount installation has contradictory sequencing.**

Step 3 says the audit mount does not yet exist and is installed in step 6a; step 6a says it is mounted before step 6. [Cutover steps 3–6a](/home/tony/projects/hamutay/docs/superpowers/specs/2026-11-04-camera-source-b-design.md:165)

**Failure scenario—hypothesis:** an operator follows the installation statement and reaches recreation before the required mount exists. Move mount installation/readiness explicitly before recreation.

The spec is **not yet sufficient for complete blind tests**. In addition to the issues above:

- B4 says exact fixtures and expected results “are committed.” `git ls-tree` at `302612d` contains no `tests/fixtures/arango_audit/`; that directory is also absent locally. The probe contains abbreviated examples, not substitute fixtures. [B4](/home/tony/projects/hamutay/docs/superpowers/specs/2026-11-04-camera-source-b-design.md:95)
- Canonical key serialization, coalescing/replay boundaries, and durable spool behavior remain unspecified. The earlier replay counterexample still applies: store aggregate A, crash before checkpoint, replay A with newly arrived B under A’s key, then discard the conflict and checkpoint beyond B. This is a retained round-two issue, not newly introduced by r3. [Round-two tests requirements](/home/tony/projects/hamutay/docs/superpowers/specs/2026-11-04-camera-source-b-review-2.md:76)
- Seal, ledger, and log-discovery failure cases need explicit expected outcomes, beyond successful-path integration tests. [Tests](/home/tony/projects/hamutay/docs/superpowers/specs/2026-11-04-camera-source-b-design.md:189)

No files were modified; no privileged commands, container/service operations, or connections to port 8529 were performed.

