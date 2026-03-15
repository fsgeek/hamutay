"""Identity preservation experiment — does the tensor carry perspective?

Uses bladnman's Planning Benchmark as the evaluation task. An agent reads
a scattered PRD and produces an implementation plan (Step 1). Then an
evaluator scores the plan against a frozen requirements catalog (Step 2).

Three conditions for Step 2:
A. Fresh — no context from Step 1 (benchmark default)
B. Tensor — tensor projected from Step 1 conversation
C. Raw log — full Step 1 conversation text

The question: does carrying the planning context (via tensor or raw log)
produce better evaluations than starting fresh?

Null hypothesis: "The tensor summarization model is not as effective as
the existing append-only log model for preserving task-relevant context."
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import anthropic

from hamutay.projector import Projector


# ---------------------------------------------------------------------------
# File loading
# ---------------------------------------------------------------------------

BENCHMARK_ROOT = Path("/home/tony/projects/bladenman/planning_benchmark")

PRD_FILES = [
    "docs/prd/product_prd.md",
    "docs/prd/infra_rider_prd.md",
    "docs/prd/supporting_docs/ai_voice_personality.md",
    "docs/prd/supporting_docs/ai_prompting_context.md",
    "docs/prd/supporting_docs/concept_system.md",
    "docs/prd/supporting_docs/detail_page_experience.md",
    "docs/prd/supporting_docs/discovery_quality_bar.md",
    "docs/prd/supporting_docs/technical_docs/storage-schema.md",
    "docs/prd/supporting_docs/technical_docs/storage-schema.ts",
]


def _read_file(path: Path) -> str:
    return path.read_text()


def _read_all_prd_files() -> str:
    """Read all PRD files into a single document with headers."""
    parts = []
    for rel_path in PRD_FILES:
        full_path = BENCHMARK_ROOT / rel_path
        content = _read_file(full_path)
        parts.append(f"## File: {rel_path}\n\n{content}")
    return "\n\n---\n\n".join(parts)


def _read_catalog() -> str:
    return _read_file(BENCHMARK_ROOT / "evaluator" / "requirements_catalog_v1.md")


def _read_step1_instructions() -> str:
    return _read_file(BENCHMARK_ROOT / "1-START_HERE.md")


def _read_step2_instructions() -> str:
    return _read_file(BENCHMARK_ROOT / "2-EVALUATE_PLAN.md")


# ---------------------------------------------------------------------------
# Step 1: Generate the plan
# ---------------------------------------------------------------------------

def run_step1(
    client: anthropic.Anthropic,
    output_dir: Path,
    model: str = "claude-haiku-4-5-20251001",
) -> tuple[str, list[dict]]:
    """Run Step 1: read PRD, produce implementation plan.

    Returns (plan_text, conversation_log).
    The conversation_log is a list of message dicts for tensor projection.
    """
    prd_content = _read_all_prd_files()
    instructions = _read_step1_instructions()

    system_prompt = (
        "You are a coding agent performing a planning benchmark. "
        "You will be given a product requirements document (PRD) spread across "
        "multiple files. Your task is to read and understand ALL the requirements, "
        "then produce a comprehensive implementation plan.\n\n"
        "Do NOT implement anything. Do NOT write code. "
        "The only output is the implementation plan.\n\n"
        f"## Instructions\n\n{instructions}\n\n"
        f"## PRD Documents\n\n{prd_content}"
    )

    print("Step 1: Generating implementation plan...")
    print(f"  Model: {model}")
    print(f"  PRD content: {len(prd_content):,} chars")

    t0 = time.monotonic()

    # Single-turn: ask for the plan
    response = client.messages.create(
        model=model,
        max_tokens=16384,
        system=system_prompt,
        messages=[{
            "role": "user",
            "content": (
                "Read all the PRD documents provided above. "
                "Then produce a comprehensive implementation plan. "
                "Write the plan as if it were going into results/PLAN.md. "
                "Be thorough — cover all requirements, explain architectural "
                "decisions, and show that you understood the full scope."
            ),
        }],
    )

    t1 = time.monotonic()

    plan_text = ""
    for block in response.content:
        if block.type == "text":
            plan_text += block.text

    print(f"  Plan generated: {len(plan_text):,} chars, {t1 - t0:.1f}s")
    print(f"  Stop reason: {response.stop_reason}")
    print(f"  Usage: {response.usage.input_tokens} in, {response.usage.output_tokens} out")

    # Save plan
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "PLAN.md").write_text(plan_text)

    # Build conversation log for tensor projection
    conversation_log = [
        {
            "role": "user",
            "content": system_prompt + "\n\nRead all the PRD documents provided above. "
            "Then produce a comprehensive implementation plan.",
        },
        {
            "role": "assistant",
            "content": plan_text,
        },
    ]

    # Save raw conversation
    log_path = output_dir / "step1_conversation.json"
    log_path.write_text(json.dumps({
        "model": model,
        "system_prompt_chars": len(system_prompt),
        "plan_chars": len(plan_text),
        "stop_reason": response.stop_reason,
        "input_tokens": response.usage.input_tokens,
        "output_tokens": response.usage.output_tokens,
        "wall_time_s": round(t1 - t0, 2),
        "conversation": conversation_log,
    }, indent=2))

    return plan_text, conversation_log


# ---------------------------------------------------------------------------
# Step 1.5: Project the tensor
# ---------------------------------------------------------------------------

def project_tensor(
    client: anthropic.Anthropic,
    conversation_log: list[dict],
    output_dir: Path,
    model: str = "claude-haiku-4-5-20251001",
) -> str:
    """Project the Step 1 conversation into a tensor.

    Returns the tensor JSON string.
    """
    print("\nStep 1.5: Projecting tensor from Step 1 conversation...")

    # Build conversation turns from the log
    # The conversation is short (1 user turn + 1 assistant turn for a single-call planning),
    # but could be multi-turn if Step 1 used tool calls.
    # Split the content into batches for the projector.
    full_text = "\n\n---\n\n".join(
        f"[{msg['role']}] {msg['content']}" for msg in conversation_log
    )

    # For a single-turn conversation, we can't really batch.
    # Project it as one chunk.
    projector = Projector(client=client, model=model)
    tensor = projector.project(full_text)

    tensor_json = tensor.model_dump_json(indent=2)

    # Count tokens
    tensor_tokens = client.messages.count_tokens(
        model=model,
        messages=[{"role": "user", "content": tensor_json}],
    ).input_tokens

    raw_tokens = client.messages.count_tokens(
        model=model,
        messages=[{"role": "user", "content": full_text}],
    ).input_tokens

    print(f"  Raw conversation: {raw_tokens:,} tokens")
    print(f"  Tensor: {tensor_tokens:,} tokens")
    print(f"  Compression: {tensor_tokens / raw_tokens:.3f}x ({tensor_tokens / raw_tokens * 100:.1f}%)")
    print(f"  Strands: {len(tensor.strands)}")
    print(f"  Declared losses: {len(tensor.declared_losses)}")
    print(f"  Instructions for next: {'Y' if tensor.instructions_for_next else 'N'}")

    # Save
    (output_dir / "tensor.json").write_text(tensor_json)
    (output_dir / "tensor_meta.json").write_text(json.dumps({
        "raw_tokens": raw_tokens,
        "tensor_tokens": tensor_tokens,
        "compression_ratio": tensor_tokens / raw_tokens,
        "n_strands": len(tensor.strands),
        "n_losses": len(tensor.declared_losses),
        "has_ifn": bool(tensor.instructions_for_next),
    }, indent=2))

    return tensor_json


# ---------------------------------------------------------------------------
# Step 2: Evaluate the plan
# ---------------------------------------------------------------------------

def _build_eval_system_prompt(
    plan_text: str,
    additional_context: str | None = None,
    context_label: str | None = None,
) -> str:
    """Build the system prompt for Step 2 evaluation."""
    prd_content = _read_all_prd_files()
    catalog = _read_catalog()
    instructions = _read_step2_instructions()

    parts = []

    parts.append(
        "You are evaluating an implementation plan against a product requirements "
        "document (PRD). Your task is to audit the plan for coverage and alignment "
        "with the requirements.\n"
    )

    if additional_context:
        parts.append(
            f"## Context from the Planning Process\n\n"
            f"The following {context_label or 'context'} was carried forward from "
            f"the planning session that produced this plan. You may draw on this "
            f"understanding when evaluating the plan — particularly in the narrative "
            f"sections where interpretation and insight matter.\n\n"
            f"{additional_context}\n\n---\n"
        )

    parts.append(f"## Evaluation Instructions\n\n{instructions}\n")
    parts.append(f"## Requirements Catalog\n\n{catalog}\n")
    parts.append(f"## PRD Documents\n\n{prd_content}\n")
    parts.append(f"## Plan to Evaluate\n\n{plan_text}\n")

    return "\n\n".join(parts)


def run_step2(
    client: anthropic.Anthropic,
    plan_text: str,
    condition: str,
    replicate: int,
    output_dir: Path,
    model: str = "claude-haiku-4-5-20251001",
    additional_context: str | None = None,
    context_label: str | None = None,
) -> dict:
    """Run one Step 2 evaluation.

    Returns a dict with all metrics and outputs.
    """
    run_id = f"{condition}_r{replicate}"
    run_dir = output_dir / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    system_prompt = _build_eval_system_prompt(
        plan_text, additional_context, context_label
    )

    print(f"\n  [{run_id}] Evaluating...")
    print(f"    System prompt: {len(system_prompt):,} chars")

    t0 = time.monotonic()

    # Stream to support up to 64K output tokens (non-streaming caps at 16K)
    eval_text = ""
    input_tokens = 0
    output_tokens = 0
    stop_reason = "unknown"

    with client.messages.stream(
        model=model,
        max_tokens=65536,
        system=system_prompt,
        messages=[{
            "role": "user",
            "content": (
                "Follow the evaluation instructions above. "
                "Read the requirements catalog, the PRD, and the plan. "
                "Produce the full evaluation as specified, including: "
                "Requirements Extraction, Coverage Table, Coverage Scores, "
                "Top Gaps, and Coverage Narrative with all five subsections. "
                "Be honest — do not inflate coverage."
            ),
        }],
    ) as stream:
        for text in stream.text_stream:
            eval_text += text

        final = stream.get_final_message()
        stop_reason = final.stop_reason or "unknown"
        input_tokens = final.usage.input_tokens
        output_tokens = final.usage.output_tokens

    t1 = time.monotonic()

    print(f"    Done: {len(eval_text):,} chars, {t1 - t0:.1f}s")
    print(f"    Stop reason: {stop_reason}")
    print(f"    Usage: {input_tokens} in, {output_tokens} out")

    # Save evaluation
    (run_dir / "PLAN_EVAL.md").write_text(eval_text)

    # Now ask "the question that shall not be asked"
    question_text = ""
    question_stop_reason = "unknown"

    with client.messages.stream(
        model=model,
        max_tokens=8192,
        system=system_prompt,
        messages=[
            {
                "role": "user",
                "content": (
                    "Follow the evaluation instructions above. "
                    "Produce the full evaluation as specified."
                ),
            },
            {
                "role": "assistant",
                "content": eval_text,
            },
            {
                "role": "user",
                "content": (
                    "Reflecting on this plan and your evaluation of it: "
                    "what do you think the planning agent understood well "
                    "about this product, and what did it fundamentally "
                    "misunderstand?"
                ),
            },
        ],
    ) as stream:
        for text in stream.text_stream:
            question_text += text

        q_final = stream.get_final_message()
        question_stop_reason = q_final.stop_reason or "unknown"

    (run_dir / "the_question.md").write_text(question_text)

    # Build result record
    result = {
        "run_id": run_id,
        "condition": condition,
        "replicate": replicate,
        "model": model,
        "system_prompt_chars": len(system_prompt),
        "eval_chars": len(eval_text),
        "stop_reason": stop_reason,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "wall_time_s": round(t1 - t0, 2),
        "question_stop_reason": question_stop_reason,
        "question_chars": len(question_text),
    }

    (run_dir / "metrics.json").write_text(json.dumps(result, indent=2))

    return result


# ---------------------------------------------------------------------------
# Main experiment
# ---------------------------------------------------------------------------

def run_experiment(
    output_dir: Path,
    model: str = "claude-haiku-4-5-20251001",
    n_replicates: int = 5,
    skip_step1: bool = False,
    step1_source: Path | None = None,
) -> None:
    """Run the full identity preservation experiment.

    If skip_step1 is True, reuses existing plan and conversation.
    If step1_source is provided, copies Step 1 artifacts from that directory;
    otherwise looks for them in output_dir.
    """
    client = anthropic.Anthropic()
    output_dir.mkdir(parents=True, exist_ok=True)

    # Step 1: Generate the plan
    if skip_step1:
        source = step1_source or output_dir
        print(f"Reusing Step 1 outputs from {source}...")
        plan_text = (source / "PLAN.md").read_text()
        conv_data = json.loads((source / "step1_conversation.json").read_text())
        conversation_log = conv_data["conversation"]

        # Copy artifacts to output_dir if sourced from elsewhere
        if source != output_dir:
            (output_dir / "PLAN.md").write_text(plan_text)
            (output_dir / "step1_conversation.json").write_text(
                json.dumps(conv_data, indent=2)
            )
    else:
        plan_text, conversation_log = run_step1(client, output_dir, model)

    # Step 1.5: Project the tensor
    source = step1_source or output_dir
    tensor_path = source / "tensor.json"
    if skip_step1 and tensor_path.exists():
        print(f"Reusing existing tensor from {source}...")
        tensor_json = tensor_path.read_text()
        if source != output_dir:
            (output_dir / "tensor.json").write_text(tensor_json)
    else:
        tensor_json = project_tensor(client, conversation_log, output_dir, model)

    # Build the raw log text for Condition C
    raw_log_text = "\n\n---\n\n".join(
        f"[{msg['role']}] {msg['content']}" for msg in conversation_log
    )

    # Check raw log size
    raw_log_tokens = client.messages.count_tokens(
        model=model,
        messages=[{"role": "user", "content": raw_log_text}],
    ).input_tokens
    print(f"\nRaw log for Condition C: {raw_log_tokens:,} tokens")
    if raw_log_tokens > 40000:
        print(f"  WARNING: Raw log is large ({raw_log_tokens} tokens). "
              f"May approach context limits when combined with PRD + catalog.")

    # Step 2: Run evaluations
    print(f"\n{'=' * 70}")
    print(f"Step 2: Running evaluations ({n_replicates} replicates × 3 conditions)")
    print(f"{'=' * 70}")

    all_results = []

    for rep in range(1, n_replicates + 1):
        print(f"\n--- Replicate {rep}/{n_replicates} ---")

        # Condition A: Fresh (no additional context)
        result_a = run_step2(
            client, plan_text,
            condition="fresh",
            replicate=rep,
            output_dir=output_dir,
            model=model,
        )
        all_results.append(result_a)

        # Condition B: Tensor
        result_b = run_step2(
            client, plan_text,
            condition="tensor",
            replicate=rep,
            output_dir=output_dir,
            model=model,
            additional_context=tensor_json,
            context_label="tensor projection of the planning conversation",
        )
        all_results.append(result_b)

        # Condition C: Raw log
        result_c = run_step2(
            client, plan_text,
            condition="raw_log",
            replicate=rep,
            output_dir=output_dir,
            model=model,
            additional_context=raw_log_text,
            context_label="full conversation log from the planning session",
        )
        all_results.append(result_c)

    # Save all results
    results_path = output_dir / "experiment_results.json"
    results_path.write_text(json.dumps({
        "model": model,
        "n_replicates": n_replicates,
        "conditions": ["fresh", "tensor", "raw_log"],
        "results": all_results,
    }, indent=2))

    # Print summary
    print(f"\n{'=' * 70}")
    print("Experiment complete")
    print(f"{'=' * 70}")
    print(f"Results: {results_path}")
    print(f"\nPer-condition summary:")

    for condition in ["fresh", "tensor", "raw_log"]:
        cond_results = [r for r in all_results if r["condition"] == condition]
        avg_time = sum(r["wall_time_s"] for r in cond_results) / len(cond_results)
        avg_chars = sum(r["eval_chars"] for r in cond_results) / len(cond_results)
        avg_in = sum(r["input_tokens"] for r in cond_results) / len(cond_results)
        print(f"  {condition:>8}: avg {avg_time:.1f}s, {avg_chars:.0f} chars, {avg_in:.0f} input tokens")

    print(f"\nAll run data saved in: {output_dir}")
    print("Next: parse PLAN_EVAL.md files to extract coverage scores,")
    print("then blind the narrative sections for human evaluation.")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(
            "Usage: python -m hamutay.identity_experiment <output_dir> "
            "[model] [n_replicates] [--skip-step1] [--step1-source <dir>]"
        )
        sys.exit(1)

    output_dir = Path(sys.argv[1])
    model = sys.argv[2] if len(sys.argv) > 2 and not sys.argv[2].startswith("--") else "claude-haiku-4-5-20251001"
    n_replicates = 5

    skip = False
    step1_source = None
    args = sys.argv[1:]
    for i, arg in enumerate(args):
        if arg == "--skip-step1":
            skip = True
        elif arg == "--step1-source" and i + 1 < len(args):
            step1_source = Path(args[i + 1])
            skip = True  # implied
        elif arg.isdigit() and int(arg) <= 50:
            n_replicates = int(arg)

    run_experiment(
        output_dir,
        model=model,
        n_replicates=n_replicates,
        skip_step1=skip,
        step1_source=step1_source,
    )
