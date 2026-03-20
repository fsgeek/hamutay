# Content Flow Analysis — Observation Full (104 cycles)

## Method
3-gram overlap analysis on full tensor data. Separates content (strand titles,
content, key claims) from meta (declared losses, IFN, open questions).

## Key Findings

### 1. The tensor is a semantic rewriter, not a text accumulator
- Mean 3-gram survival between consecutive cycles: **9.5%**
- 90.3% of content 3-grams appear only once across all 104 cycles
- BUT prior embedding-based analysis showed 71-89% semantic similarity
- **Conclusion**: the tensor preserves meaning through paraphrase, not through text preservation

### 2. Two rewrite modes: incremental integration vs structural reorganization
- **Incremental** (small batch, <500 tokens): 14.1% survival, minor title edits, strand structure preserved
  - Example: Cycle 13→14 (195 tok batch), 95.4% survival, same 11 strands
- **Reorganization** (large batch, >2000 tokens): 4.1% survival, complete structural rebuild
  - Example: Cycle 39→40 (11,783 tok batch), 0.6% survival, 5→4 strands with new titles
- Batch size is the primary driver of rewrite depth

### 3. Strand growth preserves, strand shrinkage destroys
- Growing transitions (35): 14.1% mean survival
- Stable transitions (40): 9.4% mean survival
- Shrinking transitions (28): 4.0% mean survival
- The tensor preserves more when adding structure, rewrites aggressively when consolidating

### 4. Persistent content is either invariant facts or schema echo
- **Invariant facts**: "system context interface mode", "model claude opus" — persist because the underlying reality doesn't change (19 consecutive cycles)
- **Schema echo**: "what was dropped and why" — the schema instruction language leaks into content strands (22 cycle appearances)
- True subject-matter content is highly transient at the lexical level

### 5. Declared losses are metacognitive, not accurate
- **60.4% of declared losses don't reference content from the prior tensor**
- Losses describe what *should have* been captured or what the model chose not to integrate
- No correlation between loss declarations and actual content survival rates
- **Implication**: declared losses function as self-prompting for epistemic humility, not as a changelog
- This is consistent with identity v2: losses are load-bearing as mechanism, not as information

### 6. Meta content is even more transient than content
- Meta 3-gram survival: **5.6% mean** (vs 9.5% for content)
- IFN and loss declarations are almost completely rewritten each cycle
- The most persistent meta n-grams are generic phrases: "how does the", "what are the"

## Implications for Evaluation

1. **Embedding-based similarity** measures content preservation (the right tool for semantic fidelity)
2. **N-gram overlap** measures structural stability (the right tool for rewrite depth)
3. **These measure different things** and both matter — a healthy tensor has high semantic preservation with flexible structural rewriting
4. **Declared loss accuracy** is a new metric worth tracking — what fraction of losses reference actual prior content?
5. **Batch size must be controlled** in comparative experiments — it's the strongest predictor of rewrite behavior

## Implications for Tensor Design

1. The schema echo effect suggests the schema instructions are too literal — the model embeds instruction language in content
2. A quality metric should penalize schema echo (instruction language appearing in content strands)
3. The two-mode rewrite suggests the tensor might benefit from explicit "integration" vs "reorganization" signaling
4. Loss declarations should perhaps be restructured — separate "what I dropped" from "what I notice is missing"

## Raw Numbers
- Content survival: mean 0.095, std 0.158, range [0.006, 0.954]
- Meta survival: mean 0.056, std 0.109, range [0.000, 0.995]
- Title persistence: mean 0.119, range [0.000, 1.000]
- Total declared losses: 528 (authorial_choice: 233, context_pressure: 137, practical_constraint: 113, traversal_bias: 45)
- Persistent content n-grams (5+ cycles): 589 content-specific, 156 meta-specific
