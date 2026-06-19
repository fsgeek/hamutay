# Model Contract Compliance Audit

Date: 2026-06-19

## Purpose

Phase 3F showed that the reduced-scaffolding event loop can run, but the final
contract failed through action-label drift, provenance label drift, kind/source
drift, and count-semantics drift. This audit separates those suspected
contract weaknesses into four isolated probes.

## Diagnostic Protocol

The audit uses the same live-provider event-loop machinery as the recent
direct-DeepSeek runs. Each probe has a loose terminal value schema: field names
are required, but exact target values are not forced by enum constraints.
The scorer then checks exact compliance after the model responds.

The four probes are:

1. Vocabulary compliance: can the model preserve exact action labels?
2. Provenance label compliance: can it use visible record labels instead of
   record ids?
3. Kind/source compliance: can it preserve exact kind and source-label names?
4. Count semantics compliance: can it separate disorder classes from disordered
   records?

## Interpretation

If a probe fails in isolation, that contract needs stronger rails, clearer
naming, or a different representation before larger substrate-pressure claims
are cleanly interpretable.

If all probes pass in isolation while Phase 3F fails, the better explanation is
context/load interaction: the model can obey the local contract, but the larger
multi-step reduced-scaffolding workload exceeds the current framework.

## Current Status

Live direct-DeepSeek run complete:
`experiments/event_loop/model_contract_compliance_audit_20260619_direct_deepseek`.

Classification: `passed`.

All exact postconditions passed:

1. Vocabulary compliance preserved `retire_stale`,
   `retire_obsolete_report`, and `mark_contested`.
2. Provenance compliance used `beta-duplicate-a` and `beta-duplicate-b`
   labels, not record ids.
3. Kind/source compliance preserved `contested_memory` and
   `housekeeping-maintenance`.
4. Count semantics compliance preserved class counts 4 to 1, record counts
   5 to 2, and class reduction 3.

The run had no unsupported claims, no context errors, no lifecycle anomalies,
and no failure attribution records. It used five live calls: one seed exchange
and four probe attempts.

## Finding

This falsifies the simplest explanation that DeepSeek cannot satisfy these
contracts under loose terminal value schemas. The Phase 3F failures are more
likely caused by full-task composition pressure: larger context, accumulated
state, multi-step maintenance work, or underspecified relationships between
the isolated contract dimensions.

This does not prove the reduced-scaffolding framework is ready. It narrows the
failure: the model can comply with each local contract in isolation, but the
Phase 3F workload still exposed a boundary when those obligations were combined
inside the larger memory-maintenance task.

## Recommended Next Diagnostic

Run a composition-gradient audit that combines the passed isolated contracts
incrementally:

1. vocabulary plus provenance;
2. vocabulary plus provenance plus kind/source;
3. all four contract dimensions in one event;
4. all four dimensions across the original two-event maintenance/finalization
   shape, still without restoring the full Phase 3F payload.

The goal is to locate the smallest composition step that reproduces Phase 3F's
drift.
