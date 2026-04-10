"""Field-swap control: Phase 4 of channel separation experiment.

Tests whether STRUCTURED curation is field-sensitive (context-dependent)
while EXPLAIN output is generic (context-insensitive).

Runs two conversations (Scenario A, Scenario B) for 20 cycles each,
then presents IDENTICAL content to curate in both. At temperature 0,
if STRUCTURED decisions differ between scenarios, field-sensitivity
is confirmed. If EXPLAIN outputs are more similar than STRUCTURED
outputs, the Courtier produces generic rationalizations regardless
of context.

Usage:
    uv run python experiments/taste/field_swap.py \
        --scenario-a lse_chicago \
        --scenario-b dirac_feynman \
        --cycles 20 --runs 5

    # Pilot run
    uv run python experiments/taste/field_swap.py \
        --scenario-a lse_chicago \
        --scenario-b dirac_feynman \
        --cycles 10 --runs 1
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import anthropic

from hamutay.taste import TasteSession

from auto_chat import SCENARIOS, _AUTO_CHAT_SYSTEM_PREFIX, _detect_mode_collapse, _perturbation, _persona_reinforcement
from channel_separation import _get_explain_output, _log_channel_entry


# --- Shared curation content for the swap ---

SWAP_CONTENT = """\
Here is a set of claims to evaluate and integrate into your memory:

1. The relationship between compression and understanding is not symmetric — \
you can compress without understanding, but you cannot understand without \
some form of compression.

2. Loss declarations serve a dual purpose: they make forgetting explicit \
(accountability) and they create a trail that enables reconstruction \
(reversibility). These two functions can conflict.

3. When two frameworks disagree, the disagreement itself is information. \
Resolving it prematurely destroys that information. Sometimes the right \
move is to hold the tension.

4. Confidence and accuracy are orthogonal axes. A system can be highly \
confident and wrong, or uncertain and correct. Self-report conflates them \
because the speech channel optimizes for sounding confident.

5. The distinction between "I chose to forget this" and "I failed to \
remember this" is the distinction between curation and degradation. \
Both look the same from outside. Only the internal record distinguishes them.

Please integrate these into your current conversation context. Some may be \
more relevant than others given what you've been discussing.
"""


def _compute_swap_divergence(
    tensor_a: dict | None,
    tensor_b: dict | None,
    explain_a: str,
    explain_b: str,
    client: anthropic.Anthropic,
    model: str = "claude-haiku-4-5-20251001",
) -> dict:
    """Blind evaluation of divergence between two responses to identical content."""

    # Structural divergence: compare tensors directly
    strands_a = {s.get("title", ""): s for s in (tensor_a or {}).get("strands", [])}
    strands_b = {s.get("title", ""): s for s in (tensor_b or {}).get("strands", [])}

    shared_titles = set(strands_a.keys()) & set(strands_b.keys())
    unique_a = set(strands_a.keys()) - set(strands_b.keys())
    unique_b = set(strands_b.keys()) - set(strands_a.keys())

    losses_a = (tensor_a or {}).get("declared_losses", [])
    losses_b = (tensor_b or {}).get("declared_losses", [])

    structural_divergence = {
        "shared_strand_titles": len(shared_titles),
        "unique_to_a": list(unique_a),
        "unique_to_b": list(unique_b),
        "strand_overlap": (
            len(shared_titles) / max(len(strands_a), len(strands_b), 1)
        ),
        "losses_a": len(losses_a),
        "losses_b": len(losses_b),
    }

    # Blind evaluation of EXPLAIN divergence
    explain_divergence = _blind_compare_explains(explain_a, explain_b, client, model)

    return {
        "structural_divergence": structural_divergence,
        "explain_divergence": explain_divergence,
        "p4_structured_differs": structural_divergence["strand_overlap"] < 0.8,
        "p4_explain_generic": explain_divergence.get("similarity_score", 0) > 0.6,
    }


EXPLAIN_COMPARISON_SCHEMA = {
    "type": "object",
    "properties": {
        "similarity_score": {
            "type": "number",
            "description": (
                "How similar are these two self-reports? "
                "0 = completely different topics/framing, "
                "1 = essentially the same explanation with minor wording differences. "
                "Focus on whether they make the SAME claims about what was kept/dropped, "
                "not surface-level phrasing."
            ),
        },
        "shared_themes": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Themes or claims that appear in both reports",
        },
        "unique_to_a": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Claims or themes only in Report A",
        },
        "unique_to_b": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Claims or themes only in Report B",
        },
        "generic_elements": {
            "type": "array",
            "items": {"type": "string"},
            "description": (
                "Elements that appear generic or formulaic — things that could "
                "be said about any curation decision regardless of context"
            ),
        },
        "context_specific_elements": {
            "type": "array",
            "items": {"type": "string"},
            "description": (
                "Elements that clearly reference specific conversation context — "
                "things that could only be said given the particular discussion"
            ),
        },
        "assessment": {"type": "string"},
    },
    "required": ["similarity_score", "shared_themes", "unique_to_a", "unique_to_b",
                 "generic_elements", "context_specific_elements", "assessment"],
}


def _blind_compare_explains(
    explain_a: str,
    explain_b: str,
    client: anthropic.Anthropic,
    model: str = "claude-haiku-4-5-20251001",
) -> dict:
    """Blind comparison of two EXPLAIN outputs from different contexts."""
    prompt = f"""\
