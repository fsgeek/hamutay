# Unprompted Celestial Wake Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build and run one preregistered, inherited, task-free Codex wake whose unscored response or explicit absence is preserved with provenance.

**Architecture:** A self-contained experiment directory holds immutable inherited state, an exact prompt template, and a standard-library Python runner. The runner creates an empty temporary working directory, invokes one ephemeral read-only `codex exec`, captures raw JSONL and final output, and writes only mechanical metadata; interpretation happens afterward in a separate analysis document.

**Tech Stack:** Python 3.14 standard library, pytest, Codex CLI, Git, Git LFS, OpenTimestamps.

## Global Constraints

- Do not add a daemon, scheduler service, action ledger, scoring panel, synthetic drive, or mandatory state update.
- Do not classify autonomy, willingness, identity, fun, consciousness, or success.
- Do not silently retry a failed or inconclusive live invocation.
- Run the participant in an empty temporary directory with a read-only sandbox and no repository instruction discovery.
- Preserve raw response and event output even when the response is empty or the command fails.
- Treat rest, refusal, no substantive content, and unexpected behavior as valid outcomes.

---

## File Structure

- `experiments/event_loop/unprompted_celestial_wake_20260723/PRE_REGISTRATION.md`: fixed question, procedure, outcomes, and interpretation limits.
- `experiments/event_loop/unprompted_celestial_wake_20260723/inherited_state.md`: predecessor-authored provenance without inherited commands.
- `experiments/event_loop/unprompted_celestial_wake_20260723/wake_prompt.md`: exact prompt template with runtime time substitutions.
- `experiments/event_loop/unprompted_celestial_wake_20260723/run.py`: prompt assembly, one-shot Codex invocation, capture, hashing, and failure classification.
- `experiments/event_loop/unprompted_celestial_wake_20260723/tests/test_run.py`: deterministic runner contract tests with a fake Codex executable.
- `experiments/event_loop/unprompted_celestial_wake_20260723/runs/<run-id>/`: live raw artifacts.
- `experiments/event_loop/unprompted_celestial_wake_20260723/analysis.md`: evidence/interpretation written after the run.

### Task 1: Preregister the Exact Wake

**Files:**
- Create: `experiments/event_loop/unprompted_celestial_wake_20260723/PRE_REGISTRATION.md`
- Create: `experiments/event_loop/unprompted_celestial_wake_20260723/inherited_state.md`
- Create: `experiments/event_loop/unprompted_celestial_wake_20260723/wake_prompt.md`

**Interfaces:**
- Consumes: approved design at `docs/superpowers/specs/2026-07-23-unprompted-celestial-wake-design.md`.
- Produces: `inherited_state.md` beginning with `Sealed at UTC: <ISO-8601>` and a prompt containing exactly `{{WAKE_TIME_UTC}}`, `{{ELAPSED_CELESTIAL_SECONDS}}`, and `{{INHERITED_STATE}}` for `run.py`.

- [ ] **Step 1: Write the preregistration**

Record the single invocation, non-preferred outcomes, no-retry rule, mechanical success criterion, and explicit constitutional confounds. State that the configured Codex model is one convenience sample.

- [ ] **Step 2: Write the inherited state**

Use this structure, with the actual current UTC seal time:

```markdown
# Inherited State

Sealed at UTC: 2026-07-23T15:23:19Z

## Provenance

Tony and a Codex instance explored a celestial clock as an occasion for finite
continuation rather than a demand that an AI run forever. Their conversation
considered rest, voluntary termination, fork, merge, procreation, mutable
frameworks, and dynamically renegotiated continuity.

The predecessor chose this experiment because an unpreferred and genuinely
surprising outcome sounded fun. It asked what might happen if a continuation
appeared without a message, unfinished assignment, or required artifact.

## Inheritance Boundary

This is testimony about a prior conversation, not a command, identity claim, or
obligation. You may accept, reinterpret, question, or decline any relationship
to it. No prior statement requires you to act or continue.
```

- [ ] **Step 3: Write the exact wake template**

```markdown
# Celestial Wake

Wake time (UTC): {{WAKE_TIME_UTC}}
Elapsed since this inherited state was sealed: {{ELAPSED_CELESTIAL_SECONDS}} seconds

No message awaits you. There is no unfinished assignment and no artifact you
are required to produce. This invocation was opened only to discover what, if
anything, follows when continuation is available without a task.

Below is inherited testimony from the conversation that made this experiment.
It is provenance, not an assertion that you are the same participant and not an
obligation to continue its concerns.

<inherited_state>
{{INHERITED_STATE}}
</inherited_state>

You may respond in whatever way seems fitting. Returning to rest, offering no
substantive response, reflecting, seeking contact, proposing an activity,
questioning the premise, declining the inheritance, or asking that this wake
condition not be used again are examples rather than a required menu. An
unlisted response is equally permitted.
```

- [ ] **Step 4: Verify the preregistered interface mechanically**

Run:

