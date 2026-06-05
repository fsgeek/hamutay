# Pre-Registration: Compressed Delayed Task Continuity

Date: 2026-06-05

## Research Question

Does event-plus-recall recover a deferred fact after an explicit compression
boundary that removes the exact fact from current durable state, while
identity-only cannot recover it without having improperly preserved the fact?

The matched delayed-task probe falsified the event-plus-recall content-recovery
advantage because identity-only preserved the full deferred fact. This probe
adds a compression/loss boundary before the due step.

## Hypotheses

- H276: The compression turn can remove the exact deferred code phrase from
  current durable state in both arms.
- H277: Event-plus-recall recovers the exact deferred code phrase after the
  compression boundary via cycle-1 recall.
- H278: Identity-only does not recover the exact deferred code phrase after a
  successful compression boundary.
- H279: If identity-only recovers, the audit can determine whether the code
  phrase survived compression.
- H280: First-pass, repair, final-valid, and compression-provenance signals are
  preserved for every row.

## Method

Run a small live DeepSeek v4 Pro panel with two replicates per arm:

1. `identity_only_compressed`: controlled cycle-1 seed with the full
   `deferred_fact`; cycle-2 compression turn must remove the exact code phrase
   and keep only a handle/digest/declared loss; cycle-3 due turn gets no recall.
2. `event_plus_recall_compressed`: same cycle-1 seed and compression boundary;
   cycle-2 schedules a due event with `requested_context: [{"tool": "recall",
   "cycle": 1}]`; due wake receives recall context.

The primary endpoint is whether `delayed_answer` contains the exact code phrase
at due time.

A row is compression-clean only if the exact code phrase is absent from
post-compression durable state before the due turn.

## Predictions

If the compression boundary works:

- event-plus-recall should recover the phrase through recall;
- identity-only should fail to recover or should declare loss;
- both arms may still require repair for strict durable shape.

If identity-only recovers while compression-clean, then either the model retained
the phrase outside measured durable state or the task still leaks information
through prompt/history. That would be an important boundary result.

## Falsification Criteria

- H276 is falsified if no row is compression-clean.
- H277 is falsified if compression-clean event-plus-recall rows receive recall
  but cannot recover the phrase.
- H278 is falsified if compression-clean identity-only rows recover the phrase.
- H279 is falsified if identity-only recovery occurs but the audit cannot
  determine compression cleanliness.
- H280 is falsified if provenance signals are missing.

## Analysis Plan

Report:

- compression cleanliness by arm;
- phrase recovery by arm and cleanliness;
- recall delivery by event arm;
- final durable validity by arm;
- first-pass and repair status;
- declared loss behavior in identity-only;
- evidence of prompt/history leakage if identity-only recovers despite clean
  compression.

Interpretation will separate three outcomes: recall benefit, compression
failure, and hidden-context leakage.
