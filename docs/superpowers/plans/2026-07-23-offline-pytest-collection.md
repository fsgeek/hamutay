# Offline Pytest Collection Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Prevent bare pytest collection from executing the legacy live Anthropic pressure experiment.

**Architecture:** Restrict pytest's filename convention to the repository's actual `test_*.py` tests through `pyproject.toml`. Preserve the legacy experiment unchanged and explicitly runnable.

**Tech Stack:** pytest configuration in `pyproject.toml`, Python 3.14, uv.

## Global Constraints

- Do not install or use an API credential.
- Do not invoke a live model.
- Do not modify or delete `experiments/taste/pressure_test.py`.
- Preserve discovery of `test_run.py` and `test_score.py` experiment-local tests.

---

### Task 1: Restrict Pytest Filename Discovery

**Files:**
- Modify: `pyproject.toml`

**Interfaces:**
- Consumes: pytest's `python_files` configuration.
- Produces: a bare `uv run pytest` command that collects only `test_*.py` files.

- [ ] **Step 1: Preserve the failing baseline**

Run:

```bash
uv run pytest --collect-only -q
```

Expected: collection imports `experiments/taste/pressure_test.py` and fails while attempting to construct an unauthenticated Anthropic request.

- [ ] **Step 2: Add the minimal configuration**

Append to `pyproject.toml`:

```toml
[tool.pytest.ini_options]
python_files = ["test_*.py"]
```

- [ ] **Step 3: Verify collection is offline and complete**

Run:

```bash
uv run pytest --collect-only -q
```

Expected: exit 0, no `experiments/taste/pressure_test.py` import or API error, and both of these paths appear:

```text
experiments/event_loop/unprompted_celestial_wake_20260723/tests/test_run.py
experiments/event_loop/akrasia_second_family_20260604/test_score.py
```

- [ ] **Step 4: Verify the complete offline suite**

Run:

```bash
uv run pytest -q
git diff --check
```

Expected: pytest exits 0 with no live model call; Git reports no whitespace errors.

- [ ] **Step 5: Commit the policy**

```bash
git add pyproject.toml
git -c user.email=hamutay@wamason.com -c user.name="Tony Mason" \
  -c user.signingkey=01193FA2631C8AE8E4DF266E216D3C9B920813A1 \
  commit -S -m "Keep pytest discovery offline"
```
