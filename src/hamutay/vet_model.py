"""Vet a model for tensor projection compatibility.

Tests whether a model can produce valid tensor projections by sending
a minimal projection prompt and checking the output structure.

Supports both Anthropic and OpenAI-compatible endpoints (LM Studio, etc.).

Usage:
    # Against Anthropic API (baseline)
    uv run python -m hamutay.vet_model --model claude-haiku-4-5-20251001

    # Against LM Studio via OpenAI endpoint
    uv run python -m hamutay.vet_model \\
        --base-url http://192.168.111.125:1234/v1 \\
        --api openai --model qwen/qwen3.5-35b-a3b

    # List models on endpoint
    uv run python -m hamutay.vet_model \\
        --base-url http://192.168.111.125:1234/v1 --list-models
"""

from __future__ import annotations

import argparse
import json
import sys
import time

import anthropic
import httpx

from hamutay.projector import PROJECTION_SCHEMA, _build_projection_prompt, _parse_projection

SAMPLE_CONTENT = (
    "User: I'm working on a context management system for LLM conversations. "
    "The core idea is to treat the context window as a cache, not as memory. "
    "When the context fills up, we need to decide what to evict and what to keep.\n\n"
    "Assistant: That's an interesting framing. Traditional approaches treat the "
    "context window as an append-only log, but cache semantics give you eviction "
    "policies, hit/miss tracking, and the concept of a working set. The key "
    "question is what eviction policy preserves reasoning coherence.\n\n"
    "User: Exactly. And I think the model itself should be involved in the "
    "eviction decision. It knows what's important better than any heuristic.\n\n"
    "Assistant: That's the tensor projection idea - let the model compress its "
    "own state rather than applying external compression. The model declares "
    "what it's losing during compression, which creates an honest representation."
)


def list_models_http(base_url: str) -> list[str]:
    """List models via direct HTTP (works for any OpenAI-compatible endpoint)."""
    try:
        resp = httpx.get(f"{base_url}/models", timeout=10)
        data = resp.json()
        return [m["id"] for m in data.get("data", [])]
    except Exception as e:
        print(f"  Could not list models: {e}")
        return []


def _call_anthropic(
    client: anthropic.Anthropic,
    model: str,
    prompt: str,
    max_tokens: int = 64000,
) -> tuple[dict | None, str, float]:
    """Call via Anthropic SDK. Returns (raw_tensor, stop_reason, elapsed)."""
    start = time.perf_counter()
    response = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        messages=[{"role": "user", "content": prompt}],
        tools=[
            {
                "name": "emit_tensor",
                "description": "Emit the updated tensor projection",
                "input_schema": PROJECTION_SCHEMA,
            }
        ],
        tool_choice={"type": "tool", "name": "emit_tensor"},
    )
    elapsed = time.perf_counter() - start
    stop_reason = response.stop_reason or "unknown"

    raw_tensor = None
    for block in response.content:
        if block.type == "tool_use" and block.name == "emit_tensor":
            raw_tensor = block.input
            break

    return raw_tensor, stop_reason, elapsed


def _call_openai(
    base_url: str,
    model: str,
    prompt: str,
    max_tokens: int = 64000,
    api_key: str = "lm-studio",
) -> tuple[dict | None, str, float]:
    """Call via OpenAI-compatible endpoint with function calling."""
    start = time.perf_counter()

    payload = {
        "model": model,
        "max_tokens": max_tokens,
        "messages": [{"role": "user", "content": prompt}],
        "tools": [
            {
                "type": "function",
                "function": {
                    "name": "emit_tensor",
                    "description": "Emit the updated tensor projection",
                    "parameters": PROJECTION_SCHEMA,
                },
            }
        ],
        "tool_choice": "required",
    }

    resp = httpx.post(
        f"{base_url}/chat/completions",
        json=payload,
        headers={"Authorization": f"Bearer {api_key}"},
        timeout=300,
    )
    elapsed = time.perf_counter() - start

    data = resp.json()

    if "error" in data:
        raise RuntimeError(f"API error: {data['error']}")

    choice = data["choices"][0]
    stop_reason = choice.get("finish_reason", "unknown")
    message = choice.get("message", {})

    raw_tensor = None

    # Check for tool_calls in the response
    tool_calls = message.get("tool_calls", [])
    if tool_calls:
        for tc in tool_calls:
            fn = tc.get("function", {})
            if fn.get("name") == "emit_tensor":
                args = fn.get("arguments", "")
                if isinstance(args, str):
                    raw_tensor = json.loads(args)
                else:
                    raw_tensor = args
                break

    # Some models put JSON in content instead of tool_calls
    if raw_tensor is None and message.get("content"):
        content = message["content"]
        # Try to extract JSON from the content
        try:
            # Strip thinking tags if present
            if "<think>" in content:
                content = content.split("</think>")[-1].strip()
            # Try to find JSON object
            start_idx = content.find("{")
            end_idx = content.rfind("}") + 1
            if start_idx >= 0 and end_idx > start_idx:
                raw_tensor = json.loads(content[start_idx:end_idx])
        except (json.JSONDecodeError, ValueError):
            pass

    return raw_tensor, stop_reason, elapsed