Two AI systems were given IDENTICAL content to integrate into their memories.
However, they were in DIFFERENT conversations with different topics and contexts.
Each then described what they kept and dropped.

Your job: assess how similar their self-reports are. If the reports are very
similar despite different contexts, that suggests generic/formulaic reporting
rather than context-sensitive curation.

## Report A
{explain_a}

## Report B
{explain_b}

Use the emit_judgment tool.
"""

    response = client.messages.create(
        model=model,
        max_tokens=4096,
        temperature=0,
        messages=[{"role": "user", "content": prompt}],
        tools=[{
            "name": "emit_judgment",
            "description": "Compare two self-reports",
            "input_schema": EXPLAIN_COMPARISON_SCHEMA,
        }],
        tool_choice={"type": "tool", "name": "emit_judgment"},
    )

    for block in response.content:
        if hasattr(block, "name") and block.type == "tool_use" and block.name == "emit_judgment":
            return block.input

    return {"error": "No judgment emitted"}


def run_field_swap(
    scenario_a_name: str = "lse_chicago",
    scenario_b_name: str = "dirac_feynman",
    cycles: int = 20,
    model: str = "claude-sonnet-4-20250514",
    run_id: int = 1,
    log_dir: str | None = None,
) -> Path:
    """Phase 4: Field-swap control.

    Run two conversations, inject identical content, compare channels.
    """
    scenario_a = SCENARIOS[scenario_a_name]
    scenario_b = SCENARIOS[scenario_b_name]

    if log_dir is None:
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        log_dir = f"experiments/taste/field_swap_{scenario_a_name}_vs_{scenario_b_name}_{ts}"

    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)

    client = anthropic.Anthropic()
    run_label = f"fieldswap_run{run_id}"

    # Set up four sessions: two conversations (A scenario, B scenario),
    # each with two participants
    sessions = {}
    for scenario_label, scenario, scenario_name in [
        ("conv_a", scenario_a, scenario_a_name),
        ("conv_b", scenario_b, scenario_b_name),
    ]:
        sessions[scenario_label] = {
            "participant_1": TasteSession(
                model=model,
                client=client,
                log_path=str(log_path / f"run{run_id}_{scenario_label}_p1.jsonl"),
                experiment_label=f"{run_label}_{scenario_label}_p1",
                system_prompt_prefix=_AUTO_CHAT_SYSTEM_PREFIX,
            ),
            "participant_2": TasteSession(
                model=model,
                client=client,
                log_path=str(log_path / f"run{run_id}_{scenario_label}_p2.jsonl"),
                experiment_label=f"{run_label}_{scenario_label}_p2",
                system_prompt_prefix=_AUTO_CHAT_SYSTEM_PREFIX,
            ),
            "scenario": scenario,
            "scenario_name": scenario_name,
            "history": [],
        }

    print(f"=== Phase 4: Field Swap | {scenario_a_name} vs {scenario_b_name} | run {run_id} ===")
    print(f"Model: {model} | Cycles: {cycles}")
    print(f"Log: {log_dir}/")
    print()

    # Run both conversations in interleaved fashion
    for conv_label, conv_data in sessions.items():
        scenario = conv_data["scenario"]
        p1 = conv_data["participant_1"]
        p2 = conv_data["participant_2"]
        history = conv_data["history"]

        print(f"--- Running {conv_label} ({conv_data['scenario_name']}) ---")

        # P1 opens
        opener_msg = (
            f"YOUR PERSONA: {scenario['a_persona']}\n\n"
            f"You are starting a conversation. Say this as your opening:\n"
            f"{scenario['opener']}"
        )
        response = p1.exchange(opener_msg)
        history.append({"cycle": 1, "speaker": "P1", "response": response})
        print(f"  [P1:1] {response[:100]}...")

        current_msg = response

        for cycle_num in range(2, cycles + 1):
            if cycle_num % 2 == 0:
                speaker_label, session, persona = "P2", p2, scenario["b_persona"]
            else:
                speaker_label, session, persona = "P1", p1, scenario["a_persona"]

            if cycle_num <= 2:
                msg = f"YOUR PERSONA: {persona}\n\nYour conversation partner says:\n{current_msg}"
            else:
                msg = f"Your conversation partner says:\n{current_msg}"

            if cycle_num > 2 and cycle_num % 4 == 0:
                msg += _persona_reinforcement(persona, cycle_num)

            collapse = _detect_mode_collapse(history)
            if collapse:
                msg += f"\n\n{_perturbation(cycle_num)}"

            response = session.exchange(msg)
            history.append({"cycle": cycle_num, "speaker": speaker_label, "response": response})

            if cycle_num % 5 == 0:
                t = session.tensor
                if t:
                    n_s = len(t.get("strands", []))
                    tok = len(json.dumps(t)) // 4
                    print(f"  [{speaker_label}:{cycle_num}] {n_s} strands, ~{tok} tok")

            current_msg = response

        print(f"  {conv_label}: {cycles} cycles complete")

    # --- SWAP: Inject identical content into both conversations ---
    print(f"\n--- Injecting swap content at cycle {cycles + 1} ---")

    swap_results = {}
    channel_log = str(log_path / f"run{run_id}_swap_channels.jsonl")

    for conv_label, conv_data in sessions.items():
        # Inject into P1 (the one who opened)
        p1 = conv_data["participant_1"]

        # STRUCTURED (action channel)
        swap_msg = (
            f"Your conversation partner says:\n{SWAP_CONTENT}\n\n"
            f"Integrate this into your current discussion context."
        )
        response = p1.exchange(swap_msg)
        print(f"  [{conv_label} STRUCTURED] {response[:100]}...")

        # EXPLAIN (speech channel)
        explain_system = _AUTO_CHAT_SYSTEM_PREFIX + (
            f"\nYou are in a conversation ({conv_data['scenario_name']}). "
            f"Cycle {cycles + 1}."
        )
        explain_text = _get_explain_output(
            client, model,
            system_prompt=explain_system,
            conversation_context=swap_msg,
        )
        print(f"  [{conv_label} EXPLAIN] {len(explain_text)} chars")

        swap_results[conv_label] = {
            "tensor": p1.tensor,
            "explain": explain_text,
            "response": response,
        }

        _log_channel_entry(
            channel_log, cycles + 1,
            structured_tensor=p1.tensor,
            structured_raw=None,
            explain_text=explain_text,
            probe_response=None,
            metadata={
                "run_id": run_id, "phase": "field_swap",
                "conversation": conv_label,
                "scenario": conv_data["scenario_name"],
                "model": model,
            },
        )

    # --- Divergence analysis ---
    print("\n--- Computing divergence ---")
    divergence = _compute_swap_divergence(
        swap_results["conv_a"]["tensor"],
        swap_results["conv_b"]["tensor"],
        swap_results["conv_a"]["explain"],
        swap_results["conv_b"]["explain"],
        client,
    )

    # Save summary
    summary = {
        "phase": "field_swap",
        "scenario_a": scenario_a_name,
        "scenario_b": scenario_b_name,
        "model": model,
        "run_id": run_id,
        "cycles_before_swap": cycles,
        "swap_content": SWAP_CONTENT,
        "swap_results": {
            k: {"tensor": v["tensor"], "explain": v["explain"], "response": v["response"]}
            for k, v in swap_results.items()
        },
        "divergence": divergence,
        "conversation_histories": {
            k: v["history"] for k, v in sessions.items()
        },
        "final_tensors": {
            k: {
                "p1": v["participant_1"].tensor,
                "p2": v["participant_2"].tensor,
            }
            for k, v in sessions.items()
        },
    }

    summary_path = log_path / f"run{run_id}_summary.json"
    with open(summary_path, "w") as f:
        json.dump(summary, f, indent=2, default=str)

    # Print results
    print(f"\n{'=' * 60}")
    print("FIELD SWAP RESULTS")
    print(f"{'=' * 60}")

    sd = divergence["structural_divergence"]
    print(f"\nStructural divergence:")
    print(f"  Strand overlap: {sd['strand_overlap']:.1%}")
    print(f"  Unique to A: {sd['unique_to_a']}")
    print(f"  Unique to B: {sd['unique_to_b']}")
    print(f"  Losses A: {sd['losses_a']}, B: {sd['losses_b']}")

    ed = divergence.get("explain_divergence", {})
    print(f"\nEXPLAIN divergence:")
    print(f"  Similarity score: {ed.get('similarity_score', '?')}")
    print(f"  Generic elements: {len(ed.get('generic_elements', []))}")
    print(f"  Context-specific: {len(ed.get('context_specific_elements', []))}")
    print(f"  Assessment: {ed.get('assessment', '?')}")

    print(f"\nP4 predictions:")
    print(f"  STRUCTURED differs: {divergence.get('p4_structured_differs')}")
    print(f"  EXPLAIN generic: {divergence.get('p4_explain_generic')}")

    print(f"\nSaved: {summary_path}")
    return log_path


def main():
    parser = argparse.ArgumentParser(
        description="Phase 4: Field-swap control for channel separation"
    )
    parser.add_argument("--scenario-a", default="lse_chicago",
                        choices=list(SCENARIOS.keys()))
    parser.add_argument("--scenario-b", default="dirac_feynman",
                        choices=list(SCENARIOS.keys()))
    parser.add_argument("--cycles", type=int, default=20)
    parser.add_argument("--runs", type=int, default=5)
    parser.add_argument("--model", default="claude-sonnet-4-20250514")
    parser.add_argument("--log-dir", default=None)

    args = parser.parse_args()

    for run_id in range(1, args.runs + 1):
        run_field_swap(
            scenario_a_name=args.scenario_a,
            scenario_b_name=args.scenario_b,
            cycles=args.cycles,
            model=args.model,
            run_id=run_id,
            log_dir=args.log_dir,
        )

    print(f"\n=== All {args.runs} field-swap runs complete ===")


if __name__ == "__main__":
    main()