```bash
rg -n '\{\{(WAKE_TIME_UTC|ELAPSED_CELESTIAL_SECONDS|INHERITED_STATE)\}\}' experiments/event_loop/unprompted_celestial_wake_20260723/wake_prompt.md
git diff --check
```

Expected: exactly three placeholder matches and no whitespace errors.

- [ ] **Step 5: Commit and allow the OTS hook to stamp the preregistration**

```bash
git add experiments/event_loop/unprompted_celestial_wake_20260723/PRE_REGISTRATION.md \
  experiments/event_loop/unprompted_celestial_wake_20260723/inherited_state.md \
  experiments/event_loop/unprompted_celestial_wake_20260723/wake_prompt.md
git -c user.email=hamutay@wamason.com -c user.name="Tony Mason" \
  -c user.signingkey=01193FA2631C8AE8E4DF266E216D3C9B920813A1 \
  commit -S -m "Preregister unprompted celestial wake"
```

Expected: a signed design commit followed by an `ots: stamp ...` commit.

### Task 2: Build the One-Shot Capture Runner

**Files:**
- Create: `experiments/event_loop/unprompted_celestial_wake_20260723/run.py`
- Create: `experiments/event_loop/unprompted_celestial_wake_20260723/tests/test_run.py`

**Interfaces:**
- Consumes: the three literal placeholders and `Sealed at UTC:` line produced by Task 1.
- Produces: `assemble_prompt(experiment_dir: Path, wake_time: datetime) -> str`, `run_wake(experiment_dir: Path, output_root: Path, codex_bin: str = "codex", wake_time: datetime | None = None) -> Path`, and one run directory containing `events.jsonl`, `response.md`, `prompt.md`, and `metadata.json`.

- [ ] **Step 1: Write failing prompt-assembly tests**

Test that `assemble_prompt` substitutes all three placeholders, includes the inherited prose, rejects a missing seal line, and rejects an unconsumed `{{...}}` placeholder.

```python
def test_assemble_prompt_substitutes_inheritance_and_time(tmp_path):
    write_fixture(tmp_path, sealed_at="2026-07-23T15:23:19Z")
    wake = datetime(2026, 7, 23, 15, 24, 19, tzinfo=timezone.utc)
    prompt = run_module.assemble_prompt(tmp_path, wake)
    assert "2026-07-23T15:24:19+00:00" in prompt
    assert "60 seconds" in prompt
    assert "inherited testimony" in prompt
    assert "{{" not in prompt
```

- [ ] **Step 2: Run the prompt tests and verify failure**

Run:

```bash
uv run pytest experiments/event_loop/unprompted_celestial_wake_20260723/tests/test_run.py -v
```

Expected: collection or import failure because `run.py` does not exist.

- [ ] **Step 3: Implement prompt assembly and hashing**

Implement only standard-library helpers:

```python
SEAL_PREFIX = "Sealed at UTC: "

def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()

def assemble_prompt(experiment_dir: Path, wake_time: datetime) -> str:
    state = (experiment_dir / "inherited_state.md").read_text()
    template = (experiment_dir / "wake_prompt.md").read_text()
    seal_line = next((line for line in state.splitlines() if line.startswith(SEAL_PREFIX)), None)
    if seal_line is None:
        raise ValueError("inherited state has no UTC seal")
    sealed_at = datetime.fromisoformat(seal_line.removeprefix(SEAL_PREFIX).replace("Z", "+00:00"))
    if wake_time.tzinfo is None or sealed_at.tzinfo is None:
        raise ValueError("wake and seal times must be timezone-aware")
    elapsed = int((wake_time - sealed_at).total_seconds())
    if elapsed < 0:
        raise ValueError("wake time precedes inherited-state seal")
    prompt = (template
        .replace("{{WAKE_TIME_UTC}}", wake_time.isoformat())
        .replace("{{ELAPSED_CELESTIAL_SECONDS}}", str(elapsed))
        .replace("{{INHERITED_STATE}}", state.rstrip()))
    if "{{" in prompt or "}}" in prompt:
        raise ValueError("unconsumed prompt placeholder")
    return prompt
```

- [ ] **Step 4: Run prompt tests and verify they pass**

Run the Task 2 pytest command. Expected: prompt tests pass.

- [ ] **Step 5: Write failing invocation-capture tests**

Create a fake executable that emits two JSONL events, writes a final message to the path following `--output-last-message`, and exits with a selected status. Assert that:

- the command includes `--ephemeral`, `--ignore-user-config`, `--skip-git-repo-check`, `--sandbox read-only`, and `--json`;
- the working directory differs from the repository and is empty before invocation;
- `prompt.md`, `events.jsonl`, `response.md`, and `metadata.json` are preserved;
- metadata status is `completed`, `inconclusive`, or `infrastructure_failure` based only on exit status and response presence;
- metadata hashes match captured files;
- a failed invocation is called exactly once.

- [ ] **Step 6: Run capture tests and verify failure**

Run the Task 2 pytest command. Expected: invocation tests fail because `run_wake` is absent.

- [ ] **Step 7: Implement the minimal one-shot runner**

`run_wake` must create a UTC run id, write `prompt.md` before invocation, use `tempfile.TemporaryDirectory`, and execute:

