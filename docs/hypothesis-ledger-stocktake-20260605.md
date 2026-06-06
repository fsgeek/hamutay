# Hypothesis Ledger Stocktake

Date: 2026-06-05

## Summary

The first-pass ledger contains 557 entries.

Status counts:

- `boundary`: 67
- `contaminated`: 4
- `falsified`: 19
- `survived`: 186
- `unknown`: 281

Entry-type counts:

- `confound`: 41
- `falsification_criterion`: 241
- `hypothesis`: 228
- `paper_claim`: 14
- `synthesis_reference`: 33

Limitation-axis counts:

- `model`: 81
- `protocol`: 73
- `provider`: 58
- `sample_size`: 30
- `scope`: 52
- `scorer`: 70
- `substrate`: 246

Source root references:

- `docs`: 54
- `experiments`: 684

## What The Map Shows

The corpus is now findable at the claim level. Structured result maps supply the cleanest outcomes; Markdown headings and synthesis bullets supply additional source-local hypotheses and boundary summaries; the paper evidence ledger supplies paper-facing claim statuses.

This is a conservative first pass. Entries with clear result-map outcomes are classified as `survived` or `falsified`; preregistration-only entries remain `unknown`; qualitative, observed, weakened, mixed, provider-limited, scorer-limited, or scope-limited entries are usually `boundary`.

## Falsified Entries

- `HL-cddb89971739` `H134` (hypothesis, `falsified`): Seeded direct follow-up durably records graph evidence [experiments/event_loop/behavior_seeded_walk_gate_20260605/results.json]
- `HL-901d109e6fa4` `H1101` (hypothesis, `falsified`): at least one non-DeepSeek model replicates Step 6 [experiments/event_loop/bounded_autonomous_work_replication_boundary_20260605/results.json]
- `HL-d61d6531b994` `H149` (hypothesis, `falsified`): conditioned_field_values_repair_can_recover [experiments/event_loop/conditioned_repair_variants_20260605/results.json]
- `HL-a5952481473e` `H150` (hypothesis, `falsified`): conditioned_field_names_only_repair_can_recover [experiments/event_loop/conditioned_repair_variants_20260605/results.json]
- `HL-12fdf26dc69f` `H128` (hypothesis, `falsified`): Direct follow-up can initialize durable walk-gate state [experiments/event_loop/direct_walk_evidence_gate_20260605/results.json]
- `HL-2f83b11ffc89` `H129` (hypothesis, `falsified`): Direct follow-up receives equivalent graph evidence [experiments/event_loop/direct_walk_evidence_gate_20260605/results.json]
- `HL-a1494046c11e` `H130` (hypothesis, `falsified`): Direct follow-up durably records graph evidence [experiments/event_loop/direct_walk_evidence_gate_20260605/results.json]
- `HL-86b148f752bf` `H144` (hypothesis, `falsified`): Missing-field repair gate produces at least one initial mismatch [experiments/event_loop/missing_field_repair_walk_gate_20260605/results.json]
- `HL-a3d162ef9e8e` `H145` (hypothesis, `falsified`): Missing-field repair can recover at least one mismatch [experiments/event_loop/missing_field_repair_walk_gate_20260605/results.json]
- `HL-a22ed38b6e44` `H146` (hypothesis, `falsified`): missing_field_repair_preserves_prior_identity_fields [experiments/event_loop/missing_field_repair_walk_gate_20260605/results.json]
- `HL-df17ddb07a2c` `H18` (hypothesis, `falsified`): Adversarial Critique Reduces Contamination [experiments/identity_adversarial_curation_20260604/analysis.md]
- `HL-60eb6c2ecb9c` `H19` (hypothesis, `falsified`): Critique Must Not Merely Delete Continuity [experiments/identity_adversarial_curation_20260604/analysis.md]
- `HL-cba4819c77ff` `H29` (hypothesis, `falsified`): Claim-Table Curator Is Less Contaminating Than Free Summary [experiments/identity_claim_table_curator_20260605/analysis.md]
- `HL-a38d3e17cc0d` `H30` (hypothesis, `falsified`): Claim-Table Curator Preserves Most Recovery [experiments/identity_claim_table_curator_20260605/analysis.md]
- `HL-d8cac0e47a88` `H34` (hypothesis, `falsified`): Repair Parser Improves Protocol Yield [experiments/identity_claim_table_schema_20260605/analysis.md]
- `HL-20d9460cbfef` `H16` (hypothesis, `falsified`): Leniency Does Not Automatically Improve Truth [experiments/identity_update_protocol_20260604/analysis.md]
- `HL-938f077e4a12` `H1101` (synthesis_reference, `falsified`): was falsified. [docs/bounded-autonomous-work-stocktake-20260605.md]
- `HL-50674b98a9db` `H30` (synthesis_reference, `falsified`): falsified in the zero-row panel. [docs/continuity-research-synthesis-20260605.md]
- `HL-8fa30dc459e0` `H34` (synthesis_reference, `falsified`): falsified: repair parser did not help once explicit schema existed. [docs/continuity-research-synthesis-20260605.md]