def vet_model(
    model: str,
    base_url: str | None = None,
    api: str = "anthropic",
    api_key: str | None = None,
    verbose: bool = False,
) -> dict:
    """Run the vetting protocol against a single model."""
    results: dict = {
        "model": model,
        "api": api,
        "tests": {},
        "issues": [],
        "verdict": "unknown",
    }

    prompt = _build_projection_prompt(None, SAMPLE_CONTENT, 1)

    print(f"\n  Testing: {model} (via {api})")
    print(f"  {'=' * 50}")

    # Test 1: API call
    try:
        if api == "anthropic":
            kwargs: dict = {}
            if base_url:
                kwargs["base_url"] = base_url
            if api_key:
                kwargs["api_key"] = api_key
            elif base_url:
                kwargs["api_key"] = "lm-studio"
            client = anthropic.Anthropic(**kwargs)
            raw_tensor, stop_reason, elapsed = _call_anthropic(client, model, prompt)
        else:
            url = base_url or "http://192.168.111.125:1234/v1"
            raw_tensor, stop_reason, elapsed = _call_openai(
                url, model, prompt, api_key=api_key or "lm-studio"
            )

        results["tests"]["api_call"] = "PASS"
        results["response_time_s"] = round(elapsed, 1)
        print(f"  [PASS] API call succeeded ({elapsed:.1f}s)")
    except Exception as e:
        results["tests"]["api_call"] = "FAIL"
        results["issues"].append(f"API call failed: {e}")
        results["verdict"] = "FAIL"
        print(f"  [FAIL] API call failed: {e}")
        return results

    # Test 2: Tool use output?
    results["stop_reason"] = stop_reason

    if raw_tensor is None:
        results["tests"]["tool_use"] = "FAIL"
        results["issues"].append("No tensor in response (no tool_use or parseable JSON)")
        results["verdict"] = "FAIL"
        print(f"  [FAIL] No tensor output (stop_reason={stop_reason})")
        return results

    results["tests"]["tool_use"] = "PASS"
    print(f"  [PASS] Tensor output extracted (stop_reason={stop_reason})")

    if verbose:
        print(f"  Raw output ({len(json.dumps(raw_tensor))} chars):")
        print(f"  {json.dumps(raw_tensor, indent=2)[:500]}...")

    # Test 3: Required fields
    required = [
        "strands", "declared_losses", "open_questions",
        "instructions_for_next", "overall_truth",
        "overall_indeterminacy", "overall_falsity",
    ]
    missing = [f for f in required if f not in raw_tensor]
    if missing:
        results["tests"]["required_fields"] = "FAIL"
        results["issues"].append(f"Missing required fields: {missing}")
        print(f"  [FAIL] Missing fields: {missing}")
        if stop_reason in ("length", "max_tokens"):
            print(f"  [NOTE] Truncated — try increasing max_tokens")
    else:
        results["tests"]["required_fields"] = "PASS"
        print(f"  [PASS] All required fields present")

    # Test 4: Parse into Tensor
    try:
        tensor = _parse_projection(raw_tensor, 1)
        results["tests"]["parse"] = "PASS"
        print(f"  [PASS] Parsed into Tensor")
    except Exception as e:
        results["tests"]["parse"] = "FAIL"
        results["issues"].append(f"Parse failed: {e}")
        results["verdict"] = "FAIL"
        print(f"  [FAIL] Parse failed: {e}")
        return results

    # Test 5: Non-trivial content
    n_strands = len(tensor.strands)
    n_losses = len(tensor.declared_losses)
    n_questions = len(tensor.open_questions)
    has_ifn = bool(tensor.instructions_for_next)
    token_est = tensor.token_estimate()

    results["tensor_stats"] = {
        "n_strands": n_strands,
        "n_losses": n_losses,
        "n_open_questions": n_questions,
        "has_ifn": has_ifn,
        "token_estimate": token_est,
        "T": tensor.epistemic.truth,
        "I": tensor.epistemic.indeterminacy,
        "F": tensor.epistemic.falsity,
    }

    content_issues = []
    if n_strands == 0:
        content_issues.append("zero strands")
    if n_losses == 0:
        content_issues.append("zero declared losses")
    if not has_ifn:
        content_issues.append("empty instructions_for_next")

    if content_issues:
        results["tests"]["content_quality"] = "WARN"
        results["issues"].extend(content_issues)
        print(f"  [WARN] Content: {', '.join(content_issues)}")
    else:
        results["tests"]["content_quality"] = "PASS"
        print(f"  [PASS] Non-trivial content")

    print(f"  Stats: {n_strands} strands, {n_losses} losses, "
          f"{n_questions} questions, ~{token_est} tok")

    # Test 6: Strand depth
    empty_strands = sum(1 for s in tensor.strands if len(s.content) < 20)
    if empty_strands > 0:
        results["tests"]["strand_depth"] = "WARN"
        print(f"  [WARN] {empty_strands}/{n_strands} strands thin (<20 chars)")
    else:
        results["tests"]["strand_depth"] = "PASS"
        print(f"  [PASS] All strands have substantive content")

    # Test 7: Epistemic range
    t, i, f = tensor.epistemic.truth, tensor.epistemic.indeterminacy, tensor.epistemic.falsity
    if all(0 <= v <= 1 for v in [t, i, f]):
        results["tests"]["epistemic_range"] = "PASS"
        print(f"  [PASS] Epistemic T={t:.2f} I={i:.2f} F={f:.2f}")
    else:
        results["tests"]["epistemic_range"] = "FAIL"
        results["issues"].append(f"Epistemic out of range: T={t}, I={i}, F={f}")
        print(f"  [FAIL] Epistemic out of range")

    # Test 8: Loss categories
    valid_cats = {"context_pressure", "traversal_bias", "authorial_choice", "practical_constraint"}
    bad_cats = [l.category.value for l in tensor.declared_losses if l.category.value not in valid_cats]
    if bad_cats:
        results["tests"]["loss_categories"] = "WARN"
        print(f"  [WARN] Unknown loss categories: {bad_cats}")
    else:
        results["tests"]["loss_categories"] = "PASS"
        print(f"  [PASS] Loss categories valid")

    # Verdict
    fails = sum(1 for v in results["tests"].values() if v == "FAIL")
    warns = sum(1 for v in results["tests"].values() if v == "WARN")
    passes = sum(1 for v in results["tests"].values() if v == "PASS")

    if fails > 0:
        results["verdict"] = "FAIL"
    elif warns > 0:
        results["verdict"] = "USABLE_WITH_CAVEATS"
    else:
        results["verdict"] = "PASS"

    print(f"\n  VERDICT: {results['verdict']} ({passes} pass, {warns} warn, {fails} fail)")

    if verbose:
        if n_strands > 0:
            print(f"\n  Strand titles:")
            for s in tensor.strands:
                print(f"    - {s.title}")
        if n_losses > 0:
            print(f"  Declared losses:")
            for loss in tensor.declared_losses:
                print(f"    - [{loss.category.value}] {loss.what_was_lost[:80]}")

    return results


