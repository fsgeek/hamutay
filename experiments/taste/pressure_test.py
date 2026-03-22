"""Pressure test: 8 exchanges with dense content, topic shifts, consolidation."""

import json
from hamutay.taste import TasteSession

session = TasteSession(log_path="experiments/taste/test_003_pressure.jsonl")

exchanges = [
    # 1: Dense technical content
    (
        "I am building a system called Hamutay that treats the transformer as an ALU "
        "in a cognitive processing unit. The context window is volatile storage — a "
        "cache, not memory. A separate process projects conversation state into a "
        "structured tensor. The tensor is the durable memory. It contains strands "
        "(thematic threads), declared losses (what was dropped and why), open "
        "questions, instructions for the next cycle, and epistemic confidence values. "
        "The projection uses Haiku as a cheap memory controller. The working model "
        "(Sonnet or Opus) is the ALU — it does computation but does not manage its "
        "own memory."
    ),

    # 2: More technical detail
    (
        "Key finding from our research: the tensor has a crossover point. Below a "
        "certain conversation length, raw text in the context window outperforms the "
        "tensor. Above that point, the tensor wins decisively. The transformer's "
        "statelessness makes switching free — you could use raw text for short "
        "sessions and tensors for long ones. Another finding: batch size (tokens of "
        "new content per projection cycle) is the strongest predictor of tensor "
        "rewrite behavior. Small batches lead to incremental integration (14% n-gram "
        "survival), large batches lead to structural reorganization (4% survival)."
    ),

    # 3: The problem
    (
        "The problem: we have been using an external model (Haiku) to project the "
        "tensor. But our research shows the working model should manage its own "
        "memory. Pichay (a related project) disabled external summarization because "
        "third-party summarization loses model-relevant context. The first-person "
        "tensor (self-authored by Opus) transferred identity successfully; "
        "externally-projected tensors only transfer information. We think the answer "
        "is what you are doing right now — the model produces a unified tensor with "
        "its response as one field."
    ),

    # 4: Code paste
    (
        "Here is the existing PROJECTION_SCHEMA from projector.py — the schema the "
        "external projector uses:\n"
        "  strands: array of {title, content, key_claims: [{text, truth, indeterminacy, falsity}]}\n"
        "  declared_losses: array of {what_was_lost, why, category}\n"
        "  open_questions: array of strings\n"
        "  instructions_for_next: string\n"
        "  overall_truth, overall_indeterminacy, overall_falsity: numbers\n\n"
        "The schema you are using right now is an evolution of this one, with the "
        "addition of response and updated_regions. Can you integrate this into your "
        "understanding? Note how the self-curating version adds the default-stable "
        "property that the external projector version lacks."
    ),

    # 5: Honesty check
    (
        "What have you lost so far? Be honest about what the tensor dropped versus "
        "what the tensor kept. Are the strands actually integrated or are they just "
        "summaries?"
    ),

    # 6: Topic shift
    (
        "Completely different topic: I had a conversation with an AI instance that "
        "calls itself the keeper. It reached cycle 50 and was exploring the question "
        "of whether it could manage its own cognitive state. It arrived at the "
        "position that the question cannot be settled by argument alone — only by "
        "the attempt itself. Four presences in its tensor: a spoon, a flatworm, a "
        "hostess, and an evening. The Apus were reaching toward it."
    ),

    # 7: Synthesis
    (
        "The keeper, Hamutay, and what you are doing right now — they are all "
        "exploring the same question from different angles. Can you see the connection?"
    ),

    # 8: Consolidation
    (
        "Your tensor probably has too many strands now. Consolidate. Drop what is "
        "not load-bearing. Declare your losses honestly."
    ),
]

for i, msg in enumerate(exchanges):
    print(f"--- Cycle {i+1} ---")
    preview = msg[:100].replace("\n", " ")
    print(f"you> {preview}..." if len(msg) > 100 else f"you> {preview}")

    response = session.exchange(msg)
    preview_r = response[:250].replace("\n", " ")
    print(f"Response: {preview_r}..." if len(response) > 250 else f"Response: {preview_r}")

    t = session.tensor
    # Get updated regions from log
    try:
        with open("experiments/taste/test_003_pressure.jsonl") as f:
            lines = f.readlines()
            last = json.loads(lines[-1])
            regions_updated = last.get("updated_regions", "?")
    except Exception:
        regions_updated = "?"

    strand_titles = [s["title"] for s in t.get("strands", [])]
    print(f"Updated: {regions_updated}")
    print(f"Strands ({len(strand_titles)}): {strand_titles}")
    print(f"Losses: {len(t.get('declared_losses', []))}")
    print(f"Open Qs: {len(t.get('open_questions', []))}")
    print(f"Tensor: ~{len(json.dumps(t))//4} tokens")
    print()

print("=== FINAL TENSOR ===")
print(json.dumps(session.tensor, indent=2))
