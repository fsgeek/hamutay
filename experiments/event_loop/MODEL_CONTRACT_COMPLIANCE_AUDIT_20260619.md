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

Protocol creation in progress. Live result pending.
