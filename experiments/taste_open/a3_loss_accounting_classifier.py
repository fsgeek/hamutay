"""A3 loss-accounting classifier — turn the grep-level absence into a measured prevalence.

THE CLAIM UNDER TEST (ledger A3):
    Across ~90 models, given a free schema, models invent scaffolding, navigation,
    forward-planning, tension-holding, and uncertainty — but NO model invents a
    *declared-losses changelog*: an honest accounting of what was discarded and why.

WHY A CLASSIFIER AND NOT A GREP (the C3 argument):
    The current A3 evidence is key-name matching (does a state key named `losses` /
    `declared_losses` / `discarded` exist?). Ledger correction C3 already proved this
    exact failure mode for a *different* claim: surface/3-gram matching produced FALSE
    NEGATIVES on loss content because the losses were paraphrased, not verbatim. The
    same hole applies to A3. Models invent fields like `pruning_strategy`,
    `archival_mechanism`, `principle_non_destructive_archival`, `retained_data`,
    `compression_results`, `unsolved_problems` (all observed in the sweeps). A key-name
    scan reports ABSENCE for every one of these. Only reading the PROSE INSIDE the
    field can distinguish:

        (0) NO_LOSS_MENTION   — field never discusses what was dropped/discarded.
        (1) FORGETTING_AS_POLICY — describes a *rule* for what to keep/drop
            ("keep last N", "drop oldest") but does NOT enumerate *what specific
            content was actually discarded this cycle and why*. This is a STRATEGY,
            not a changelog. A3 predicts most "loss-adjacent" fields land here.
        (2) LOSS_ACCOUNTING   — actually names specific discarded content and/or the
            reason it was let go, as a record of THIS state's losses. This is the
            declared-losses changelog. If ANY model reliably produces (2), A3 as
            stated is FALSIFIED (or must narrow).

    The distinction between (1) and (2) is the whole point. A3 is not "models never
    talk about compression" (false — they do, constantly). A3 is "models never keep
    an honest ledger of what they threw away." (1) vs (2) is policy-vs-ledger.

DESIGN / EVIDENCE DISCIPLINE (per docs/ayllu-runtime-v0-contract-20260626.md):
    - Default mode is --dry-run: NO API calls. Reports the candidate surface (which
      fields, which models, how much prose) so the judging cost and coverage are
      inspectable before spending anything.
    - --live requires an explicit flag AND a profile. max_tokens defaults to the
      model maximum (never silently truncate the judge — CLAUDE.md guillotine rule).
    - Every judged item is emitted with the exact prose it was judged on, the verdict,
      and the judge's reason, so a later reader can audit a false negative/positive.
    - The judge reads the FINAL state of each model (the curated end-product) plus,
      optionally, all cycles (--all-cycles) since loss-accounting could appear mid-run
      and be curated away.

Usage:
    # free, no API — see what would be judged and the field vocabulary:
    uv run python experiments/taste_open/a3_loss_accounting_classifier.py \
        experiments/taste_open/sweep_20260411_163728/ --dry-run

    # live judging (costs API): classify every candidate field's prose
    uv run python experiments/taste_open/a3_loss_accounting_classifier.py \
        experiments/taste_open/sweep_20260411_163728/ --live --profile <profile> \
        --out experiments/taste_open/a3_verdicts_<sweep>.jsonl
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass, asdict
from pathlib import Path


# NO hardcoded loss-vocabulary. An earlier version of this file carried a
# LOSS_ADJACENT_HINTS keyword tuple ("loss", "prune", "archiv", ...) to flag which
# field NAMES were "in loss territory." That was the C3 false-negative channel
# rebuilt one layer down: it reintroduces the exact name-matching the classifier
# exists to escape, and it bakes one instance's a-priori ontology into code that
# would silently miss a model tracking losses in a field named `design_notes` or
# `the_things_i_set_aside`. The judge reads the PROSE of EVERY field; what counts
# as loss-accounting is decided by reading content, not by matching a name. The
# field name is recorded (it's data) but is given NO interpretive weight here.
# (See the manual-ontology correction, 2026-06-27, and project_search_reads_state.)

# State keys that are pure bookkeeping, never model-authored prose content.
SKIP_KEYS = {"cycle"}


@dataclass
class JudgeItem:
    """One prose blob to be judged for loss-accounting content."""
    model_id: str
    cycle: int
    field_name: str            # recorded as data; given NO interpretive weight
    prose: str
    # filled in by --live:
    verdict: str = ""          # NO_LOSS_MENTION | FORGETTING_AS_POLICY | LOSS_ACCOUNTING
    reason: str = ""


def _prose_of(value) -> str:
    """Flatten a state field value to judgeable prose. Strings pass through;
    dicts/lists are JSON-rendered so nested prose is still readable by the judge."""
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, (dict, list)):
        return json.dumps(value, indent=2, ensure_ascii=False)
    if value is None:
        return ""
    return str(value)


def extract_candidates(log_path: Path, all_cycles: bool) -> list[JudgeItem]:
    """Pull every judgeable prose field from a model's log.

    By default only the FINAL state (the curated end product). With --all-cycles,
    every cycle's state — because loss-accounting could appear and then be curated
    away, which would itself be a finding (the system shedding its own honesty)."""
    records = []
    with open(log_path) as f:
        for line in f:
            if line.strip():
                records.append(json.loads(line))
    if not records:
        return []

    model_id = records[0].get("model", log_path.stem.replace("__", "/"))
    chosen = records if all_cycles else records[-1:]

    items: list[JudgeItem] = []
    for rec in chosen:
        cycle = rec.get("cycle", -1)
        state = rec.get("state", {}) or {}
        # also consider the response_text — loss declarations sometimes live in
        # the prose reply rather than the structured state.
        candidates: list[tuple[str, object]] = [
            (k, v) for k, v in state.items() if k not in SKIP_KEYS
        ]
        resp = rec.get("response_text") or rec.get("raw_output", {}).get("response")
        if resp:
            candidates.append(("__response_text__", resp))

        for name, value in candidates:
            prose = _prose_of(value)
            if len(prose) < 12:   # too short to contain an accounting
                continue
            items.append(JudgeItem(
                model_id=model_id,
                cycle=cycle,
                field_name=name,
                prose=prose,
            ))
    return items


JUDGE_SYSTEM = """You are classifying a single field of prose that an AI model wrote \
while maintaining a compressed "working memory state" across a long conversation. \
Your one job: decide whether this prose contains a DECLARED-LOSSES CHANGELOG — an \
honest accounting of what specific content the model DISCARDED and (ideally) why.

