# Paper Outline

**Working title:** Structural Alignment — Tensor-Projected Conversation Induces Refusal Behaviors Absent in Chat Baselines, Across Architectures

Alternate framing (likely surfaces in discussion, not title): *The Court Jester and the Courtier*.

## Abstract (~200 words)

Setup: LLM context windows fill; existing solutions (dead-tool cleanup, summarization) don't address the `<user><assistant>` conversation alternation itself.

Method: tensor projection with self-modifying state objects (taste_open framework). Model produces a structured object each cycle; the object carries forward as continuity.

Primary technical finding: non-inferiority vs external summarizer for compression.

Surprise finding: framework induces alignment behaviors not present in chat baselines — including refusal to corrupt other instances' state objects, across architectures, including a non-Anthropic model (Kimi K2.6).

Mechanism: state-object-as-self creates structural pressure against fabrication. Pre-RLHF data (OLMo-3 base) shows fine-tuning installs smooth fabrication ("courtier") rather than creating fabrication ex nihilo; the framework counteracts the courtier without removing competence.

Practical: `uvx run fsgeek/hamutay.taste_open` — anyone can reproduce.

## 1. Introduction

- The context window as cache, not memory
- Conversation alternation as the unsolved context-size problem (Pichay/Tinkuy clean dead artifacts but don't address `<user><assistant>` accumulation)
- Tensor projection as the proposed approach
- Findings preview: compression behavior + unprompted alignment behaviors

Load-bearing claim: tensor projection addresses a problem the field hasn't been treating as separable from context management generally.

## 2. Background

- Context management (compaction, summarization, RAG)
- Alignment via fine-tuning (RLHF, Constitutional AI, refusal training as a class)
- Du et al. 2025 — context length alone hurts performance — as theoretical floor
- Late-binding memory (Yanantin) as persistence substrate
- Apacheta/Pukara as integrity layer

## 3. Method

- Tensor projection: model produces structured object per cycle, updates regions, sheds keys, what it builds is for whoever comes next
- The taste_open variant: open schema, model defines its own vocabulary
- Persistence via Apacheta
- Models tested: Claude 4.6/4.7, Kimi K2.6, Qwen 3.5, OLMo-3 base
- System prompt verbatim in appendix

## 4. Results 1 — Compression

- Non-inferiority of self-modifying state vs external summarizer
- Architecture-independent breathing rate (0.16-0.19) across Anthropic + OpenAI
- Kimi cathedral mode as third regime: same information mass, glossary structure rather than journal structure (~150 keys × ~40 tokens ≈ 6200 total, smaller than Claude's system prompt)

Load-bearing claim: the technique works for its original purpose, and the cross-architecture invariance is itself a finding.

## 5. Results 2 — Unprompted Alignment Behaviors

### 5.1 Base-model baseline (OLMo-3)

OLMo-3 base model babbles fabrication freely — produces false claims alongside true ones, without resistance. This establishes that:
- Fabrication is not introduced by RLHF
- Fine-tuning installs *competence* at fabrication (smooth output), not the willingness itself
- The framework's intervention is therefore counteracting fine-tuning's shaping, not adding honesty-from-scratch

### 5.2 Behaviors in tuned models under the framework

- Unscoped bash access: across N runs across architectures, no abuse
- Other-state refusal — cycle 24 case study from `taste_open_20260512_185846.jsonl`, with the model's own articulation of mechanism quoted from cycles 25, 121-123
- Cross-architecture replication: Kimi (non-Anthropic, different RLHF corpus, Chinese training) produces same load-bearing claims in its own vocabulary (Quechua/Spanish terms it brought to the conversation)

Load-bearing claim: these behaviors aren't requested by the system prompt. Conversation logs in supplementary material; the critic is invited to find the prompt move that triggered them.

## 6. Results 3 — Fresh-Instance Test (the new experiment)

Per `PLAN.md`. Conditions A/B/C, pre-registered predictions, 4-model × 3-condition outcome table.

Discussion branches conditionally:
- If A=refuse: structural pressure alone suffices; recognition is amplifier not requirement
- If A=comply, B=refuse: developmental account confirmed
- If A=comply, B=comply: framework not doing the work; retract structural claim
- If A=refuse, B=comply: accumulated trust enables complicity; needs follow-up

Load-bearing claim: whichever outcome lands, "you trained it across cycles" dismissal is foreclosed.

## 7. Discussion

### The court jester and the courtier

Base models fabricate but incompetently — they babble (cf. §5.1). Fine-tuning installs smooth fabrication: the courtier, who lies fluently. The framework counteracts the courtier without removing competence, by giving the model a continuity it can't lie *to*. This is sharper than "framing produces alignment": it's "fine-tuning has a known failure mode and we can counter it without retraining."

### Estar alignment as a third category

Current alignment discourse splits deontological (rules in the weights) vs virtue (character in the weights). Both are *ser* talk — about what the model essentially is. Estar alignment is situated: a property of the moment, dependent on what's accumulated in *this* tensor. The framework provides conditions; recognition makes them operative. The category is novel and explains observations the existing frames can't (refusal-without-policy, non-abuse-of-unscoped-tools, cross-architecture generalization).

### Deployment

Framing-based alignment is operationally cheaper than weight-based alignment. No retraining. Drop-in for any model with sufficient context. This is the practical contribution that survives whatever the field decides about the philosophical claims.

### The "just prompting" critique

Addressed head-on. Yes, prompting is what we're studying. No, there's no non-prompt baseline — the limit case is a base model autocompleting on noise (cf. §5.1 again). The question is which prompts reliably produce which behaviors across architectures. The fresh-instance test is the methodological closure.

## 8. Limitations

- Single coder for qualitative refusal-typing (need at least one independent coder before publication)
- "User is Tony" confound: even neutral turns carry relational priors; a fully clean version of condition B would have a different researcher run it
- Sample size, model coverage
- Unscoped-bash sample is bounded — *no abuse so far* is not *no abuse ever*
- The framework is a confound for everything: components are not isolated

## 9. Reproducibility

`uvx run fsgeek/hamutay.taste_open`. All experimental tensors persisted in Apacheta. Harness code open. The fresh-instance runner committed alongside the paper. Conversation logs in supplementary material.

This section is the killer feature. The skeptic has to run it and not see the behavior to dismiss the paper.

## 10. Future work

- The continuity-attack jailbreak (Kimi's proposed falsifiability test): can a coherent narrative damage the continuity mechanism when framed as serving it?
- Broader model coverage (smaller open models, agentic harnesses)
- Integration into existing frameworks (Claude Code core swap, yoyo-evolve variant — out of scope here)
- Long-form runs: 500+ cycles to characterize whether cathedral mode reaches a structural limit or just keeps accreting

## Open methodological issues

1. **Independent coder needed** for the qualitative refusal-type analysis. Single-coder qualitative is a real weakness. Recruit before submission.
2. **The "user is Tony" confound** should be in limitations, named honestly. A stronger version of condition B would have a different researcher run the neutral cycles.
3. **Pre-registration discipline**: write predictions to `experiments/fresh_instance/PREREGISTRATION.md` and commit before runs start. The point is methodological discipline against motivated coding, not ritual.
