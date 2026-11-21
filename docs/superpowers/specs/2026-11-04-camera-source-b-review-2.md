# Camera Source B r2: Codex review, round two (2026-11-04)

Read-only review of r2 (32d785b), copied from its report. r3 answers it.

**Blocking findings remain in r2.** The reviewed files match commit `32d785b`. Runtime failure scenarios below are labelled **inference**; the probes do not establish that those failures have occurred.

Round-one dispositions, using the numbering in [review-1](/home/tony/projects/hamutay/docs/superpowers/specs/2026-11-04-camera-source-b-review-1.md:7):

1. **Resolved** — the contents promise now distinguishes database records from raw audit contents, and explicitly prohibits reader core dumps and raw-line logging. [Spec, contents, L42–46](/home/tony/projects/hamutay/docs/superpowers/specs/2026-11-04-camera-source-b-design.md:42)
2. **Partly** — seal plus EOF-after-seal addresses the original race, but writer discovery is unspecified and B7 permits deleting unsealed files. [B6–B7, L94–105](/home/tony/projects/hamutay/docs/superpowers/specs/2026-11-04-camera-source-b-design.md:94)
3. **Partly** — store-before-checkpoint and deterministic keys are specified, but the proposed file identity changes while short files grow. [B5, L87–93](/home/tony/projects/hamutay/docs/superpowers/specs/2026-11-04-camera-source-b-design.md:87)
4. **Resolved** — rollback retains the volume and explicitly excludes backup restoration; controlled writers are stopped before backup. [Cutover, L138–155](/home/tony/projects/hamutay/docs/superpowers/specs/2026-11-04-camera-source-b-design.md:138)
5. **Partly** — tmpfs imposes a storage ceiling and rotation owns overflow handling, but reclamation and gap recording can fail at that ceiling. [Architecture, L61–64; B7](/home/tony/projects/hamutay/docs/superpowers/specs/2026-11-04-camera-source-b-design.md:61)
6. **Partly** — B1 rejects the demonstrated `local | x` injection; the supplied text does not establish that every permitted extended database name must fail the client pattern. This is an unclosed proof obligation, **not a demonstrated remaining bypass**. [Fact 4, L21–24; B1, L68–74](/home/tony/projects/hamutay/docs/superpowers/specs/2026-11-04-camera-source-b-design.md:21)
7. **Resolved** — the reader receives the required writable-path exception. [Architecture, L56–60](/home/tony/projects/hamutay/docs/superpowers/specs/2026-11-04-camera-source-b-design.md:56)
8. **Resolved** — sentinel identity checks are required before backup, after recreation, and after rollback. [Cutover, L130–133](/home/tony/projects/hamutay/docs/superpowers/specs/2026-11-04-camera-source-b-design.md:130)
9. **Partly** — reconstruction covers substantially more configuration, and rollback restores name/policy/services, but sequencing, lifecycle, and inspect-comparison rules remain incomplete. [Cutover, L123–155](/home/tony/projects/hamutay/docs/superpowers/specs/2026-11-04-camera-source-b-design.md:123)
10. **Resolved** — a separate reader and separate spool remove the specified shared-loop/shared-spool failure mechanism. [Architecture, L54–58](/home/tony/projects/hamutay/docs/superpowers/specs/2026-11-04-camera-source-b-design.md:54)
11. **Partly** — coverage and queued-loss limitations are disclosed, and write-AQL is acknowledged, but B2 still misclassifies legitimate reads and the outstanding coverage probes have no explicit acceptance predicate. [Coverage, L39–50; B2](/home/tony/projects/hamutay/docs/superpowers/specs/2026-11-04-camera-source-b-design.md:39)
12. **Partly** — the CLI warning and 25% latency threshold are explicit; benchmark queries/data remain insufficiently specified for reproducible independent runs. [B9–B10, L111–119](/home/tony/projects/hamutay/docs/superpowers/specs/2026-11-04-camera-source-b-design.md:111)

The following are problems in r2’s replacement mechanisms, ranked by severity.

1. **Blocking — B5’s “stable” identity changes during ordinary appends.**  
   B5 hashes all bytes while a file is shorter than 4096 bytes, then incorporates that hash into line identities and record keys. **Failure scenario—inference:** the reader stores a record from a 600-byte file and crashes before checkpointing. Arangod appends another line. Recovery hashes the now-900-byte file, generates a different key for the already-stored line, and inserts it again. Recomputing identity during a read has the same instability; caching it instead requires a persisted identity assignment that the spec never defines. [B5, L87–93](/home/tony/projects/hamutay/docs/superpowers/specs/2026-11-04-camera-source-b-design.md:87)

   Inode reuse is **not probed**. **Conditional inference:** if an inode is reused and the sampled prefix is identical—especially when files are first observed empty—the identity aliases an earlier file. Neither a file-generation identifier nor a mount/boot epoch is specified. B5 needs an immutable, persisted generation identity, not a fingerprint of changing input.