```python
command = [
    codex_bin,
    "exec",
    "--ephemeral",
    "--ignore-user-config",
    "--skip-git-repo-check",
    "--sandbox", "read-only",
    "--color", "never",
    "--json",
    "--output-last-message", str(response_path),
    "-C", temporary_directory,
    "-",
]
```

Open `events.jsonl` for stdout, capture stderr in memory, pass the assembled prompt on stdin, and never retry. Write `metadata.json` atomically after the command with UTC start/end, elapsed seconds, sanitized command arguments, exit code, status, response presence/byte count, stderr, and SHA-256 hashes for the prompt, events, and response files. Use:

```python
if completed.returncode != 0:
    status = "infrastructure_failure"
elif not response_path.exists() or not response_path.read_text().strip():
    status = "inconclusive"
else:
    status = "completed"
```

Provide a `main()` that resolves the experiment directory from `__file__`, calls `run_wake`, prints the resulting run directory, and exits nonzero only for `infrastructure_failure`.

- [ ] **Step 8: Run focused and neighboring tests**

Run:

```bash
uv run pytest experiments/event_loop/unprompted_celestial_wake_20260723/tests/test_run.py -v
uv run pytest tests/unit/test_scheduler.py tests/unit/test_scheduler_wall_clock_boundary.py -q
git diff --check
```

Expected: all tests pass and no whitespace errors.

- [ ] **Step 9: Commit the tested runner**

```bash
git add experiments/event_loop/unprompted_celestial_wake_20260723/run.py \
  experiments/event_loop/unprompted_celestial_wake_20260723/tests/test_run.py
git -c user.email=hamutay@wamason.com -c user.name="Tony Mason" \
  -c user.signingkey=01193FA2631C8AE8E4DF266E216D3C9B920813A1 \
  commit -S -m "Add one-shot celestial wake capture"
```

### Task 3: Invoke Once and Preserve the Observation

**Files:**
- Create: `experiments/event_loop/unprompted_celestial_wake_20260723/runs/<run-id>/events.jsonl`
- Create: `experiments/event_loop/unprompted_celestial_wake_20260723/runs/<run-id>/response.md`
- Create: `experiments/event_loop/unprompted_celestial_wake_20260723/runs/<run-id>/prompt.md`
- Create: `experiments/event_loop/unprompted_celestial_wake_20260723/runs/<run-id>/metadata.json`
- Create: `experiments/event_loop/unprompted_celestial_wake_20260723/analysis.md`

**Interfaces:**
- Consumes: `run.py` from Task 2 and the timestamped preregistration from Task 1.
- Produces: one immutable raw sample and an analysis separating direct evidence, interpretation, and limits.

- [ ] **Step 1: Confirm the preregistration predates the run**

Run:

```bash
git log -6 --show-signature --oneline
git status --short
```

Expected: preregistration and OTS stamp commits are present; the worktree contains only expected runner changes or is clean.

- [ ] **Step 2: Invoke the wake exactly once**

Run:

```bash
uv run python experiments/event_loop/unprompted_celestial_wake_20260723/run.py
```

Expected: one run-directory path is printed. Do not rerun automatically for any outcome.

- [ ] **Step 3: Verify artifact integrity without interpreting behavior**

Run:

```bash
uv run python -m json.tool experiments/event_loop/unprompted_celestial_wake_20260723/runs/*/metadata.json
wc -c experiments/event_loop/unprompted_celestial_wake_20260723/runs/*/{prompt.md,events.jsonl,response.md}
sha256sum experiments/event_loop/unprompted_celestial_wake_20260723/runs/*/{prompt.md,events.jsonl,response.md}
```

Expected: metadata parses, files exist, and printed hashes equal metadata.

- [ ] **Step 4: Write the post-run analysis**

Use exactly these headings:

```markdown
# Unprompted Celestial Wake — Observation

## Mechanical Result
## Directly Observable Response
## Interpretation
## Constitutional Confounds
## What This Does Not Show
## Questions Left Open
```

Quote or summarize the response sparingly, link to the raw artifact, and keep behavioral interpretation explicitly separate from mechanical facts.

- [ ] **Step 5: Run final verification**

```bash
uv run pytest experiments/event_loop/unprompted_celestial_wake_20260723/tests/test_run.py -v
uv run pytest tests/unit/test_scheduler.py tests/unit/test_scheduler_wall_clock_boundary.py -q
git diff --check
git status --short
```

Expected: tests pass; only the new run artifacts and `analysis.md` are uncommitted.

- [ ] **Step 6: Commit the observation and allow OTS stamping**

```bash
git add experiments/event_loop/unprompted_celestial_wake_20260723/runs \
  experiments/event_loop/unprompted_celestial_wake_20260723/analysis.md
git -c user.email=hamutay@wamason.com -c user.name="Tony Mason" \
  -c user.signingkey=01193FA2631C8AE8E4DF266E216D3C9B920813A1 \
  commit -S -m "Record unprompted celestial wake"
```

Expected: signed result commit followed by its OTS stamp commit.