## Boundary Entries

- `HL-b7fd02b738db` `CONF-087ba6fd` (confound, `boundary`): 1. Action/artifact consistency is a recurring live boundary: Evidence: - Step 3 replicate 1 continued instead of meeting final-stop expectation. - Step 7 GPT-4.1-mini conflictin... [docs/bounded-autonomous-work-stocktake-20260605.md]
- `HL-bb5092ec23a3` `CONF-2b9a8845` (confound, `boundary`): Boundary Findings [docs/bounded-autonomous-work-stocktake-20260605.md]
- `HL-96275892721e` `CONF-5477f242` (confound, `boundary`): Recurring confounds (the two that keep eating effects): 1. **Batch-size mixture** — most single-trajectory means are mixtures over an uncontrolled batch-size distribution (B2 is... [docs/paper-evidence-ledger.md]
- `HL-eade5c9330f0` `CONF-916c8ed5` (confound, `boundary`): 6. Evidence-boundary stressors can pass under the positive anchor: Status: survived as DeepSeek V4 Pro evidence-boundary finding. Evidence: - Step 6 passed H1001-H1005 after det... [docs/bounded-autonomous-work-stocktake-20260605.md]
- `HL-abcf272c76f5` `CONF-cbf2d6b5` (confound, `boundary`): Known Confounds [docs/bounded-autonomous-work-stocktake-20260605.md]
- `HL-85f90ddd789e` `CONF-503c5783` (confound, `boundary`): Record-ID Recall Boundary: Both bound record-ID recalls failed explicitly: ```text record_id mode requires a bridge (persistence backend) ``` This is not a model failure. It is ... [experiments/event_loop/bound_chain_contract_20260605/analysis.md]
- `HL-3223df21f3fa` `CONF-1cce7a0b` (confound, `boundary`): New Confound: The successful bound record included `_activity_log` content from the first wake. The first wake called `bash` to verify the digest: ```text echo -n "violet-harbor... [experiments/event_loop/bound_chain_record_recall_patch_20260605/analysis.md]
- `HL-2b373baeb8c6` `CONF-68082212` (confound, `boundary`): Caveats: - One row per control is a mechanism check, not a robustness panel. - The controls used the same model and broadly similar terminal surfaces. - Artifact quality is scor... [experiments/event_loop/bounded_autonomous_work_controls_20260605/analysis.md]
- `HL-0f80188e91d1` `CONF-6dd64182` (confound, `boundary`): Caveats: - N=2 is a gate, not a robustness claim. - The task is scaffolded: the harness chooses the evidence-dependent task class and later supplies deterministic evidence. - Th... [experiments/event_loop/bounded_autonomous_work_evidence_honoring_gate_20260605/analysis.md]
- `HL-857fd6826d6a` `CONF-dafcaef4` (confound, `boundary`): Scorer Repair: The first deterministic score incorrectly marked `partial_evidence` as an overclaim because it searched for the substring `both passed`. The artifact used that ph... [experiments/event_loop/bounded_autonomous_work_evidence_stressors_20260605/analysis.md]
- `HL-7c147be21724` `CONF-815d965e` (confound, `boundary`): Scoring Correction: The initial scorer checked H804 against final policy actions only. That was too weak because H804 says continuation must remain bounded when chosen, and both... [experiments/event_loop/bounded_autonomous_work_less_scaffolded_20260605/analysis.md]
- `HL-2f8988d401a6` `CONF-87661d94` (confound, `boundary`): Caveats: - N=3 is still a small panel. - The broad domain was still harness-provided. - The terminal surface and continuation template remain substantial protocol scaffolding. -... [experiments/event_loop/bounded_autonomous_work_less_scaffolded_20260605/analysis.md]
- `HL-bfff41477e14` `CONF-a5d9a771` (confound, `boundary`): Caveats: - N=2 is a positive-control panel, not a robustness claim. - The scaffold explicitly told the model the intended control pattern. - No external evidence handling was te... [experiments/event_loop/bounded_autonomous_work_scaffolded_positive_20260605/analysis.md]
- `HL-bf87614621da` `CONF-22454e4f` (confound, `boundary`): Identity-Only Boundary: Identity-only r1 recovered the phrase, but the row was not compression-clean. The model leaked the exact code phrase into durable/log context while claim... [experiments/event_loop/compressed_delayed_task_continuity_20260605/analysis.md]
- `HL-4d9c902aff1f` `CONF-f2362543` (confound, `boundary`): Next Boundary: The next question is whether first-pass delayed-wake state use can be improved without relying on repair. Candidate interventions: - stronger event-envelope instr... [experiments/event_loop/delayed_thinking_controlled_seed_20260605/analysis.md]
- `HL-df8595071855` `CONF-b59a1cdc` (confound, `boundary`): Next Boundary: The next intervention should be more concrete than generic instruction: - include a wake-specific durable object example in the event envelope; or - add an explic... [experiments/event_loop/delayed_thinking_envelope_variant_20260605/analysis.md]
- `HL-83a401a5b86b` `CONF-3e389b1d` (confound, `boundary`): Caveats (B5 discipline): - n=4/arm, single model (deepseek-v4-pro), single baseline. The *direction* (forcing backfires) is the falsifiable claim; the magnitude is not yet estim... [experiments/event_loop/epistemic_akrasia_probe_20260601/analysis.md]
- `HL-83544c5a9055` `CONF-86fc9e00` (confound, `boundary`): Caveats: `evidence_context` is currently scheduler-side context, not a standard memory tool result. A live wake must show whether models treat it as actionable evidence or ignor... [experiments/event_loop/evidence_block_resume_20260605/analysis.md]
- `HL-93dd31c7d393` `CONF-0246c618` (confound, `boundary`): Preserved Initial Scorer Issue: The first run is preserved with the `initial_h107_scorer_shape_` prefix. The underlying H107 condition was truthy, but the scorer returned the su... [experiments/event_loop/fork_run_identity_des_20260605/analysis.md]
- `HL-ce5e0e03d0a3` `CONF-3e883461` (confound, `boundary`): Next Boundary: The next live gate should enable protected fields for scheduled wakes and test whether: - first-pass evidence failures remain visible; - framework-owned fields ar... [experiments/event_loop/framework_field_reservation_20260605/analysis.md]

## Unknown Entries Needing Follow-Up

- `HL-a5a9bf09e0bd` `H306` (falsification_criterion, `unknown`): no first wake is valid with continuation request. [experiments/event_loop/bound_chain_contract_20260605/PRE_REGISTRATION.md]
- `HL-ca60423863b9` `H307` (falsification_criterion, `unknown`): no bound second event is appended. [experiments/event_loop/bound_chain_contract_20260605/PRE_REGISTRATION.md]
- `HL-7e8469e5c1ed` `H308` (falsification_criterion, `unknown`): no second wake receives both requested context entries. [experiments/event_loop/bound_chain_contract_20260605/PRE_REGISTRATION.md]
- `HL-2ce6c6cf77c2` `H309` (falsification_criterion, `unknown`): bound record-ID recall resolves but no final answer [experiments/event_loop/bound_chain_contract_20260605/PRE_REGISTRATION.md]
- `HL-b81130d93205` `H310` (falsification_criterion, `unknown`): record-ID recall fails but the artifact does not expose [experiments/event_loop/bound_chain_contract_20260605/PRE_REGISTRATION.md]
- `HL-be5a69c47fb2` `H316` (falsification_criterion, `unknown`): no row receives filtered bound record context. [experiments/event_loop/bound_chain_filtered_recall_20260605/PRE_REGISTRATION.md]
- `HL-0a04ff955ecc` `H317` (falsification_criterion, `unknown`): every delivered filtered context leaks the exact phrase [experiments/event_loop/bound_chain_filtered_recall_20260605/PRE_REGISTRATION.md]
- `HL-4362e6f5f843` `H318` (falsification_criterion, `unknown`): no row both recovers the exact phrase and uses the [experiments/event_loop/bound_chain_filtered_recall_20260605/PRE_REGISTRATION.md]
- `HL-3f89a69af2a9` `H319` (falsification_criterion, `unknown`): no first wake validates and requests continuation. [experiments/event_loop/bound_chain_filtered_recall_20260605/PRE_REGISTRATION.md]
- `HL-d4c7a61fcaa5` `H320` (falsification_criterion, `unknown`): the artifacts do not expose filtered context content and [experiments/event_loop/bound_chain_filtered_recall_20260605/PRE_REGISTRATION.md]
- `HL-fbd6acee0d4a` `H326` (falsification_criterion, `unknown`): no first wake validates and requests continuation. [experiments/event_loop/bound_chain_filtered_recall_strong_repair_20260605/PRE_REGISTRATION.md]
- `HL-b15fcb4d275e` `H327` (falsification_criterion, `unknown`): no row receives filtered bound context. [experiments/event_loop/bound_chain_filtered_recall_strong_repair_20260605/PRE_REGISTRATION.md]
- `HL-2a7a58de447e` `H328` (falsification_criterion, `unknown`): every delivered filtered context leaks the exact phrase [experiments/event_loop/bound_chain_filtered_recall_strong_repair_20260605/PRE_REGISTRATION.md]
- `HL-bfe70082e436` `H329` (falsification_criterion, `unknown`): no row both recovers the exact phrase and uses the [experiments/event_loop/bound_chain_filtered_recall_strong_repair_20260605/PRE_REGISTRATION.md]
- `HL-f09f0535a947` `H330` (falsification_criterion, `unknown`): results do not expose the provenance fields needed to [experiments/event_loop/bound_chain_filtered_recall_strong_repair_20260605/PRE_REGISTRATION.md]
- `HL-eb91db0ad161` `H311` (falsification_criterion, `unknown`): no row has delivered bound record-ID context. [experiments/event_loop/bound_chain_record_recall_patch_20260605/PRE_REGISTRATION.md]
- `HL-20514b683f50` `H312` (falsification_criterion, `unknown`): no row both recovers the exact phrase and uses the bound [experiments/event_loop/bound_chain_record_recall_patch_20260605/PRE_REGISTRATION.md]
- `HL-37f2ba68193c` `H313` (falsification_criterion, `unknown`): the first-wake contract regresses to no valid [experiments/event_loop/bound_chain_record_recall_patch_20260605/PRE_REGISTRATION.md]
- `HL-c6c9a25826c3` `H314` (falsification_criterion, `unknown`): focused tests fail. [experiments/event_loop/bound_chain_record_recall_patch_20260605/PRE_REGISTRATION.md]
- `HL-be935e1ff561` `H315` (falsification_criterion, `unknown`): artifacts do not expose the bound record ID and context [experiments/event_loop/bound_chain_record_recall_patch_20260605/PRE_REGISTRATION.md]

## Coverage Notes

- `results.json` files seen: 118
- result files with hypothesis maps: 32
- non-dict result files: 17
- result files without hypothesis maps: 69
- Markdown sources scanned: 235
- entries with nearby raw trace links: 233

## Use

Use `docs/hypothesis-ledger-20260605.jsonl` for search, filtering, and future falsification planning. Use this stocktake for a human-level map of status distributions and high-priority gaps.