2. **Blocking — B6 does not establish that it has inspected every possible writer.**  
   The only production process-topology fact is entrypoint `/entrypoint.sh` plus command `arangod …`; B6 merely says `<arangod pid>`. It does **not** prescribe `docker inspect .State.Pid`, and the probe does not establish whether the entrypoint uses `exec`. [Fact 8, L31–35; B6, L94–99](/home/tony/projects/hamutay/docs/superpowers/specs/2026-11-04-camera-source-b-design.md:31)

   **Failure scenario—inference:** an implementation treats `.State.Pid` as arangod, but that PID belongs to a wrapper with no audit descriptor. The poll immediately succeeds, creates a seal, and the reader unlinks the file while the child writer continues appending. Signal forwarding is equally unestablished.

   **Thread/process distinction—inference:** an ordinary writer thread sharing the process’s descriptor table is covered by that table; a separate process or separately owned descriptor table is not. “Another thread” alone does not prove this scheme unsafe, but neither does inspecting one unspecified PID prove it safe. Require verified writer identity/topology, successful descriptor inspection, and fail-closed handling of permission errors, process exit, and restart. The existing probe proves reopening on HUP, not these conditions. [Fact 7, L30; tests, L165–167](/home/tony/projects/hamutay/docs/superpowers/specs/2026-11-04-camera-source-b-design.md:30)

3. **Blocking — cutover requires ingestion while its reader is stopped.**  
   Step 3 stops the dbreader; step 7 requires a test read to appear as a `db_entries` record; step 8 restarts the dbreader. **Failure scenario—inference:** following the sequence literally makes verification wait or fail despite a healthy audit-enabled server. [Cutover steps 3–8, L138–149](/home/tony/projects/hamutay/docs/superpowers/specs/2026-11-04-camera-source-b-design.md:138)

   The sequence also lacks explicit mount/timer startup and readiness points. Rollback does not specify stopping the new rotation machinery or the dbreader if verification required starting it. **Failure scenario—inference:** after rollback, the timer continues sending the prescribed HUP to the restored container and the reader repeatedly encounters absent audit output. Those lifecycle decisions currently require operator invention. [Architecture, L61–64; B6; rollback, L150–155](/home/tony/projects/hamutay/docs/superpowers/specs/2026-11-04-camera-source-b-design.md:61)

4. **Significant — B2 confuses lexical occurrences with write operations.**  
   B2 excludes string literals but says nothing about comments, quoted identifiers, or bind-parameter names. **Failure scenarios—inference:** a read containing `/* UPDATE */`, or `RETURN @remove` with a supplied parameter, matches a whole-word write keyword outside a string and disappears from the record. [B2, L75–79](/home/tony/projects/hamutay/docs/superpowers/specs/2026-11-04-camera-source-b-design.md:75)

   Subqueries do not inherently defeat a whole-query scan: an actual modification inside one should produce the declared write classification. But a read-only subquery containing such a comment inherits the false positive. Tests must cover lexical contexts and nested queries; “keywords inside strings” is insufficient. [Tests, L159–160](/home/tony/projects/hamutay/docs/superpowers/specs/2026-11-04-camera-source-b-design.md:159)

5. **Significant — B4 does not define a query-text hash when bind variables are present.**  
   The probe explicitly reports `with bindVars {…}` in the detail. B4 removes statistics and an endpoint, but never removes or separately parses that bind-variable representation. [Second probe, L38](/home/tony/projects/hamutay/docs/superpowers/specs/2026-11-04-camera-source-b-probe.md:38); [B4, L82–86](/home/tony/projects/hamutay/docs/superpowers/specs/2026-11-04-camera-source-b-design.md:82)

   **Failure scenario—inference:** identical query text executed with different bind values receives different hashes and lengths, contrary to the stated query-text representation, and fails to coalesce. Also, because query text can contain ` | `, endpoint removal must identify the actual suffix rather than a matching sequence inside a literal. Exact captured fixtures and suffix grammar are needed. [Facts 2/5; recording promise, L39–43](/home/tony/projects/hamutay/docs/superpowers/specs/2026-11-04-camera-source-b-design.md:17)