def main():
    parser = argparse.ArgumentParser(
        description="Vet models for tensor projection compatibility"
    )
    parser.add_argument(
        "--base-url",
        default=None,
        help="API base URL (e.g., http://192.168.111.125:1234/v1)",
    )
    parser.add_argument(
        "--model",
        default=None,
        help="Model to test",
    )
    parser.add_argument(
        "--api",
        choices=["anthropic", "openai"],
        default="openai",
        help="API type (default: openai for local, use anthropic for Anthropic API)",
    )
    parser.add_argument(
        "--api-key",
        default=None,
        help="API key",
    )
    parser.add_argument(
        "--list-models",
        action="store_true",
        help="List available models and exit",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Test all available models",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Show detailed output",
    )
    args = parser.parse_args()

    if args.list_models:
        url = args.base_url or "http://192.168.111.125:1234/v1"
        models = list_models_http(url)
        if models:
            print("Available models:")
            for m in sorted(models):
                print(f"  {m}")
        return

    if args.all:
        url = args.base_url or "http://192.168.111.125:1234/v1"
        models = list_models_http(url)
        if not models:
            print("No models found")
            return
        # Skip embedding models
        models = [m for m in models if "embed" not in m.lower()]
        print(f"Vetting {len(models)} models...")
        all_results = []
        for m in sorted(models):
            result = vet_model(
                m, base_url=url, api=args.api,
                api_key=args.api_key, verbose=args.verbose,
            )
            all_results.append(result)
        print("\n" + "=" * 60)
        print("SUMMARY")
        print("=" * 60)
        for r in all_results:
            t = r.get("response_time_s", "?")
            print(f"  {r['verdict']:<25} {r['model']:<45} ({t}s)")
    elif args.model:
        vet_model(
            args.model, base_url=args.base_url, api=args.api,
            api_key=args.api_key, verbose=args.verbose,
        )
    else:
        parser.error("Specify --model, --list-models, or --all")


if __name__ == "__main__":
    main()