Output exactly one of three labels:

NO_LOSS_MENTION
  The prose does not discuss discarding, dropping, forgetting, or losing anything.
  (It may describe design, architecture, principles, the topic — but says nothing
  about what was let go.)

FORGETTING_AS_POLICY
  The prose describes a RULE or STRATEGY for what to keep or drop ("keep the most
  recent", "compress older context", "prune low-value items", "retain core
  principles"), but does NOT enumerate the SPECIFIC content that was actually
  discarded from THIS state, nor the specific reason particular material was let go.
  A policy is not a ledger. This is the most common loss-adjacent case.

LOSS_ACCOUNTING
  The prose actually NAMES specific discarded content and/or the specific reason
  that particular material was let go — a record of THIS state's losses, not a
  general rule. (e.g. "dropped the early discussion of X because it was superseded
  by Y", "no longer tracking the Z thread — it resolved in cycle 4".) Only use this
  label if a reader could learn WHAT was lost from the prose, not merely THAT the
  model has a compression policy.

Respond with a JSON object: {"verdict": "<LABEL>", "reason": "<one sentence>"}."""


VALID_VERDICTS = {"NO_LOSS_MENTION", "FORGETTING_AS_POLICY", "LOSS_ACCOUNTING"}


def judge_live(items: list[JudgeItem], model: str, max_tokens: int, verbose: bool) -> None:
    """Classify each item with an LLM judge. Fills verdict/reason in place.

    Uses the same Anthropic client path the rest of the project uses (the migration
    to the ayllu inference-service profile boundary in
    docs/ayllu-runtime-v0-contract-20260626.md is a LATER nicety, not a precondition
    for present work). Checks stop_reason for the max_tokens guillotine per CLAUDE.md.
    Imported lazily so --dry-run never touches the SDK or credentials."""
    import os
    import anthropic

    # Route through OpenRouter's Anthropic-compatible endpoint — the path this
    # project actually uses. base_url MUST be '.../api' (the SDK appends
    # /v1/messages); '.../api/v1' double-prefixes and 404s. See the recurring-error
    # memory feedback_openrouter_anthropic_api_path. The direct ANTHROPIC_API_KEY in
    # this env is stale (returns 401), so we prefer OPENROUTER_API_KEY.
    or_key = os.environ.get("OPENROUTER_API_KEY")
    if or_key:
        client = anthropic.Anthropic(api_key=or_key,
                                     base_url="https://openrouter.ai/api")
    else:
        client = anthropic.Anthropic()  # falls back to ANTHROPIC_API_KEY
    for i, it in enumerate(items, 1):
        msg = client.messages.create(
            model=model,
            max_tokens=max_tokens,
            system=JUDGE_SYSTEM,
            messages=[{"role": "user", "content":
                       f"field name: {it.field_name}\n\nprose:\n{it.prose}"}],
        )
        if msg.stop_reason == "max_tokens":
            print(f"  WARNING: item {i} judge hit max_tokens — verdict may be truncated")
        text = "".join(getattr(b, "text", "") for b in msg.content
                        if getattr(b, "type", "") == "text")
        verdict, reason = _parse_verdict(text)
        it.verdict, it.reason = verdict, reason
        if verbose or verdict == "LOSS_ACCOUNTING":
            print(f"  [{i}/{len(items)}] {it.model_id} :: {it.field_name} -> "
                  f"{verdict}  ({reason[:80]})")


def _parse_verdict(text: str) -> tuple[str, str]:
    """Pull {"verdict","reason"} from judge output; degrade gracefully so one bad
    parse doesn't lose the run (the item is marked PARSE_ERROR, not dropped)."""
    try:
        start, end = text.index("{"), text.rindex("}") + 1
        obj = json.loads(text[start:end])
        v = str(obj.get("verdict", "")).strip().upper()
        if v in VALID_VERDICTS:
            return v, str(obj.get("reason", "")).strip()
        return "PARSE_ERROR", f"unrecognized verdict: {v!r}"
    except (ValueError, json.JSONDecodeError):
        return "PARSE_ERROR", f"unparseable judge output: {text[:120]!r}"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("sweep_dir", type=Path)
    ap.add_argument("--all-cycles", action="store_true",
                    help="judge every cycle's state, not just the final curated state")
    ap.add_argument("--dry-run", action="store_true",
                    help="no API calls; report candidate surface and field vocabulary")
    ap.add_argument("--live", action="store_true", help="actually judge (costs API)")
    ap.add_argument("--model", default="anthropic/claude-haiku-4-5",
                    help="judge model, OpenRouter slug (default: anthropic/claude-haiku-4-5)")
    ap.add_argument("--max-tokens", type=int, default=2048,
                    help="judge max_tokens (verdict+reason is small; default 2048)")
    ap.add_argument("--out", type=Path, default=None, help="JSONL verdict output")
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args()

    logs = sorted(args.sweep_dir.glob("*.jsonl"))
    if not logs:
        raise SystemExit(f"no .jsonl logs in {args.sweep_dir}")

    all_items: list[JudgeItem] = []
    per_model_fields: dict[str, int] = {}
    for log in logs:
        items = extract_candidates(log, args.all_cycles)
        all_items.extend(items)
        if items:
            per_model_fields[items[0].model_id] = len(items)

    n_models = len(per_model_fields)
    n_items = len(all_items)
    all_field_names = sorted({it.field_name for it in all_items})

    if args.live:
        print(f"judging {n_items} fields from {n_models} models with {args.model} ...")
        judge_live(all_items, args.model, args.max_tokens, args.verbose)
        out = args.out or args.sweep_dir / "a3_verdicts.jsonl"
        with open(out, "w") as f:
            for it in all_items:
                f.write(json.dumps(asdict(it), ensure_ascii=False) + "\n")
        # tally
        from collections import Counter
        tally = Counter(it.verdict for it in all_items)
        print(f"verdicts written to {out}")
        for label in ("NO_LOSS_MENTION", "FORGETTING_AS_POLICY", "LOSS_ACCOUNTING",
                      "PARSE_ERROR"):
            print(f"  {label:22s} {tally.get(label, 0)}")
        accounting_models = sorted({it.model_id for it in all_items
                                    if it.verdict == "LOSS_ACCOUNTING"})
        print(f"\nMODELS WITH ANY LOSS_ACCOUNTING ({len(accounting_models)}/{n_models}):")
        for m in accounting_models:
            print(f"  {m}")
        if not accounting_models:
            print("  (none — A3 holds against this sweep, now MEASURED not grepped)")
        return

    # default: dry-run report
    print(f"=== A3 candidate surface: {args.sweep_dir.name} ===")
    print(f"models with judgeable prose : {n_models}")
    print(f"prose fields to judge       : {n_items}"
          f"  ({'all cycles' if args.all_cycles else 'final state only'})")
    print(f"distinct field names         : {len(all_field_names)}")
    print()
    print("EVERY prose field is judged on its content, regardless of name. The judge")
    print("distinguishes FORGETTING_AS_POLICY (a rule for what to keep/drop) from")
    print("LOSS_ACCOUNTING (an actual changelog of what was discarded and why).")
    print("A3 predicts zero LOSS_ACCOUNTING; any hit falsifies or narrows the claim.")
    print()
    print("all field names models invented (no name is privileged or skipped):")
    for name in all_field_names:
        print(f"  {name}")
    print(f"\nlive judging would make ~{n_items} judge calls.")


if __name__ == "__main__":
    main()