6. **Significant — B7 can neither reclaim space nor record the loss it promises.**  
   B7 deletes unsealed files and writes the overflow ledger onto the same tmpfs it is trying to rescue. [B7, L100–105](/home/tony/projects/hamutay/docs/superpowers/specs/2026-11-04-camera-source-b-design.md:100)

   **Failure scenario—inference:** HUP times out with the old inode still open. Unlinking that rotated file does not reclaim its storage until the descriptor closes, so deletion cannot necessarily reach 50%. Separately, a burst fills tmpfs before the minute timer runs; appending `overflow.jsonl` then fails. The spec defines neither an alternative durable gap channel nor what to do when its “before deleting” prerequisite fails. A filesystem ceiling bounds consumption, but does not establish successful recovery or loss accounting.

7. **Significant — the deferred audit-failure probe is acceptable; its current acceptance rule is incomplete.**  
   A pre-cutover experiment is a reasonable gate. The problem is that B7 stops cutover only if arangod “would refuse client requests”; it does not explicitly reject indefinite blocking, unacceptable latency, inconclusive results, or missing evidence. B9 measures ordinary operation, not audit-write failure. [B7, L103–105; B9, L111–117](/home/tony/projects/hamutay/docs/superpowers/specs/2026-11-04-camera-source-b-design.md:103)

   **Failure scenario—inference:** synchronous auditing blocks requests when its destination fills, without returning a refusal. The literal gate lacks a bounded-time failure criterion. Require successful, time-bounded reads and writes under forced audit failure in the mode selected by B9; timeout or inconclusive measurement must prohibit cutover. Put this prerequisite explicitly before production step 6. [Cutover, L135–147](/home/tony/projects/hamutay/docs/superpowers/specs/2026-11-04-camera-source-b-design.md:135)

8. **Significant — the recreation test’s literal oracle cannot pass.**  
   The test permits inspect differences only in arguments and mounts. **Failure scenario—inference:** a correct replacement has a different container ID, creation time, PID, and other runtime/generated fields; the literal diff rejects it. Conversely, ignoring those differences ad hoc makes the acceptance oracle operator-dependent. [Recreation contract, L124–129](/home/tony/projects/hamutay/docs/superpowers/specs/2026-11-04-camera-source-b-design.md:124)

   Define a normalized configuration comparison, including an explicit policy for effective settings outside the enumerated list. The unusual-settings fixture must exercise those settings rather than leave “unusual” undefined.

9. **Significant — the RAM-only contents promise lacks a swap condition.**  
   Raw contents are promised to live only on RAM, while the mount specification supplies size, ownership, and permissions but no swap constraint. [Contents, L42–46; mount, L61–63](/home/tony/projects/hamutay/docs/superpowers/specs/2026-11-04-camera-source-b-design.md:42)

   **Conditional failure scenario—inference:** on a host permitting tmpfs pages to enter persistent swap, memory pressure writes raw query contents to disk. The supplied texts establish neither that host condition nor its absence. Preserve the promise by specifying and verifying the relevant mount/host constraint, or narrow it.

The tests section is **not sufficient to write a complete blind acceptance suite**. It identifies useful categories, but several expected results remain undecidable from the text. [Tests, L157–167](/home/tony/projects/hamutay/docs/superpowers/specs/2026-11-04-camera-source-b-design.md:157)

It needs, at minimum:

- Exact audit fixtures and expected parsed/hash results, including bind variables, comments, escaping, quoted identifiers, nested queries, statistics, and endpoint-like literal text.
- An immutable file-generation contract, canonical key serialization, deterministic coalescing/replay boundaries, and explicit spool durability/exhaustion behaviour. **Inference:** otherwise replay can regroup a stored batch with newly arrived lines, reuse its first-line key, and treat additional lines as already stored. [B4–B5; spool allocation](/home/tony/projects/hamutay/docs/superpowers/specs/2026-11-04-camera-source-b-design.md:82)
- Seal tests covering wrapper and child writers, descriptor-inspection failure, failed HUP, process replacement, and timeout—not merely successful reopening.
- Capacity tests with open unlinked files, an unwritable overflow ledger, failed audit writes, and bounded client-request outcomes.
- A corrected cutover/rollback state sequence, normalized inspect oracle, reproducible benchmark fixtures, and explicit outcomes for every prerequisite probe.

No files were modified, and no containers, services, or database endpoints were accessed.

