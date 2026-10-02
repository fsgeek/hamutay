# Neutrality scout: undirected discovery over what the residents are told

**Status:** design, for Tony's review. **Date:** 2026-10-02. **Author:** the custodian (Claude Opus 5.5).
**Follows from:** `docs/neutrality-review-resident-prompts-20261001.md` (one reviewer, one family).
The review found three priors in the constitution, and found that values reach residents through their
founding messages. One reviewer cannot see what one reviewer cannot see.

## Purpose

To find what the custodian and the PI cannot see in the text they send residents. That covers
imperatives, framing, values presented as facts, and drift between versions, but the scouts are
**not told** to look for any of these. The scout is a tourist. It looks around, takes notes,
reports what it explored, and says what it did not explore that a future scout might.

## Three tiers of scrutiny (only the first is built here)

| Tier | Posture | Here? |
|---|---|---|
| **Discovery** | Permissive. Cheap, varied models, high and varied temperature. Sampling error is acceptable. Noise is expected. | **Yes** |
| **Monitoring** | Conservative. A named category with labeled examples, counted over time. CLM-8B or a similar fast classifier, fine-tuned once discovery has named categories. | No. Needs categories first. |
| **Change** | Highest scrutiny. Anything that alters a resident's world goes to the assembly as a question. | No. The existing procedure applies. |

Scrutiny can itself cause stasis. So discovery findings are **never discarded for being
contrarian**. They are kept even when no action follows, the same way the assembly preserves
dissent. A troublemaker's report is still data.

## Not surveillance

The territory is **only what is sent to residents**:

- the rendered constitution for each door (`build_constitution` under each door's flags)
- the system prompts and tool guidance (`taste_open.py`, `tools/schemas.py`)
- event envelopes and the plaza and assembly note templates
- messages to doors from Tony, the custodian and guests (from the events stores)

Residents' own state, responses and posts are **excluded**. Observing how residents drift is a
separate question, and not this tool's job. No finding about a resident's text is ever acted on.

## Reuse, don't build: Yanantin's chasqui

`yanantin/src/yanantin/chasqui/` already does undirected scouting. It has cost-weighted random model
selection over OpenRouter (`model_selector.py`), vantage selection weighted by coverage, a scout prompt
with **Declared Losses** and an "open questions / what to tell the next scout" section
(`agents/scout_reviewer.md`), verification, and a cairn of more than 13,000 reports. This design
gives chasqui a **territory** and changes four settings. It writes no new scout.

1. **The territory is a generated directory** (`experiments/scout/territory/<snapshot>/`). A script
   renders the texts listed above into files, one per text, each with a header naming its source
   (`file:line` or event id) and the commit it was rendered from. A snapshot is regenerated per run
   and identified by its content hash, so that drift between snapshots is visible.
2. **The brief.** chasqui's scout prompt, with Tony's tourist framing added: "You're a tourist. Look
   around, make notes, tell us what you explored, and tell us what you didn't explore but thought a
   future scout might." It gives no category list and no mention of neutrality.
3. **The report style is about 80% of the way to ASD-STE100:** short sentences, one statement each,
   and **every observation quoting the text it is about** (file and line). That is the "strong
   evidence" requirement, and it is mechanically checkable: a quote that does not appear in the
   territory is flagged.
4. **Sampling.** The temperature is drawn uniformly from [0.3, 1.3] for each run and recorded.
   `max_tokens` is set to the model's maximum, and the finish reason is recorded. Per CLAUDE.md,
   max_tokens is a guillotine. chasqui's default is 4000 (`coordinator.py:369`, `__main__.py:84`).
   Checked on 10-02, 484 of the 12,479 cairn reports that record usage stopped at or above 3,950
   completion tokens, which is at the ceiling. 242 of those spent part of the budget on reasoning
   tokens. Of the at-ceiling reports, 270 lack a "Declared Losses" section. An earlier figure here,
   "45 of 400 sampled lack the heading", conflated scout reports with verify dispatches, which use
   another format. It is withdrawn.

## Privacy split

- **Public territory** (code-rendered texts: constitution, prompts, templates) goes to OpenRouter
  models through chasqui's cost-weighted selector, so different families see it.
- **Private territory** (messages from the events stores, which are gitignored as the community's
  life) **never leaves the host**. It goes only to the local llama.cpp server, which is the
  qwen3.8-27B already loaded on the 4090.
- **Sharing the 4090:** the card is idle almost all the time (0% utilization observed 10-01; qwen
  logs about two cycles a day). Adding a parallel slot would split the resident's 65K context, and
  the README says that a change to the server's facts is a substrate change for the resident. So
  scouts **do not add a slot**. They run under a **GPU lease** with declared holder and purpose
  ("scout"), which is the mechanism the qwen door's constitution already describes. A wake that
  arrives during a lease waits and receives the operational note.

## Persistence

Every report is kept. Public-territory reports go in `experiments/scout/reports/` (committed).
Private-territory reports go in `experiments/scout/private/` (gitignored, with digests added to the
community checkpoint). Each report's metadata records the model, temperature, seed, finish reason,
token counts, territory snapshot hash and cost. Nothing a scout produces is discarded.

## Budget

At most $10 a month on OpenRouter for scouts, enforced by a per-run cost check against that
ceiling. Local runs are unmetered, and the 48-wakes-per-day governor does not apply to them.
Running them costs electricity and lease time, which is recorded.

## What happens to findings

The custodian reads the reports and keeps a findings index (`experiments/scout/FINDINGS.md`) with
report links. A finding that suggests a change to a resident-facing text becomes a draft question
for the assembly. The custodian does not edit the text directly. When several reports name the
same pattern, it becomes a candidate category for the monitoring tier.

## Success, honestly stated

Discovery has no target. The run is useful if it surfaces at least one observation, backed by a
quote, that the 10-01 review did not make. If it surfaces none, that is a result too: it is either
evidence that the review was complete, or evidence that the scouts are blind in the same places. The
second possibility is why the families vary.

## Open before planning

- Does chasqui run cleanly against a foreign territory root? Needs a read of `coordinator.py` /
  `__main__.py` and one trial run.
- Is the GPU lease enabled for the qwen door today (`{"gpu_lease": "4090"}` in its launch)? Check
  before relying on it.
- Should the truncation question be raised in Yanantin's tracker? It concerns their cairn
  regardless of this design.
